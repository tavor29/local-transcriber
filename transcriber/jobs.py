"""Job queue and history.

Each upload becomes a job folder under data/jobs/<id>/ holding the audio file and job.json.
One background worker runs jobs in order, one at a time, since the CPU can only do one well.
History survives restarts because it is read back from those folders.
"""
import json
import queue
import threading
import time
import traceback
import uuid
from pathlib import Path

from . import config, engine

_queue: "queue.Queue[str]" = queue.Queue()
_save_lock = threading.Lock()
_worker: threading.Thread | None = None


def jobs_dir() -> Path:
    d = config.DATA_DIR / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(job_id: str) -> Path:
    return jobs_dir() / job_id / "job.json"


def load(job_id: str) -> dict | None:
    p = _path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save(job: dict) -> None:
    with _save_lock:
        p = _path(job["id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)


def create(filename: str, data_file: Path, language: str, quality: str) -> dict:
    job_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    folder = jobs_dir() / job_id
    folder.mkdir()
    audio = folder / ("audio" + Path(filename).suffix.lower())
    data_file.replace(audio)
    job = {
        "id": job_id,
        "filename": filename,
        "audio": audio.name,
        "language": language,
        "quality": quality,
        "model": config.pick_model(quality, language),
        "status": "queued",
        "progress": 0.0,
        "created": time.time(),
        "started": None,
        "finished": None,
        "duration": None,
        "detected_language": None,
        "segments": [],
        "error": None,
    }
    save(job)
    _queue.put(job_id)
    return job


def list_all() -> list[dict]:
    out = []
    for p in jobs_dir().glob("*/job.json"):
        job = json.loads(p.read_text(encoding="utf-8"))
        job.pop("segments", None)
        out.append(job)
    return sorted(out, key=lambda j: j["created"], reverse=True)


def delete(job_id: str) -> bool:
    folder = jobs_dir() / job_id
    if not folder.exists():
        return False
    job = load(job_id)
    if job and job["status"] in ("queued", "running"):
        return False
    for f in folder.iterdir():
        f.unlink()
    folder.rmdir()
    return True


def run(job_id: str) -> None:
    job = load(job_id)
    if not job:
        return
    job.update(status="running", started=time.time())
    save(job)
    try:
        info, segments = engine.transcribe(
            str(jobs_dir() / job_id / job["audio"]), job["model"], config.LANGUAGES[job["language"]]
        )
        job.update(duration=info["duration"], detected_language=info["language"])
        last_save = 0.0
        for seg, progress in segments:
            job["segments"].append(seg)
            job["progress"] = round(progress, 3)
            if time.time() - last_save > 1:
                save(job)
                last_save = time.time()
        job.update(status="done", progress=1.0)
    except Exception as e:  # keep the worker alive and show the error on the page
        traceback.print_exc()
        job.update(status="failed", error=f"{type(e).__name__}: {e}")
    job["finished"] = time.time()
    save(job)


def _loop():
    while True:
        run(_queue.get())


def start_worker() -> None:
    """Start the worker and re-queue anything left unfinished by a previous run."""
    global _worker
    if _worker and _worker.is_alive():
        return
    for job in sorted(list_all(), key=lambda j: j["created"]):
        if job["status"] in ("queued", "running"):
            full = load(job["id"])
            full.update(status="queued", progress=0.0, segments=[])
            save(full)
            _queue.put(job["id"])
    _worker = threading.Thread(target=_loop, daemon=True)
    _worker.start()
