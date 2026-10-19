"""The part that actually runs Whisper.

transcribe() yields (segment, progress) pairs so the job can show a progress bar.
Models are loaded once and kept in memory, because loading takes longer than short files.
"""
import threading
import time
from typing import Iterator

from . import config

_models: dict[str, object] = {}
_lock = threading.Lock()


def _load(name: str):
    with _lock:
        if name not in _models:
            from faster_whisper import WhisperModel

            kw = dict(
                device=config.DEVICE,
                compute_type=config.COMPUTE_TYPE,
                cpu_threads=config.CPU_THREADS,
                download_root=str(config.DATA_DIR / "models"),
            )
            try:
                # Use the downloaded copy without touching the internet
                _models[name] = WhisperModel(name, local_files_only=True, **kw)
            except Exception:
                # First use: download it (needs internet once)
                _models[name] = WhisperModel(name, **kw)
        return _models[name]


def transcribe(path: str, model_name: str, language: str | None) -> tuple[dict, Iterator[tuple[dict, float]]]:
    """Returns (info, segments). info has 'language' and 'duration'."""
    if config.FAKE_ENGINE:
        return _fake(language)

    model = _load(model_name)
    segments, info = model.transcribe(path, language=language, beam_size=config.BEAM_SIZE, vad_filter=True)
    duration = info.duration or 0

    def gen():
        for s in segments:
            seg = {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            yield seg, min(s.end / duration, 1.0) if duration else 0.0

    return {"language": info.language, "duration": duration}, gen()


def _fake(language):
    lines = (
        ["שלום, זו הקלטת בדיקה.", "המערכת עובדת בלי אינטרנט."]
        if language == "he"
        else ["Hello, this is a test recording.", "The system works without internet.", "Nothing leaves this laptop."]
    )

    def gen():
        for i, text in enumerate(lines):
            time.sleep(0.05)
            yield {"start": i * 3.0, "end": i * 3.0 + 2.5, "text": text}, (i + 1) / len(lines)

    return {"language": language or "en", "duration": len(lines) * 3.0}, gen()
