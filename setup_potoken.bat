@echo off
setlocal enabledelayedexpansion
title PO-token helper setup
echo.
echo   YouTube PO-token helper - one-time setup
echo   ----------------------------------------
echo   Some YouTube videos hide their audio behind a "PO token". Without it yt-dlp fails with
echo   "Requested format is not available". This installs the helper that mints those tokens so
echo   MIDIfy / KaraoKey can download normally. Re-run it any time to repair or update the helper.
echo.

REM --- Python (py launcher first, then python.exe) ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo   [X] Python not found. Install Python 3.9+ from https://www.python.org/downloads/ ^(tick "Add to PATH"^).
  pause & exit /b 1
)

REM --- Node.js >= 20 (the token generator runs on Node) ---
where node >nul 2>&1
if errorlevel 1 (
  echo   [X] Node.js is not installed. Install Node.js 20 or newer ^(LTS is fine^):
  echo         https://nodejs.org/      or      winget install OpenJS.NodeJS.LTS
  echo       Then run this script again.
  pause & exit /b 1
)
for /f "tokens=1 delims=." %%a in ('node --version') do set "NRAW=%%a"
set "NMAJ=%NRAW:v=%"
if %NMAJ% LSS 20 (
  echo   [X] Node.js 20+ required, but found %NRAW%. Update Node.js and run this again.
  pause & exit /b 1
)
echo   Node.js %NRAW% - OK

REM --- git ---
where git >nul 2>&1
if errorlevel 1 (
  echo   [X] git is not installed. Get Git for Windows: https://git-scm.com/download/win
  pause & exit /b 1
)

REM --- 1) the yt-dlp plugin (the Python half) ---
echo.
echo   [1/3] Installing yt-dlp plugin (bgutil-ytdlp-pot-provider) ...
%PY% -m pip install -q --disable-pip-version-check -U bgutil-ytdlp-pot-provider
if errorlevel 1 ( echo   [X] plugin install failed - check your internet connection. & pause & exit /b 1 )
set "POTVER="
for /f "tokens=2" %%v in ('%PY% -m pip show bgutil-ytdlp-pot-provider ^| findstr /b /c:"Version:"') do set "POTVER=%%v"
if not defined POTVER ( echo   [X] could not read the plugin version. & pause & exit /b 1 )
echo         plugin version %POTVER%

REM --- 2) build the provider (the Node half) at the plugin's default location ---
set "DEST=%USERPROFILE%\bgutil-ytdlp-pot-provider"
echo.
echo   [2/3] Building provider at "%DEST%" to match %POTVER% ...
if exist "%DEST%" rmdir /s /q "%DEST%"
git clone --single-branch --branch %POTVER% --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "%DEST%"
if errorlevel 1 ( echo   [X] clone failed ^(is %POTVER% a real release tag?^). & pause & exit /b 1 )
pushd "%DEST%\server"
call npm ci
if errorlevel 1 ( echo   [X] npm ci failed. & popd & pause & exit /b 1 )
call npx tsc
if errorlevel 1 ( echo   [X] build ^(tsc^) failed. & popd & pause & exit /b 1 )

REM --- 3) smoke-test: mint one token (contacts Google; ~10-30s) ---
echo.
echo   [3/3] Testing token generation ...
node build\generate_once.js >nul 2>&1
if errorlevel 1 (
  echo         [!] the test call errored - yt-dlp may still work; try a video before worrying.
) else (
  echo         [OK] token generation works.
)
popd

echo.
echo   Done. YouTube downloads in MIDIfy / KaraoKey now use the PO-token helper automatically
echo   (yt-dlp finds it at "%DEST%" - no extra windows, no configuration).
echo   You can close this window.
pause
endlocal
