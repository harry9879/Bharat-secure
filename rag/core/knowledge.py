"""Collects every labelled example the retriever can search.

Each passage: {id, source, group, label, text}
  label  "safe" or a scam type (config.SCAM_TYPES)
  group  passages from the same original call/item share a group, so an
         evaluation can leave a whole item out of the search (leave-one-out)

Sources
  pattern    knowledge/patterns.jsonl: hand-written scam and genuine examples
  scams_txt  data/scams_call.txt: 31 scam + 23 genuine calls supplied by the team,
             types in data/scams_call_types.csv
  audio      data/audio_labels.csv: real scam recordings, transcribed with the
             same Whisper turbo + Hinglish converter as live calls
"""

import csv
import json
import re

from . import config
from .text import clean

def patterns():
    for line in open(config.KNOWLEDGE_DIR / "patterns.jsonl", encoding="utf-8"):
        p = json.loads(line)
        yield dict(id=f"pattern/{p['id']}", source="pattern", group=f"pattern/{p['id']}",
                   label=p["label"], text=clean(p["text"]))


def parse_scams_txt():
    """(kind, number, text) for each numbered call in data/scams_call.txt."""
    kind = None
    for line in open(config.DATA_DIR / "scams_call.txt", encoding="utf-8"):
        line = line.strip()
        low = line.lower()
        if low.startswith("scams call"):
            kind = "scam"
            continue
        if low.startswith("genuine call"):
            kind = "genuine"
            continue
        m = re.match(r"(\d+)\.\s*(.+)", line)
        if kind and m:
            # The file's ₹ signs were lost to an old encoding and show as "?".
            text = re.sub(r"\?(?=\s?\d)", "₹", m.group(2)).strip().strip('"“”�')
            yield kind, int(m.group(1)), text


def scams_txt():
    types = {int(r["number"]): r["type"] for r in csv.DictReader(open(config.DATA_DIR / "scams_call_types.csv",
                                                                        encoding="utf-8"))}
    for kind, num, text in parse_scams_txt():
        label = types[num] if kind == "scam" else "safe"
        gid = f"scams_txt/{kind}/{num}"
        yield dict(id=gid, source="scams_txt", group=gid, label=label, text=clean(text))


def audio():
    path = config.DATA_DIR / "audio_labels.csv"
    if not path.exists():
        return
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if not r["transcript"].strip():
            continue
        gid = f"audio/{r['file']}"
        yield dict(id=gid, source="audio", group=gid, label=r["type"], text=clean(r["transcript"]))


def all_passages():
    out = [p for src in (patterns, scams_txt, audio) for p in src() if p["text"]]
    return out
