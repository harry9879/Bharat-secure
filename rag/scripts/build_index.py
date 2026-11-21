"""Builds the retrieval index from every knowledge source (core/knowledge.py).

Run from rag/:  .venv/Scripts/python -m scripts.build_index
Re-run after adding audio (scripts/label_audio.py) or editing patterns.
Writes index/vectors.npy and index/passages.jsonl.
"""

import time
from collections import Counter

from core.index import Index, embed
from core.knowledge import all_passages


def main():
    passages = all_passages()
    print("passages by source:", dict(Counter(p["source"] for p in passages)))
    print("passages by label: ", dict(Counter(p["label"] for p in passages)))
    start = time.time()
    vectors = embed([p["text"] for p in passages], "passage")
    Index(vectors, passages).save()
    print(f"embedded {len(passages)} passages in {time.time() - start:.0f}s -> index/")


if __name__ == "__main__":
    main()
