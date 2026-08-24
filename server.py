"""MIDIfy — local backend for the YouTube → MIDI transcriber.

Runs LOCALLY (binds to 127.0.0.1). Its only server job is to download a YouTube video's audio (via the shared
yt_extract library) and serve it; the actual transcription (Spotify's Basic Pitch) runs in the browser. A
separate utility from KaraoKey — different audience — but it reuses the same yt_extract.py extractor.

  GET /                     -> the transcriber page
  GET /api/health           -> {"ok":true} (present only locally; the page uses it to enable the YouTube box)
  GET /api/extract?url=...  -> yt-dlp pulls the AUDIO, caches it, returns {audioUrl,title,duration,id}
  GET /cache/<file>         -> serves the cached audio (Range-enabled)
"""
import os
from flask import Flask, request, jsonify, send_from_directory
from yt_extract import extract, is_youtube

HERE   = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
CACHE  = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
PORT   = 8610

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():          return send_from_directory(STATIC, "audio2midi.html")

@app.get("/api/health")
def health():         return jsonify(ok=True, extract=True)

@app.get("/static/<path:fn>")
def static_files(fn): return send_from_directory(STATIC, fn)

@app.get("/cache/<path:fn>")
def cache_files(fn):  return send_from_directory(CACHE, fn, conditional=True)

@app.get("/api/extract")
def api_extract():
    url = (request.args.get("url") or "").strip()
    if not url or not is_youtube(url):
        return jsonify(error="Please paste a YouTube link."), 400
    try:
        r = extract(url, CACHE, kind="audio")
    except Exception as e:
        return jsonify(error=f"Couldn't fetch that video: {e}"), 502
    return jsonify(audioUrl=f"/cache/{os.path.basename(r['path'])}",
                   title=r["title"], duration=r["duration"], id=r["id"])


if __name__ == "__main__":
    print(f"MIDIfy running -> http://127.0.0.1:{PORT}   (local personal tool - Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=PORT, debug=False)
