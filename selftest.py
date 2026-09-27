"""MIDIfy self-test — checks the server's input guards without YouTube, Demucs or a browser.

    py -3 selftest.py          (exit code 0 = all pass)

is_youtube() must accept only YouTube HOSTS (it once matched "youtube.com/" anywhere in the text, so
https://attacker.com/youtube.com/x got through), and /api/separate must reject an unknown stem name BEFORE running
Demucs. Demucs is faked (no 250MB model load) and uploads go to a throwaway folder, never to cache/.
"""
import io, os, shutil, sys, tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server, yt_extract

fails = []
def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else f"   <- {detail}"))
    if not cond:
        fails.append(name)

print("== is_youtube: only YouTube hosts ==")
for u in ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://youtu.be/dQw4w9WgXcQ",
          "https://music.youtube.com/watch?v=dQw4w9WgXcQ", "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
          "https://youtube.com/shorts/dQw4w9WgXcQ", "youtu.be/dQw4w9WgXcQ", "www.youtube.com/watch?v=dQw4w9WgXcQ",
          "  HTTPS://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ  "):
    check(f"accepts {u.strip()}", yt_extract.is_youtube(u) is True)
for u in ("https://malicious-domain.com/test/youtube.com/video", "https://evil.example/?next=youtu.be/abc",
          "https://youtube.com.evil.example/x", "https://youtube.com@evil.example/x", "https://notyoutube.com/x",
          "https://vimeo.com/123456", "ftp://youtube.com/x", "[https://youtu.be/x](https://youtu.be/x)", "", None):
    check(f"rejects {u!r}", yt_extract.is_youtube(u) is False)

print("== console labels ==")
check("label names the client", "tv" in yt_extract._label({"extractor_args": {"youtube": {"player_client": ["tv"]}}}))
check("label names cookies.txt", "cookies.txt" in yt_extract._label({"cookiefile": "cookies.txt"}))
check("label says no-cookies", "no-cookies" in yt_extract._label({}))

print("== server routes ==")
server.CACHE = tempfile.mkdtemp(prefix="midify-selftest-")
demucs_runs = []
def _fake_separate(inp, out_dir):
    demucs_runs.append(inp)
    for name in server.STEM_NAMES:
        open(os.path.join(out_dir, name + ".wav"), "wb").close()
server._separate_all = _fake_separate
server.app.config["TESTING"] = True
c = server.app.test_client()
wav = lambda: (io.BytesIO(b"RIFF....WAVEfmt "), "clip.wav")
try:
    r = c.get("/api/health"); j = r.get_json() or {}
    check("health: ok + extract + stem list", r.status_code == 200 and j.get("ok") is True and j.get("extract") is True
          and isinstance(j.get("stemNames"), list), j)
    check("extract: empty link → 400", c.get("/api/extract?url=").status_code == 400)
    r = c.get("/api/extract", query_string={"url": "https://vimeo.com/123456"})
    check("extract: another site → 400 'Please paste a YouTube link'",
          r.status_code == 400 and "Please paste a YouTube link" in r.get_json()["error"])
    r = c.get("/api/extract", query_string={"url": "https://attacker.com/youtube.com/x"})
    check("extract: 'youtube.com' hidden in another site's path → 400", r.status_code == 400)
    with patch("server._stems_available", return_value=False):
        r = c.post("/api/separate?stem=vocals")
        check("separate: Demucs not installed → 501 naming setup_stems.bat",
              r.status_code == 501 and "setup_stems.bat" in r.get_json()["error"])
    with patch("server._stems_available", return_value=True):
        r = c.post("/api/separate?stem=vocals")
        check("separate: no upload → 400", r.status_code == 400 and "No audio was uploaded" in r.get_json()["error"])
        for bad in ("invalid_stem_name", "../../secret"):
            n = len(demucs_runs)
            r = c.post("/api/separate", query_string={"stem": bad}, data={"audio": wav()}, content_type="multipart/form-data")
            check(f"separate: stem {bad!r} → 400 before any Demucs run",
                  r.status_code == 400 and len(demucs_runs) == n, (r.status_code, r.get_json()))
        r = c.post("/api/separate", query_string={"stem": "Bass"}, data={"audio": wav()}, content_type="multipart/form-data")
        j = r.get_json() or {}
        check("separate: an offered stem (any case) → its URL",
              r.status_code == 200 and j.get("stem") == "bass" and j.get("stemUrl", "").endswith("/bass.wav"), j)
finally:
    shutil.rmtree(server.CACHE, ignore_errors=True)

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURE(S): {fails}"))
sys.exit(1 if fails else 0)
