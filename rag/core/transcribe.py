"""Speech-to-text: Whisper large-v3-turbo on Groq, output in Roman Hinglish.

Used for BOTH the labelled audio dataset and live calls, so the knowledge
base and the live transcript look the same.
"""

import io
import re
import time
import wave

import numpy as np
import requests

from . import config
from .translit import to_roman

# Whisper invents these from silence or noise (the last ones measured on Groq
# with language=hi: silence and hiss both came back as "jhaal").
HALLUCINATIONS = {"thank you", "thanks for watching", "thank you for watching", "you", "bye",
                  "please subscribe", "subtitles by the amaraorg community", "dhanyavaad", "shukriya",
                  "", "jhaal", "jhaal jhaal", "jhal", "hmm", "um", "uh"}


class TranscriptionError(RuntimeError):
    pass


_PROMPT_WORDS = set(re.sub(r"[^a-z\s]", " ", config.WHISPER_PROMPT.lower()).split())


def _loose(word: str) -> str:
    # "achha" / "acha", "haan" / "han": drop h and doubled letters before comparing.
    return re.sub(r"(.)\1+", r"\1", word.replace("h", ""))


def _echoes_prompt(text: str) -> bool:
    """True when the output is mostly the prompt's own words (Whisper repeating it)."""
    if not _PROMPT_WORDS:
        return False
    words = re.sub(r"[^a-z\s]", " ", text.lower()).split()
    prompt = {_loose(w) for w in _PROMPT_WORDS}
    return len(words) > 0 and sum(_loose(w) in prompt for w in words) / len(words) >= 0.7


def _keep(segment: dict) -> bool:
    return (segment.get("no_speech_prob", 0.0) <= config.MAX_NO_SPEECH_PROB
            and segment.get("avg_logprob", 0.0) >= config.MIN_AVG_LOGPROB
            and segment.get("compression_ratio", 0.0) <= config.MAX_COMPRESSION_RATIO)


def transcribe_bytes(audio: bytes, filename: str = "audio.wav", prompt: str | None = None) -> dict:
    """Sends audio (wav/mp3/mp4/m4a/ogg/webm) to Groq.

    Returns {"text", "raw", "seconds", "dropped"}: "text" keeps only segments
    Whisper is confident are speech, in Hindi/English, that aren't an echo of
    the prompt; "dropped" says why anything was thrown away.
    """
    if not config.GROQ_API_KEY:
        raise TranscriptionError("GROQ_API_KEY is missing: add it to rag/.env")
    start = time.time()
    data = {"model": config.WHISPER_MODEL, "response_format": "verbose_json", "temperature": "0",
            "language": config.WHISPER_LANGUAGE}
    if prompt or config.WHISPER_PROMPT:
        data["prompt"] = prompt or config.WHISPER_PROMPT
    resp = requests.post(
        config.GROQ_TRANSCRIBE_URL,
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        files={"file": (filename, audio)},
        data=data,
        timeout=60,
    )
    if resp.status_code != 200:
        raise TranscriptionError(f"Groq HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    raw = body.get("text", "").strip()
    seconds = round(time.time() - start, 2)
    language = str(body.get("language", "")).lower()
    if language and language not in config.ALLOWED_LANGUAGES:
        return {"text": "", "raw": raw, "seconds": seconds, "dropped": f"language {language}"}

    segments = body.get("segments")
    if segments is None:  # no segment details: fall back to the whole text
        kept = [raw]
        low_confidence = 0
    else:
        kept = [s.get("text", "").strip() for s in segments if _keep(s)]
        low_confidence = len(segments) - len(kept)
    kept = [to_roman(t) for t in kept]
    kept = [t for t in kept if t.lower().strip(" .!?,।") not in HALLUCINATIONS and not _echoes_prompt(t)]
    text = " ".join(kept).strip()
    dropped = []
    if low_confidence:
        dropped.append(f"{low_confidence} low-confidence segment(s)")
    if raw and not text and not dropped:
        dropped.append("prompt echo / known hallucination")
    return {"text": text, "raw": raw, "seconds": seconds, "dropped": ", ".join(dropped)}


def transcribe_file(path) -> dict:
    with open(path, "rb") as fh:
        return transcribe_bytes(fh.read(), filename=str(path).split("\\")[-1].split("/")[-1])


def pcm_to_wav(samples: np.ndarray, sample_rate: int = 16000) -> bytes:
    """int16 mono samples -> wav bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(samples.astype(np.int16).tobytes())
    return buf.getvalue()


def frame_rms(samples: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """Loudness of each 100 ms frame."""
    frame = sample_rate // 10
    n = len(samples) // frame
    if n == 0:
        return np.zeros(0)
    frames = samples[: n * frame].astype(np.float64).reshape(n, frame)
    return np.sqrt((frames ** 2).mean(axis=1))


class NoiseFloor:
    """Tracks how loud the room is when nobody speaks.

    The quietest 20% of recent frames are taken as background noise (fan,
    traffic, line hiss). A fixed floor of 30 worked for the phone's call audio
    but not for a laptop mic, whose room noise passed it and was then boosted
    20x into "speech" that Whisper turned into words.
    """

    def __init__(self, history_frames: int = 300):  # last ~30 s
        self.history = np.zeros(0)
        self.size = history_frames

    def update(self, rms: np.ndarray) -> float:
        # Digital silence (a muted stream, RMS ~0) says nothing about room noise;
        # counting it pulled the floor to 0 and let steady fan noise through.
        self.history = np.concatenate([self.history, rms[rms > 5]])[-self.size:]
        return float(np.percentile(self.history, 20)) if len(self.history) else 0.0

    def speech_mask(self, rms: np.ndarray) -> np.ndarray:
        floor = self.update(rms)
        return rms > max(30.0, config.SPEECH_OVER_NOISE * floor)


def boost(samples: np.ndarray, speech_rms: np.ndarray, target_rms: float = 2000.0,
          max_gain: float = 20.0) -> np.ndarray:
    """Brings quiet (speakerphone) speech up to normal level, like the app does.
    The gain comes from the speech frames only, so pauses don't inflate it."""
    if len(speech_rms) == 0:
        return samples
    gain = float(np.clip(target_rms / speech_rms.mean(), 1.0, max_gain))
    return np.clip(samples.astype(np.float64) * gain, -32768, 32767).astype(np.int16)
