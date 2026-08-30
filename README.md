# MIDIfy

A small **local** tool that turns audio into **MIDI**. Paste a **YouTube link** (or open an audio file) and it
transcribes the notes to a `.mid` you can open in any DAW or notation editor. Also the "Audio → MIDI" option on
the `music.anjanm.com` hub — that in-app version does **file → MIDI** in your browser; this local app adds the
**YouTube → MIDI** path (it has to download the audio first, which a web page can't do).

Transcription runs with Spotify's open-source **Basic Pitch**, right in your browser. Nothing is uploaded; any
audio it downloads stays in a local `cache/` folder.

## Requirements
- **Windows 10 / 11.**
- **Python 3.9 or newer** (3.10+ recommended) — from <https://www.python.org/downloads/>, tick **"Add Python to PATH"**.
  `run.bat` installs everything else.
- An **internet connection** (to fetch the video, load the model, and install the two Python packages first run).
- A modern browser — **Chrome or Edge**.
- *(Optional)* **ffmpeg** on PATH — only for the odd clip whose audio comes as a separate stream (`winget install Gyan.FFmpeg`).

## Run it
1. Download this repo (green **Code ▾ → Download ZIP**, then unzip) — or `git clone` it.
2. Double-click **`run.bat`**. First launch installs `flask` + `yt-dlp` and opens <http://127.0.0.1:8610>.
3. Paste a YouTube link → **Transcribe** (or **choose an audio file**) → **Download .mid**.
   The **onset / confidence / min-length** sliders tune how many notes it picks up.

## If YouTube says "confirm you're not a bot"
YouTube sometimes demands a login. Give it your cookies:
1. Install the browser extension **"Get cookies.txt LOCALLY"** (Chrome/Edge/Firefox).
2. Open **youtube.com** while **signed in**, click the extension → **Export**, and save the file as **`cookies.txt`**.
3. Put `cookies.txt` in this app's folder (next to `run.bat`), then try the link again.

The app also tries your Firefox/Chrome/Edge cookies automatically, but recent Windows encrypts Chrome/Edge
cookies so a `cookies.txt` is the reliable route. It's git-ignored — it's your login, never share it.

## If YouTube says "Requested format is not available"
Different wall: that video's audio is gated behind a **PO token** (common on YouTube Music "- Topic" tracks).
Install the one-time helper — needs **Node.js 20+**:
1. Install Node.js if you don't have it: <https://nodejs.org/> (LTS), or `winget install OpenJS.NodeJS.LTS`.
2. Double-click **`setup_potoken.bat`**. It installs the yt-dlp plugin and builds the token generator at
   `%USERPROFILE%\bgutil-ytdlp-pot-provider`, then smoke-tests it.
3. Retry the link — yt-dlp finds and uses the helper automatically (no window to keep open, no config).

## Isolate one instrument first (optional)
By default MIDIfy transcribes the **whole clip**. You can instead isolate a single part — **Vocals, Bass,
Guitar, Piano, or Other** (sitar, veena, synth, strings… all land in "Other") — which transcribes far cleaner,
especially for a lead line. It's **local-only** and an optional add-on:
1. Double-click **`setup_stems.bat`** once. It installs **Demucs + PyTorch** and a ~250 MB model (needs
   **Python 3.9+** and a few GB of disk). One-time, runs entirely on your PC.
2. Restart MIDIfy — a **Source** menu appears under the range. Pick a part, optionally name the output track
   (type e.g. *Sitar* → it's tagged as the matching General MIDI voice), then Transcribe.

The first separation of a clip runs Demucs (seconds–a minute on CPU; a GPU is much faster). It's then cached,
so switching parts or re-tweaking the note sliders is instant. Drums come in a later update (they need a
different, non-pitch method). Not available in the web version.

## Notes
- Best on **vocals or a single instrument** — so **isolate a part** (above) for a dense mix; whole-mix transcription of a full song comes out messy.
- First run downloads the Basic Pitch model (a few seconds) and warms up; a long song takes a while.
- **Personal tool.** Downloading from YouTube is against YouTube's Terms of Service and the music is copyrighted — a
  MIDI transcription still reproduces the *composition*, so this is for personal practice/study, your call. Kept local
  on purpose (YouTube blocks cloud IPs anyway).
- Shares its YouTube extractor (`yt_extract.py`) with the KaraoKey tool — same code, two separate apps.
