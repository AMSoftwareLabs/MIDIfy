"""MIDIfy — local backend for the YouTube → MIDI transcriber.

Runs LOCALLY (binds to 127.0.0.1). Its only server job is to download a YouTube video's audio (via the shared
yt_extract library) and serve it; the actual transcription (Spotify's Basic Pitch) runs in the browser. A
separate utility from KaraoKey — different audience — but it reuses the same yt_extract.py extractor.

  GET /                     -> the transcriber page
  GET /api/health           -> {"ok":true,...} (present only locally; the page uses it to enable YouTube + stems)
  GET /api/extract?url=...  -> yt-dlp pulls the AUDIO, caches it, returns {audioUrl,title,duration,id}
  POST /api/separate?stem=  -> (optional) Demucs splits the uploaded clip; returns {stemUrl} for one stem
  GET /cache/<file>         -> serves the cached audio (Range-enabled)

Stem isolation is an OPTIONAL add-on: it only lights up if Demucs is installed (setup_stems.bat). The core
tool (whole-clip transcription) needs none of it, and the web build has no /api/separate at all.
"""
import os, hashlib
from flask import Flask, request, jsonify, send_from_directory
from yt_extract import extract, is_youtube

HERE   = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
CACHE  = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
PORT   = 8610

STEM_MODEL = "htdemucs_6s"                                   # Demucs 6-source model (adds guitar + piano)
STEM_NAMES = ["vocals", "bass", "guitar", "piano", "other"]  # pitched stems we offer (drums = a later phase)
_separator = None


def _stems_available():
    """True only if the optional Demucs engine is installed (setup_stems.bat). Keeps the feature opt-in."""
    import importlib.util
    return importlib.util.find_spec("demucs") is not None


def _separate_all(input_path, out_dir):
    """Run Demucs once → write every stem as <name>.wav into out_dir. The model loads once, then is reused."""
    global _separator
    import demucs.api, torch
    if _separator is None:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[stems] loading {STEM_MODEL} on {dev} (first time downloads the model) ...", flush=True)
        _separator = demucs.api.Separator(model=STEM_MODEL, device=dev)
    os.makedirs(out_dir, exist_ok=True)
    _, stems = _separator.separate_audio_file(input_path)
    for name, wave in stems.items():
        demucs.api.save_audio(wave, os.path.join(out_dir, name + ".wav"), samplerate=_separator.samplerate)

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():          return send_from_directory(STATIC, "audio2midi.html")

@app.get("/api/health")
def health():         return jsonify(ok=True, extract=True, stems=_stems_available(),
                                     stemModel=STEM_MODEL, stemNames=STEM_NAMES)

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


@app.post("/api/separate")
def api_separate():
    if not _stems_available():
        return jsonify(error="Stem isolation isn't installed on this machine — run setup_stems.bat once."), 501
    f = request.files.get("audio")
    if f is None:
        return jsonify(error="No audio was uploaded to separate."), 400
    stem = (request.args.get("stem") or "vocals").strip().lower()
    data = f.read()
    h = hashlib.md5(data).hexdigest()                       # cache stems by the clip's bytes → re-tries are instant
    out_dir = os.path.join(CACHE, "stems", h)
    want = os.path.join(out_dir, stem + ".wav")
    if not os.path.exists(want):                            # not separated yet → run Demucs (produces all stems)
        os.makedirs(out_dir, exist_ok=True)
        inp = os.path.join(out_dir, "input.wav")
        with open(inp, "wb") as w:
            w.write(data)
        try:
            _separate_all(inp, out_dir)
        except Exception as e:
            return jsonify(error=f"separation failed: {e}"), 500
    if not os.path.exists(want):
        return jsonify(error=f"'{stem}' isn't a stem this model produces."), 404
    return jsonify(stemUrl=f"/cache/stems/{h}/{stem}.wav", stem=stem)


if __name__ == "__main__":
    print(f"MIDIfy running -> http://127.0.0.1:{PORT}   (local personal tool - Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=PORT, debug=False)
