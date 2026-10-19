"""Turn transcript segments into .txt and .srt files."""


def _clock(seconds: float, sep: str) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_txt(segments: list[dict], timestamps: bool = True) -> str:
    if not timestamps:
        return "\n".join(seg["text"] for seg in segments) + "\n"
    return "\n".join(f"[{_clock(seg['start'], '.')[:8]}] {seg['text']}" for seg in segments) + "\n"


def to_srt(segments: list[dict]) -> str:
    blocks = []
    for i, seg in enumerate(segments, 1):
        blocks.append(f"{i}\n{_clock(seg['start'], ',')} --> {_clock(seg['end'], ',')}\n{seg['text']}\n")
    return "\n".join(blocks)
