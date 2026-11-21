"""Build the SMS index: python -m scripts.build_sms_index (from rag/)"""
import time

from core import sms

if __name__ == "__main__":
    t = time.time()
    idx = sms.build_index()
    labels = {}
    for p in idx.passages:
        labels[p["label"]] = labels.get(p["label"], 0) + 1
    print(f"SMS index: {len(idx.passages)} passages in {time.time() - t:.0f}s  {labels}")
