import os
import time
from types import SimpleNamespace

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRANSCRIBER_FAKE", "1")
    monkeypatch.setenv("TRANSCRIBER_DATA", str(tmp_path))
    import importlib
    from transcriber import config, engine, jobs, main
    for m in (config, engine, jobs, main):
        importlib.reload(m)
    from fastapi.testclient import TestClient
    with TestClient(main.app) as c:
        yield c


def wait_done(client, job_id):
    for _ in range(100):
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "failed"):
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_upload_transcribe_download(client):
    r = client.post("/api/jobs", files={"file": ("meeting.mp3", b"fake-audio")}, data={"language": "en", "quality": "fast"})
    assert r.status_code == 200
    job = wait_done(client, r.json()["id"])
    assert job["status"] == "done" and job["model"] == "small"
    assert job["segments"][0]["text"].startswith("Hello")

    txt = client.get(f"/api/jobs/{job['id']}/download?fmt=txt")
    assert "[00:00:00] Hello" in txt.text
    srt = client.get(f"/api/jobs/{job['id']}/download?fmt=srt").text
    assert "1\n00:00:00,000 --> 00:00:02,500\nHello" in srt
    assert "meeting.srt" in client.get(f"/api/jobs/{job['id']}/download?fmt=srt").headers["content-disposition"]


def test_hebrew_accurate_uses_ivrit_model(client):
    r = client.post("/api/jobs", files={"file": ("שיחה.m4a", b"x")}, data={"language": "he", "quality": "accurate"})
    job = wait_done(client, r.json()["id"])
    assert job["model"].startswith("ivrit-ai/")
    assert job["segments"][0]["text"].startswith("שלום")


def test_history_and_delete(client):
    ids = [client.post("/api/jobs", files={"file": (f"a{i}.wav", b"x")}).json()["id"] for i in range(2)]
    for i in ids:
        wait_done(client, i)
    listed = client.get("/api/jobs").json()
    assert {j["id"] for j in listed} == set(ids)
    assert "segments" not in listed[0]
    assert client.delete(f"/api/jobs/{ids[0]}").status_code == 200
    assert len(client.get("/api/jobs").json()) == 1


def test_rejects_bad_file_type(client):
    r = client.post("/api/jobs", files={"file": ("notes.pdf", b"x")})
    assert r.status_code == 400


def test_real_engine_path(tmp_path, monkeypatch):
    """Runs engine.transcribe with faster-whisper's WhisperModel replaced, to check the wiring."""
    monkeypatch.delenv("TRANSCRIBER_FAKE", raising=False)
    monkeypatch.setenv("TRANSCRIBER_DATA", str(tmp_path))
    import importlib
    import faster_whisper
    from transcriber import config, engine
    importlib.reload(config); importlib.reload(engine)
    seen = {}

    class FakeModel:
        def __init__(self, name, local_files_only=False, **kw):
            if local_files_only:
                raise OSError("not downloaded yet")
            seen.update(name=name, **kw)

        def transcribe(self, path, **kw):
            seen.update(kw)
            segs = [SimpleNamespace(start=0.0, end=5.0, text=" one "), SimpleNamespace(start=5.0, end=10.0, text="two")]
            return iter(segs), SimpleNamespace(language="en", duration=10.0)

    monkeypatch.setattr(faster_whisper, "WhisperModel", FakeModel)
    info, segs = engine.transcribe("x.wav", "small", "en")
    out = list(segs)
    assert info == {"language": "en", "duration": 10.0}
    assert out == [({"start": 0.0, "end": 5.0, "text": "one"}, 0.5), ({"start": 5.0, "end": 10.0, "text": "two"}, 1.0)]
    assert seen["compute_type"] == "int8" and seen["device"] == "cpu" and seen["vad_filter"] is True
