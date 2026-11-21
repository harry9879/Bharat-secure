"""LLM judge: DeepSeek reads the call so far, the retrieved examples and the
red-flag guide, and returns a scam probability with reasons (JSON)."""

import json
import time

import requests

from . import config

RED_FLAGS = (config.KNOWLEDGE_DIR / "red_flags.txt").read_text(encoding="utf-8")

SYSTEM = f"""You protect people in India from phone scams. You read a live phone-call transcript
(Roman Hinglish/English, from speech recognition, so expect some wrong words) and judge whether
the call is a scam so far. Use the red-flag guide and the retrieved labelled examples.

Be careful NOT to flag genuine calls: banks warning customers, real police about a complaint the
user filed, deliveries, appointments, interviews, family and friends. Mentioning a bank, police,
OTP or a parcel is not enough on its own; what matters is a request for a secret, money, or a
link/app action under pressure or threat.

{RED_FLAGS}

Reply with JSON only:
{{"scam_probability": <0-100>,
  "type": "safe" | "phishing_otp" | "digital_arrest" | "banking" | "other_scam",
  "red_flags": ["short phrases quoted or paraphrased from the call"],
  "reason": "one or two plain sentences for the user",
  "advice": "one short sentence telling the user what to do now"}}"""


class JudgeError(RuntimeError):
    pass


def judge(transcript: str, neighbours) -> dict:
    if not config.DEEPSEEK_API_KEY:
        raise JudgeError("DEEPSEEK_API_KEY is missing: add it to rag/.env")
    examples = "\n".join(f"- [{p['label']}] {p['text'][:220]}" for _, p in neighbours[:6])
    user = f"Retrieved similar labelled examples:\n{examples}\n\nCall transcript so far:\n{transcript[-3000:]}"
    start = time.time()
    resp = requests.post(
        config.DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={"model": config.DEEPSEEK_MODEL, "temperature": 0, "max_tokens": 300,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]},
        timeout=30,
    )
    if resp.status_code != 200:
        raise JudgeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:200]}")
    content = resp.json()["choices"][0]["message"]["content"]
    try:
        out = json.loads(content)
    except json.JSONDecodeError as e:
        raise JudgeError(f"DeepSeek returned non-JSON: {content[:200]}") from e
    prob = float(out.get("scam_probability", 0)) / 100.0
    kind = out.get("type", "safe")
    if kind not in config.SCAM_TYPES:
        kind = "safe" if prob < 0.5 else "other_scam"
    return dict(score=max(0.0, min(1.0, prob)), type=kind, red_flags=out.get("red_flags", [])[:5],
                reason=out.get("reason", ""), advice=out.get("advice", ""), seconds=round(time.time() - start, 2))
