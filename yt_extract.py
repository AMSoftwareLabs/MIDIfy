"""yt_extract — resilient YouTube audio/video extractor SHARED by the KaraoKey and MIDIfy local tools.

This is the one place the yt-dlp download logic lives. Each tool's server.py just calls `extract(...)`; the
tools stay separate apps (different audiences) but don't duplicate the fiddly extraction code. Because each
tool is a self-contained download, this file is copied into both repos — keep them in sync (this is the source).

    from yt_extract import extract, is_youtube
    info = extract(url, CACHE_DIR, kind="audio")   # KaraoKey uses kind="video" (for the lyrics)
    # -> {"path": <downloaded file>, "title": str, "duration": int, "id": str}

YouTube rejects the default 'web' player client for some videos ("page needs to be reloaded"), so extract()
retries across resilient clients and then your browser cookies (for age/sign-in-gated clips). Keeping yt-dlp
updated (run.bat force-updates it every launch) is the other half of surviving YouTube's constant changes.
"""
import os, re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")     # strip yt-dlp's coloured error text before showing it
_FMT = {
    "audio": "bestaudio[ext=m4a]/bestaudio/best",                                    # m4a/AAC decodes in the browser
    "video": "best[ext=mp4][height<=720]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
}
# Tried in order until one works: non-web player clients, then browser cookies, then plain default. A
# cookies.txt in the app folder (if present) is tried FIRST — see extract().
_ATTEMPTS = [
    {"extractor_args": {"youtube": {"player_client": ["tv", "android", "ios"]}}},
    {"extractor_args": {"youtube": {"player_client": ["default", "-web"]}}},
    {"cookiesfrombrowser": ("firefox",)},     # Firefox cookies read reliably on Windows
    {"cookiesfrombrowser": ("chrome",)},      # Chrome/Edge cookies are often unreadable on recent Windows (encrypted)
    {"cookiesfrombrowser": ("edge",)},
    {},
]


def is_youtube(url):
    return bool(re.search(r"(?:youtube\.com/|youtu\.be/|music\.youtube\.com/)", url or "", re.I))


def _once(url, cache_dir, kind, extra):
    import yt_dlp
    opts = {
        "format": _FMT.get(kind, _FMT["audio"]),
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(cache_dir, "%(id)s.%(ext)s"),
        "quiet": True, "no_warnings": True, "noplaylist": True, "cachedir": False,
    }
    opts.update(extra)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        if kind == "video" and not os.path.exists(path):     # a merge rewrites the extension to .mp4
            path = os.path.splitext(path)[0] + ".mp4"
    return info, path


def extract(url, cache_dir, kind="audio"):
    """Download `url` into cache_dir. kind='audio' (for transcription) or 'video' (for on-screen lyrics).
    Returns {"path","title","duration","id"}; raises RuntimeError (clean message) if every attempt fails."""
    os.makedirs(cache_dir, exist_ok=True)
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        raise RuntimeError("yt-dlp is not installed (run.bat installs it).")
    # A cookies.txt sitting in the app folder (next to cache/) is the most reliable auth — tried first.
    attempts = list(_ATTEMPTS)
    cookiefile = os.path.join(os.path.dirname(os.path.abspath(cache_dir)), "cookies.txt")
    if os.path.exists(cookiefile):
        attempts = [{"cookiefile": cookiefile}] + attempts
    last = ""
    for extra in attempts:
        try:
            info, path = _once(url, cache_dir, kind, extra)
            return {"path": path, "title": info.get("title") or "Untitled",
                    "duration": info.get("duration") or 0, "id": info.get("id") or ""}
        except Exception as e:
            s = _ANSI.sub("", str(e)).strip()
            last = s.splitlines()[-1] if s else ""
    msg = last or "extraction failed"
    if "not a bot" in msg.lower() or "sign in to confirm" in msg.lower():
        msg += ("  —  YouTube wants a login. Export a cookies.txt from a signed-in YouTube (browser extension "
                '"Get cookies.txt LOCALLY") and drop it in the app folder, next to run.bat. See the README.')
    raise RuntimeError(msg)
