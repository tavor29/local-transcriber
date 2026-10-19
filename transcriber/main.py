"""Web server: the upload page and a small JSON API behind it."""
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from . import config, formats, jobs

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app):
    jobs.start_worker()
    yield


app = FastAPI(title="Local Transcriber", lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/jobs")
def create_job(file: UploadFile = File(...), language: str = Form("auto"), quality: str = Form("accurate")):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Use one of: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}")
    if language not in config.LANGUAGES or quality not in config.QUALITIES:
        raise HTTPException(400, "Bad language or quality")
    fd, name = tempfile.mkstemp(dir=jobs.jobs_dir(), suffix=ext)
    tmp = Path(name)
    with os.fdopen(fd, "wb") as out:  # reuse mkstemp's handle so it gets closed; Windows can't move an open file
        shutil.copyfileobj(file.file, out)
    if tmp.stat().st_size > config.MAX_UPLOAD_MB * 1024 * 1024:
        tmp.unlink()
        raise HTTPException(413, f"File is larger than {config.MAX_UPLOAD_MB} MB")
    return jobs.create(file.filename, tmp, language, quality)


@app.get("/api/jobs")
def list_jobs():
    return jobs.list_all()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.load(job_id)
    if not job:
        raise HTTPException(404, "No such job")
    return job


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str):
    if not jobs.stop(job_id):
        raise HTTPException(409, "Job not found or already finished")
    return {"stopped": job_id}


@app.get("/api/jobs/{job_id}/download")
def download(job_id: str, fmt: str = "txt"):
    job = jobs.load(job_id)
    # A stopped job can still be downloaded, with the text transcribed before it was stopped
    if not job or job["status"] not in ("done", "stopped"):
        raise HTTPException(404, "Transcript not ready")
    stem = Path(job["filename"]).stem
    if fmt == "srt":
        body, name = formats.to_srt(job["segments"]), f"{stem}.srt"
    elif fmt == "txt":
        body, name = formats.to_txt(job["segments"]), f"{stem}.txt"
    else:
        raise HTTPException(400, "fmt must be txt or srt")
    # BOM so Notepad and Excel show Hebrew correctly
    return PlainTextResponse(
        "﻿" + body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    if not jobs.delete(job_id):
        raise HTTPException(409, "Job not found or still running")
    return {"deleted": job_id}

