"""Leave-one-out SMS evaluation on the ScamShield corpus + hand-written cards.

    python -m scripts.eval_sms --no-llm     # retrieval only, free
    python -m scripts.eval_sms              # with DeepSeek (one call per message)
Each message is removed from the index while it is tested, so it never finds itself.
"""
import argparse

from core import sms

ap = argparse.ArgumentParser()
ap.add_argument("--no-llm", action="store_true")
args = ap.parse_args()

index = sms.load_index()
tp = fn = fp = tn = 0
for p in index.passages:
    is_scam = p["label"] != "safe"
    r = sms.classify(index, "", p["raw"], use_llm=not args.no_llm, exclude_group=p["group"])
    flagged = r["verdict"] != "SAFE"
    if is_scam:
        tp += flagged
        fn += not flagged
        if not flagged:
            print(f"MISSED      {r['score']:.2f}  {p['raw'][:90]}")
    else:
        fp += flagged
        tn += not flagged
        if flagged:
            print(f"FALSE ALARM {r['score']:.2f}  {r['verdict']}  {p['raw'][:90]}")
print(f"\nscams caught {tp}/{tp + fn}   genuine flagged {fp}/{fp + tn}")
