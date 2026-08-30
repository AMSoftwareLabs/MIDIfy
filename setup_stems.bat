@echo off
setlocal enabledelayedexpansion
title MIDIfy - stem isolation setup
echo.
echo   MIDIfy stem isolation  (optional, one-time)
echo   -------------------------------------------
echo   Installs Demucs (Meta's source-separation engine) so MIDIfy can split a clip into
echo   vocals / bass / guitar / piano / other and transcribe just one part. Big one-time
echo   download (PyTorch + a ~250MB model); it all runs locally. Whole-clip mode never needs this.
echo.

REM --- Python: the SAME one MIDIfy runs on (run.bat uses py -3) ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo   [X] Python not found. Install Python 3.9+ from https://www.python.org/downloads/ ^(tick "Add to PATH"^).
  pause & exit /b 1
)
echo   Using Python: !PY!
!PY! --version

echo.
echo   [1/2] Installing Demucs + PyTorch  (a few hundred MB - first run is slow) ...
!PY! -m pip install --disable-pip-version-check -U demucs
if errorlevel 1 (
  echo.
  echo   [X] Install failed. If pip said it could not find a matching "torch" for your Python
  echo       version, install Python 3.12 from python.org and run this again, or grab the right
  echo       PyTorch from https://pytorch.org/get-started/locally/ first.
  pause & exit /b 1
)

echo.
echo   [2/2] Downloading the htdemucs_6s model  (~250MB, one time) ...
!PY! -c "import demucs.api; demucs.api.Separator(model='htdemucs_6s', device='cpu'); print('   model ready')"
if errorlevel 1 ( echo   [!] model download hit a snag - it will just retry on first real use. )

echo.
echo   Done. Close MIDIfy's window and re-run run.bat - the preview's "Source" menu will now
echo   offer Vocals / Bass / Guitar / Piano / Other (drums come in a later update).
echo.
echo   TIP: got an NVIDIA GPU? Separation is far faster with CUDA PyTorch -
echo        see https://pytorch.org/get-started/locally/  (optional; CPU works fine for short clips).
echo.
pause
endlocal
