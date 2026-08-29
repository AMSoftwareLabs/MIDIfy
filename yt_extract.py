"""yt_extract — resilient YouTube audio/video extractor SHARED by the KaraoKey and MIDIfy local tools.

This is the one place the yt-dlp download logic lives. Each tool's server.py just calls `extract(...)`; the
tools stay separate apps (different audiences) but don't duplicate the fiddly extraction code. Because each
tool is a self-contained download, this file is copied into both repos — keep them in sync (this is the source).

    from yt_extract import extract, is_youtube
    info = extract(url, CACHE_DIR, kind="audio")   # KaraoKey uses kind="video" (for the lyrics)
    # -> {"path": <downloaded file>, "title": str, "duration": int, "id": str}

YouTube's "Sign in to confirm you're not a bot" wall is the hard part. Two things beat it: keeping yt-dlp
current (run.bat force-updates it every launch) and, crucially, *pairing your cookies with a player client
that YouTube isn't currently challenging* — cookies on the default 'web' client often still get blocked. So
extract() tries a cookies.txt (dropped in the app folder) across several clients before falling back to
browser cookies and plain clients. Each attempt is printed to the console so you can see what got through.
"""
import os, re, sys

_ANSI = re.compile(r"\x1b\[[0-9;]*m")     # strip yt-dlp's coloured error text before showing it
_FMT = {
    "audio": "bestaudio[ext=m4a]/bestaudio/best",                                    # m4a/AAC decodes in the browser
    "video": "best[ext=mp4][height<=720]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
}


def _client(names, formats=None):
    """A yt-dlp opts fragment pinning the YouTube player client(s) — and optionally which formats to keep."""
    ya = {"player_client": list(names)}
    if formats:
        ya["formats"] = list(formats)   # e.g. 'missing_pot' keeps streams YouTube gated behind a PO token
    return {"extractor_args": {"youtube": ya}}


# No-cookie fallbacks, in order. 'tv' is currently the most bot-resistant client that needs no login;
# android/ios sometimes slip through age checks; browser-cookie reads are a last resort (Chrome/Edge are
# often unreadable on recent Windows because they're encrypted — Firefox reads reliably).
_ATTEMPTS = [
    _client(["tv"]),
    _client(["tv", "android", "ios"]),
    _client(["default", "-web"]),
    {"cookiesfrombrowser": ("firefox",)},
    {"cookiesfrombrowser": ("chrome",)},
    {"cookiesfrombrowser": ("edge",)},
    {},
]
# When a cookies.txt is present it's paired with each of these clients (tried before the list above), and with
# formats='missing_pot' so streams YouTube gates behind a PO token aren't silently dropped — that drop is what
# surfaces as "Requested format is not available" even though the login worked. The android/ios/android_vr
# clients still hand back plain (non-SABR, non-gated) streams, so they're the best bet once cookies get us in.
_COOKIE_CLIENTS = (["android_vr"], ["android"], ["ios"], ["tv"], ["mweb"], ["web_safari"], ["default"])


def is_youtube(url):
    return bool(re.search(r"(?:youtube\.com/|youtu\.be/|music\.youtube\.com/)", url or "", re.I))


def _label(extra):
    """Short human tag for an attempt, for the console log."""
    pc = extra.get("extractor_args", {}).get("youtube", {}).get("player_client")
    if "cookiefile" in extra:
        ck = "cookies.txt"
    elif "cookiesfrombrowser" in extra:
        ck = "browser:%s" % extra["cookiesfrombrowser"][0]
    else:
        ck = "no-cookies"
    return "client=%s %s" % (",".join(pc) if pc else "default", ck)


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

    # A cookies.txt sitting in the app folder (next to cache/) is the most reliable auth. Pair it with each
    # client YouTube tolerates and try those FIRST, then the no-cookie fallbacks.
    cookiefile = os.path.join(os.path.dirname(os.path.abspath(cache_dir)), "cookies.txt")
    attempts = []
    have_cookies = os.path.exists(cookiefile)
    if have_cookies:
        print("[yt] using cookies.txt from %s" % cookiefile, file=sys.stderr)
        for clients in _COOKIE_CLIENTS:
            a = _client(clients, formats=["missing_pot"])
            a["cookiefile"] = cookiefile
            attempts.append(a)
    attempts += _ATTEMPTS

    last = ""
    for extra in attempts:
        try:
            print("[yt] trying %s ..." % _label(extra), file=sys.stderr)
            info, path = _once(url, cache_dir, kind, extra)
            print("[yt] OK via %s" % _label(extra), file=sys.stderr)
            return {"path": path, "title": info.get("title") or "Untitled",
                    "duration": info.get("duration") or 0, "id": info.get("id") or ""}
        except Exception as e:
            s = _ANSI.sub("", str(e)).strip()
            last = s.splitlines()[-1] if s else ""

    msg = last or "extraction failed"
    if "not a bot" in msg.lower() or "sign in to confirm" in msg.lower():
        if have_cookies:
            msg += ("  —  Even with your cookies.txt YouTube blocked this. The cookies are likely stale: "
                    "re-export a fresh cookies.txt from a signed-in YouTube (open an incognito/private window, "
                    "sign in, export, then CLOSE that window so the session stays valid) and replace the file.")
        else:
            msg += ('  —  YouTube wants a login. Export a cookies.txt from a signed-in YouTube (browser extension '
                    '"Get cookies.txt LOCALLY") and drop it in the app folder, next to run.bat. See the README.')
    raise RuntimeError(msg)
