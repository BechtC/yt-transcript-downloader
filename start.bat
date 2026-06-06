@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat 2>nul || python -m venv .venv && call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo.
echo YouTube Transcript Downloader laeuft auf http://localhost:8765
echo Strg+C zum Beenden
echo.
python app.py
pause
