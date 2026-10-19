"""Pilot test: measure accuracy and speed of each model on clips you have reference text for.

Put clips in a folder, each with a .txt file of the same name holding the correct text:
    pilot/en/clip01.wav + pilot/en/clip01.txt
Then run:
    python -m transcriber.benchmark pilot/en --language en
It writes results.csv with word error rate (WER, lower is better) and speed per model.
"""
import argparse
import csv
import re
import time
from pathlib import Path

from . import config, engine


def normalize(text: str) -> list[str]:
    text = re.sub(r"[^\w\s']", " ", text.lower())
    return text.split()


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate: (substitutions + deletions + insertions) / words in the reference."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--language", choices=["he", "en"], required=True)
    ap.add_argument("--models", nargs="*", help="default: every model the app would use for this language")
    ap.add_argument("--out", default="results.csv")
    args = ap.parse_args()

    models = args.models or sorted({config.pick_model(q, args.language) for q in config.QUALITIES})
    clips = sorted(p for p in Path(args.folder).iterdir() if p.suffix.lower() in config.ALLOWED_EXTENSIONS)
    rows = []
    for model in models:
        for clip in clips:
            ref_file = clip.with_suffix(".txt")
            if not ref_file.exists():
                print(f"skip {clip.name}: no {ref_file.name}")
                continue
            t0 = time.time()
            info, segs = engine.transcribe(str(clip), model, args.language)
            text = " ".join(s["text"] for s, _ in segs)
            took = time.time() - t0
            row = {
                "model": model,
                "clip": clip.name,
                "audio_sec": round(info["duration"], 1),
                "processing_sec": round(took, 1),
                "x_realtime": round(info["duration"] / took, 2) if took else "",
                "wer": round(wer(ref_file.read_text(encoding="utf-8"), text), 3),
                "transcript": text,
            }
            rows.append(row)
            print(f"{model:40} {clip.name:20} WER {row['wer']:.1%}  {row['x_realtime']}x realtime")

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["model"])
        w.writeheader()
        w.writerows(rows)

    print("\nSummary (average per model):")
    for model in models:
        mine = [r for r in rows if r["model"] == model]
        if mine:
            audio = sum(r["audio_sec"] for r in mine)
            proc = sum(r["processing_sec"] for r in mine)
            print(f"  {model:40} WER {sum(r['wer'] for r in mine)/len(mine):.1%}  "
                  f"~{proc/audio*60:.0f} min per hour of audio")
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
