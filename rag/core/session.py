"""One live call: audio or text in, a continuous scam score out.

Every new piece of transcript (~5 s of speech):
  1. retrieval score on the latest part of the call (fast, local, every time)
  2. DeepSeek judge on the whole call so far, at most every LLM_EVERY_SECONDS,
     or sooner when the retrieval score jumps
  3. raw = retrieval alone until the judge has spoken, then
     (1 - LLM_WEIGHT) * retrieval + LLM_WEIGHT * judge
  4. the shown score rises quickly and falls slowly (RISE / FALL), so one
     calm sentence from a scammer doesn't reset the alarm
Level: SAFE < WARN_AT <= WARNING < SCAM_AT <= SCAM.
"""

import time

import numpy as np

from . import config
from .index import Index, embed
from .judge import JudgeError, judge
from .retrieval import knn_score
from .text import clean, last_words
from .transcribe import NoiseFloor, TranscriptionError, boost, frame_rms, pcm_to_wav, transcribe_bytes


def level_of(score: float) -> str:
    return "SCAM" if score >= config.SCAM_AT else "WARNING" if score >= config.WARN_AT else "SAFE"


class CallSession:
    def __init__(self, index: Index, use_llm: bool = True, exclude_group: str | None = None,
                 exclude_sources: tuple[str, ...] = ()):
        self.index = index
        self.use_llm = use_llm and bool(config.DEEPSEEK_API_KEY)
        # Only used by evaluation (leave-one-out); live calls search everything.
        self.exclude_group = exclude_group
        self.exclude_sources = exclude_sources
        self.pieces: list[str] = []
        self.score = 0.0
        self.peak = 0.0
        self.last_llm = None
        self.last_llm_time = 0.0
        self.last_retrieval = 0.0
        self.history: list[dict] = []
        self.noise = NoiseFloor()

    @property
    def transcript(self) -> str:
        return " ".join(self.pieces)

    def add_audio(self, samples: np.ndarray, sample_rate: int = 16000) -> dict:
        """int16 mono audio chunk -> update.

        Chunks with under 0.6 s clearly above the room's noise are skipped
        without calling Whisper; what Whisper returns is filtered again in
        transcribe_bytes (low confidence, wrong language, prompt echo).
        """
        rms = frame_rms(samples, sample_rate)
        speech = self.noise.speech_mask(rms)
        if speech.sum() < 6:
            return self._update(new_text="", note="silence")
        try:
            result = transcribe_bytes(pcm_to_wav(boost(samples, rms[speech]), sample_rate))
        except TranscriptionError as e:
            return self._update(new_text="", note=str(e))
        note = f"dropped: {result['dropped']}" if result["dropped"] else ""
        if len(clean(result["text"]).split()) < config.MIN_PIECE_WORDS:
            short = f"ignored short piece {result['text']!r}" if result["text"] else "no speech"
            return self._update(new_text="", note=(note + "; " + short).strip("; "))
        out = self.add_text(result["text"], stt_seconds=result["seconds"])
        out["note"] = note
        return out

    def add_text(self, text: str, stt_seconds: float | None = None) -> dict:
        piece = clean(text)
        if piece:
            self.pieces.append(piece)
        return self._update(new_text=piece, stt_seconds=stt_seconds)

    def _update(self, new_text: str, note: str = "", stt_seconds=None) -> dict:
        full = self.transcript
        if not full:
            return self._result(new_text, None, [], note, stt_seconds)
        start = time.time()
        query = embed([last_words(full, config.QUERY_WINDOW_WORDS)], "query")[0]
        neighbours = self.index.search(query, exclude_group=self.exclude_group, exclude_sources=self.exclude_sources)
        retrieval, r_type, evidence = knn_score(neighbours)
        retrieval_ms = round((time.time() - start) * 1000)

        now = time.time()
        if self.use_llm and new_text and (
            self.last_llm is None
            or now - self.last_llm_time >= config.LLM_EVERY_SECONDS
            or abs(retrieval - self.last_retrieval) >= config.LLM_ON_JUMP
        ):
            try:
                self.last_llm = judge(full, neighbours)
                self.last_llm_time = now
            except JudgeError as e:
                note = (note + " " + str(e)).strip()
        self.last_retrieval = retrieval

        if self.last_llm is not None:
            raw = (1 - config.LLM_WEIGHT) * retrieval + config.LLM_WEIGHT * self.last_llm["score"]
            kind = self.last_llm["type"] if self.last_llm["type"] != "safe" else r_type
        else:
            raw = retrieval
            kind = r_type
        rate = config.RISE if raw > self.score else config.FALL
        self.score += rate * (raw - self.score)
        self.peak = max(self.peak, self.score)
        details = dict(retrieval=round(retrieval, 3), retrieval_type=r_type, retrieval_ms=retrieval_ms,
                       llm=self.last_llm, raw=round(raw, 3), evidence=evidence)
        return self._result(new_text, kind, details, note, stt_seconds)

    def _result(self, new_text, kind, details, note, stt_seconds) -> dict:
        level = level_of(self.score)
        out = dict(new_text=new_text, transcript=self.transcript, score=round(self.score, 3),
                   peak=round(self.peak, 3), level=level,
                   type=None if level == "SAFE" else (kind or "other_scam"),
                   type_name=None if level == "SAFE" else config.TYPE_NAMES.get(kind or "other_scam"),
                   stt_seconds=stt_seconds, note=note, details=details)
        self.history.append({k: out[k] for k in ("score", "level", "type")})
        return out
