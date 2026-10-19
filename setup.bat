@echo off
rem One-time setup: creates a private Python environment and installs the app.
cd /d "%~dp0"
python -m venv .venv || (echo Python 3.10+ is needed. Install it from python.org and tick "Add to PATH". & pause & exit /b 1)
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt || (echo Install failed. & pause & exit /b 1)
echo.
echo Setup done. Next: run download-models.bat once (needs internet), then start.bat.
pause
