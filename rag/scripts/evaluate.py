"""Honest check of the RAG scorer on calls it can't simply look up.

Test sets
  scams_txt    the team's 31 scam + 23 genuine calls (leave-one-out: the call
               being tested is removed from the search)
  audio        the transcribed real scam recordings (leave-one-out)
The hand-written pattern cards (knowledge/patterns.jsonl) are always left out
of the search here, because they were written after seeing these test calls.

Each call is fed in pieces of ~10 words, like a live call; a call counts as
flagged if its score ever reaches the level.

Run from rag/:  .venv/Scripts/python -m scripts.evaluate [--no-llm]
Writes data/eval_results.json
"""

import argparse
import csv
import json
from collections import defaultdict

from core import config
from core.index import Index, embed
from core.knowledge import scams_txt
from core.session import CallSession
from core.text import clean

PIECE_WORDS = 10


def test_items():
    for p in scams_txt():
        yield "scams_txt", p["group"], p["label"], p["text"]
    audio_csv = config.DATA_DIR / "audio_labels.csv"
    if audio_csv.exists():
        for r in csv.DictReader(open(audio_csv, encoding="utf-8")):
            if r["transcript"].strip():
                yield "audio", f"audio/{r['file']}", r["type"], clean(r["transcript"])


def run(index, use_llm):
    if use_llm:
        config.LLM_EVERY_SECONDS = 0  # judge every piece, so results don't depend on timing
    rows = []
    for source, group, label, text in test_items():
        s = CallSession(index, use_llm=use_llm, exclude_group=group, exclude_sources=("pattern",))
        words = text.split()
        last = None
        for i in range(0, len(words), PIECE_WORDS):
            last = s.add_text(" ".join(words[i:i + PIECE_WORDS]))
        rows.append(dict(source=source, group=group, label=label, peak=s.peak,
                         final_type=last["type"] if last else None, text=text[:90]))
    return rows


def summarise(rows, warn, scam):
    out = {}
    for source in sorted({r["source"] for r in rows}):
        rs = [r for r in rows if r["source"] == source]
        legit = [r for r in rs if r["label"] == "safe"]
        scams = [r for r in rs if r["label"] != "safe"]
        caught = [r for r in scams if r["peak"] >= warn]
        out[source] = dict(
            scams=len(scams), legit=len(legit),
            caught_warning=sum(r["peak"] >= warn for r in scams),
            caught_scam=sum(r["peak"] >= scam for r in scams),
            false_alarms_warning=sum(r["peak"] >= warn for r in legit),
            false_alarms_scam=sum(r["peak"] >= scam for r in legit),
            type_correct=sum(r["final_type"] == r["label"] for r in caught),
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    use_llm = not args.no_llm and bool(config.DEEPSEEK_API_KEY)
    index = Index.load()
    embed(["warm up"], "query")
    rows = run(index, use_llm)
    mode = "retrieval + DeepSeek" if use_llm else "retrieval only"
    summary = summarise(rows, config.WARN_AT, config.SCAM_AT)
    print(f"\n{mode}  (WARNING at {config.WARN_AT}, SCAM at {config.SCAM_AT})")
    print(f"{'set':12s} {'scams caught (WARN/SCAM)':>26s} {'false alarms (WARN/SCAM)':>26s} {'type right':>11s}")
    for src, m in summary.items():
        print(f"{src:12s} {m['caught_warning']:>8d}/{m['scams']:<3d} {m['caught_scam']:>4d}/{m['scams']:<9d}"
              f"{m['false_alarms_warning']:>8d}/{m['legit']:<3d} {m['false_alarms_scam']:>4d}/{m['legit']:<9d}"
              f"{m['type_correct']:>5d}")
    # Trade-off: what other WARNING thresholds would do (all sets together).
    sweep = []
    for t in (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8):
        legit = [r for r in rows if r["label"] == "safe"]
        scams = [r for r in rows if r["label"] != "safe"]
        sweep.append(dict(threshold=t, caught=sum(r["peak"] >= t for r in scams), scams=len(scams),
                          false_alarms=sum(r["peak"] >= t for r in legit), legit=len(legit)))
    print("\nthreshold sweep (all sets):", ", ".join(f"{s['threshold']}: {s['caught']}/{s['scams']} caught, "
                                                    f"{s['false_alarms']}/{s['legit']} FA" for s in sweep))
    missed = [r for r in rows if (r["label"] != "safe") != (r["peak"] >= config.WARN_AT)]
    print("\nmistakes at WARNING:")
    for r in missed:
        print(f"  {r['source']:11s} {r['label']:15s} peak {r['peak']:.2f}  {r['text'][:70]}")
    out = config.DATA_DIR / ("eval_results_llm.json" if use_llm else "eval_results_retrieval.json")
    out.write_text(json.dumps(dict(mode=mode, warn=config.WARN_AT, scam=config.SCAM_AT, summary=summary,
                                   sweep=sweep, rows=rows), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
