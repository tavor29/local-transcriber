@echo off
rem Starts the transcriber and opens it in the browser. Close this window to stop it.
cd /d "%~dp0"
start "" http://localhost:8000
.venv\Scripts\python -m uvicorn transcriber.main:app --host 127.0.0.1 --port 8000
