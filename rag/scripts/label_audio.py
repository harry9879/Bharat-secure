"""Adds real scam recordings to the dataset.

For every audio file in the folder (default: C:/Users/asus/Desktop/ML/audiodata):
  1. copies it into data/audio/
  2. transcribes it with the SAME model as live calls (Whisper large-v3-turbo on
     Groq + Devanagari -> Roman Hinglish)
  3. labels it as a scam (every recording in the folder is a scam); the scam
     TYPE is suggested by DeepSeek and marked type_source=llm. Change a type by
     hand in data/audio_labels.csv and set type_source=manual: re-runs keep it.
Then rebuild the index:  .venv/Scripts/python -m scripts.build_index

Run from rag/:  .venv/Scripts/python -m scripts.label_audio [folder]
"""

import csv
import shutil
import sys
from pathlib import Path

from core import config
from core.judge import JudgeError, judge
from core.text import clean
from core.transcribe import transcribe_file

AUDIO_EXT = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".opus", ".webm", ".flac", ".mpeg"}
OUT = config.DATA_DIR / "audio_labels.csv"
FIELDS = ["file", "scam", "type", "type_source", "transcript", "raw_transcript", "stt_seconds"]


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\asus\Desktop\ML\audiodata")
    dest = config.DATA_DIR / "audio"
    dest.mkdir(parents=True, exist_ok=True)
    previous = {}
    if OUT.exists():
        previous = {r["file"]: r for r in csv.DictReader(open(OUT, encoding="utf-8"))}

    rows = []
    for path in sorted(src.iterdir()):
        if path.suffix.lower() not in AUDIO_EXT:
            continue
        local = dest / path.name
        if not local.exists():
            shutil.copy2(path, local)
        old = previous.get(path.name)
        result = transcribe_file(local)
        text = result["text"]
        kind, source = "other_scam", "default"
        if old and old.get("type_source") == "manual":
            kind, source = old["type"], "manual"
        elif config.DEEPSEEK_API_KEY and text:
            try:
                verdict = judge(clean(text), [])
                kind = verdict["type"] if verdict["type"] != "safe" else "other_scam"
                source = "llm"
            except JudgeError as e:
                print("  type suggestion failed:", e)
        rows.append(dict(file=path.name, scam="yes", type=kind, type_source=source, transcript=text,
                         raw_transcript=result["raw"], stt_seconds=result["seconds"]))
        print(f"{path.name}: {kind} ({source}), transcribed in {result['seconds']}s\n  {text[:160]}")

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} recordings to {OUT}. Check the types, then run: python -m scripts.build_index")


if __name__ == "__main__":
    main()
