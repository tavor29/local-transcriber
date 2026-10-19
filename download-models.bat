@echo off
rem Downloads the three Whisper models once (about 3.5 GB). After this the app works with no internet.
cd /d "%~dp0"
.venv\Scripts\python -m transcriber.download_models
pause
