"""SMS scam classification with RAG.

  1. retrieval: the nearest labelled SMS (scam / genuine) in a separate SMS index vote on the message
  2. DeepSeek judge: message + sender + on-device rule hints + retrieved examples + SMS red-flag guide
  3. blend into a score and a verdict SAFE / SUSPICIOUS / SCAM

The SMS index is separate from the call index (core/index.py) so call transcripts and SMS don't mix.
Sources: knowledge/sms_patterns.jsonl (hand-written cards) and the ScamShield labelled corpus.
"""

import json
import re
import time

import requests

from . import config
from .index import Index, embed
from .retrieval import knn_score

SMS_INDEX_DIR = config.INDEX_DIR / "sms"
CORPUS = config.REPO / "scamshield" / "backend" / "tests" / "corpus" / "sms_corpus.jsonl"
RED_FLAGS = (config.KNOWLEDGE_DIR / "sms_red_flags.txt").read_text(encoding="utf-8")

SMS_WARN_AT, SMS_SCAM_AT = 0.45, 0.75           # with the LLM
SMS_WARN_AT_NO_LLM, SMS_SCAM_AT_NO_LLM = 0.60, 0.85   # retrieval alone is less reliable
RETRIEVAL_WEIGHT = 0.35

_DIGITS = re.compile(r"\d{4,}")
_SPACES = re.compile(r"\s+")


def clean_sms(text: str) -> str:
    """Light cleaning: keep links, brand names and words (they carry the signal); mask long numbers."""
    text = _DIGITS.sub("0000", text.lower())
    return _SPACES.sub(" ", text).strip()[:600]


# ---------------------------------------------------------------- knowledge + index
def passages():
    for line in open(config.KNOWLEDGE_DIR / "sms_patterns.jsonl", encoding="utf-8"):
        p = json.loads(line)
        yield dict(id=f"card/{p['id']}", source="card", group=f"card/{p['id']}", label=p["label"],
                   text=clean_sms(p["text"]), raw=p["text"])
    if CORPUS.exists():
        for i, line in enumerate(open(CORPUS, encoding="utf-8")):
            if not line.strip():
                continue
            r = json.loads(line)
            label = "safe" if r["label"] != "scam" else "scam_corpus"   # the corpus has no scam type
            yield dict(id=f"corpus/{i}", source="corpus", group=f"corpus/{i}", label=label,
                       text=clean_sms(r["text"]), raw=r["text"])


def build_index():
    ps = list(passages())
    idx = Index(embed([p["text"] for p in ps], "passage"), ps)
    idx.save(SMS_INDEX_DIR)
    return idx


def load_index():
    return Index.load(SMS_INDEX_DIR)


# ---------------------------------------------------------------- judge
SYSTEM = f"""You protect people in India from scam SMS. You read one SMS (English, Hindi or Hinglish) with
its sender, plus hints from the phone's own rule checks and similar labelled messages found by search.
Decide whether the SMS is a scam.

{RED_FLAGS}

Reply with JSON only:
{{"scam_probability": <0-100>,
  "type": "safe" | "phishing_otp" | "digital_arrest" | "banking" | "other_scam",
  "red_flags": ["short phrases from the SMS"],
  "reason": "one or two plain sentences for the user",
  "advice": "one short sentence telling the user what to do"}}"""


class JudgeError(RuntimeError):
    pass


def judge(sender: str, text: str, in_contacts: bool, rule_hints: list[str], neighbours) -> dict:
    if not config.DEEPSEEK_API_KEY:
        raise JudgeError("DEEPSEEK_API_KEY is missing: add it to rag/.env")
    examples = "\n".join(f"- [{p['label']}] {p.get('raw', p['text'])[:220]}" for _, p in neighbours[:6])
    hints = "; ".join(rule_hints) if rule_hints else "none"
    user = (f"Similar labelled messages:\n{examples}\n\n"
            f"Sender: {sender}\nSender is {'SAVED in the user contacts' if in_contacts else 'NOT in the user contacts'}\n"
            f"On-device rule hints (may be wrong): {hints}\n\nSMS:\n{text[:1500]}")
    start = time.time()
    resp = requests.post(
        config.DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={"model": config.DEEPSEEK_MODEL, "temperature": 0, "max_tokens": 300,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]},
        timeout=20,
    )
    if resp.status_code != 200:
        raise JudgeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        out = json.loads(resp.json()["choices"][0]["message"]["content"])
        prob = float(out.get("scam_probability", 0)) / 100.0
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        raise JudgeError(f"DeepSeek returned unusable output: {e}") from e
    kind = out.get("type", "safe")
    if kind not in config.SCAM_TYPES:
        kind = "safe" if prob < 0.5 else "other_scam"
    return dict(score=max(0.0, min(1.0, prob)), type=kind, red_flags=list(out.get("red_flags", []))[:5],
                reason=str(out.get("reason", "")), advice=str(out.get("advice", "")),
                seconds=round(time.time() - start, 2))


# ---------------------------------------------------------------- classify
def retrieve(index: Index, text: str, exclude_group: str | None = None):
    q = embed([clean_sms(text)], "query")[0]
    return index.search(q, k=config.TOP_K, exclude_group=exclude_group)


def verdict_for(score: float, llm_used: bool) -> str:
    warn, scam = (SMS_WARN_AT, SMS_SCAM_AT) if llm_used else (SMS_WARN_AT_NO_LLM, SMS_SCAM_AT_NO_LLM)
    return "SCAM" if score >= scam else "SUSPICIOUS" if score >= warn else "SAFE"


def classify(index: Index, sender: str, text: str, in_contacts: bool = False, rule_hints: list[str] | None = None,
             use_llm: bool = True, exclude_group: str | None = None) -> dict:
    neighbours = retrieve(index, text, exclude_group)
    ret_score, ret_type, evidence = knn_score(neighbours)
    if ret_type == "scam_corpus":
        ret_type = "other_scam"
    llm, llm_error = None, None
    if use_llm:
        try:
            llm = judge(sender, text, in_contacts, rule_hints or [], neighbours)
        except (JudgeError, requests.RequestException) as e:
            llm_error = str(e)[:200]
    score = ret_score if llm is None else RETRIEVAL_WEIGHT * ret_score + (1 - RETRIEVAL_WEIGHT) * llm["score"]
    verdict = verdict_for(score, llm is not None)
    kind = (llm["type"] if llm and llm["type"] != "safe" else ret_type) if verdict != "SAFE" else "safe"
    return dict(
        verdict=verdict, score=round(score, 3), type=kind, type_name=config.TYPE_NAMES.get(kind, kind),
        reason=llm["reason"] if llm else "", advice=llm["advice"] if llm else "",
        red_flags=llm["red_flags"] if llm else [], llm_used=llm is not None, llm_error=llm_error,
        retrieval=dict(score=round(ret_score, 3), type=ret_type, evidence=evidence),
    )
