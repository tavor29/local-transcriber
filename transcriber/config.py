"""Settings. Change these in one place, or override with environment variables."""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("TRANSCRIBER_DATA", Path(__file__).resolve().parent.parent / "data"))

# Which Whisper model each choice on the page uses.
# "fast" = small model, "accurate" = large-v3-turbo.
# Hebrew + accurate uses the ivrit.ai model, which is fine-tuned on Hebrew.
MODELS = {
    ("fast", "any"): "small",
    ("accurate", "any"): "large-v3-turbo",
    ("accurate", "he"): os.environ.get("TRANSCRIBER_HEBREW_MODEL", "ivrit-ai/whisper-large-v3-turbo-ct2"),
}

LANGUAGES = {"auto": None, "he": "he", "en": "en"}
QUALITIES = ("fast", "accurate")

# CPU settings for a 4-core laptop. int8 is the fastest CPU mode with almost no accuracy loss.
DEVICE = os.environ.get("TRANSCRIBER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("TRANSCRIBER_COMPUTE_TYPE", "int8")
CPU_THREADS = int(os.environ.get("TRANSCRIBER_THREADS", "4"))
# How many candidate wordings Whisper weighs per sentence. 1 is about twice as fast as 5,
# with only a small accuracy cost. Set TRANSCRIBER_BEAM_SIZE=5 for the slower, careful mode.
BEAM_SIZE = int(os.environ.get("TRANSCRIBER_BEAM_SIZE", "1"))

# Set TRANSCRIBER_FAKE=1 to use a stand-in engine (for tests and demos without models).
FAKE_ENGINE = os.environ.get("TRANSCRIBER_FAKE") == "1"

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac", ".webm", ".mkv", ".aac", ".wma"}
MAX_UPLOAD_MB = 1024


def pick_model(quality: str, language: str) -> str:
    return MODELS.get((quality, language)) or MODELS[(quality, "any")]
