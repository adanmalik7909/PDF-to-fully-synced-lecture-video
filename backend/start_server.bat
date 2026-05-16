@echo off
echo ══════════════════════════════════════════════════
echo   SmartStudyInstructor V6 — Starting Server
echo ══════════════════════════════════════════════════
taskkill /F /IM python.exe /IM chrome.exe /IM ffmpeg.exe 2>nul
timeout /t 2 >nul
cd /d "%~dp0"
echo Starting on http://127.0.0.1:8000
echo Open http://127.0.0.1:8000/blueprint in your browser
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
