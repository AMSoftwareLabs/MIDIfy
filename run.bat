@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title MIDIfy
echo.
echo   MIDIfy  -  local audio / YouTube -^> MIDI transcriber
echo   ---------------------------------------------------
echo.

REM --- find Python (py launcher first, then python.exe) ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo   [X] Python was not found.
  echo       Install Python 3.9 or newer ^(3.10+ recommended^) from https://www.python.org/downloads/
  echo       IMPORTANT: tick "Add Python to PATH" during install, then double-click run.bat again.
  echo.
  pause & exit /b 1
)
echo   Using Python: !PY!

REM --- dependencies (flask + yt-dlp); yt-dlp is force-updated so YouTube doesn't break it ---
echo   Installing / updating flask + yt-dlp ...
!PY! -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo   [X] Could not install dependencies. Check your internet connection. & pause & exit /b 1 )
!PY! -m pip install -q --disable-pip-version-check -U yt-dlp

REM --- ffmpeg is optional but helps with some clips ---
where ffmpeg >nul 2>&1 || echo   [i] ffmpeg not on PATH - most clips still work; a few need it ^(winget install Gyan.FFmpeg^).

echo.
echo   Opening http://127.0.0.1:8610 ...  Keep this window open; press Ctrl+C to stop.
start "" /min cmd /c "ping -n 3 127.0.0.1 >nul & start http://127.0.0.1:8610"
!PY! server.py
echo.
echo   Server stopped.
pause
endlocal
