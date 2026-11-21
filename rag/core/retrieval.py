"""Retrieval score: the nearest labelled examples vote on the current call.

score = share of scam among the top-k neighbours, each weighted by
exp((similarity - best similarity) / temperature), so the closest examples
count most. Type = the scam type with the most weight among scam neighbours.
"""

import math
from collections import defaultdict

from . import config


def knn_score(neighbours):
    """neighbours: [(similarity, passage)] best first. Returns (score 0..1, type or None, evidence)."""
    if not neighbours:
        return 0.0, None, []
    best = neighbours[0][0]
    total, scam, by_type = 0.0, 0.0, defaultdict(float)
    for sim, p in neighbours:
        w = math.exp((sim - best) / config.KNN_TEMPERATURE)
        total += w
        if p["label"] != "safe":
            scam += w
            by_type[p["label"]] += w
    score = scam / total
    kind = max(by_type, key=by_type.get) if by_type else None
    evidence = [dict(similarity=round(s, 3), label=p["label"], source=p["source"], text=p["text"][:200])
                for s, p in neighbours[:5]]
    return score, kind, evidence
