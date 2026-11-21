"""HTTP server for real-time scam scoring (for the phone app or any client).

Run from rag/:
    .venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8000
Then open http://<laptop-ip>:8000/docs to try every endpoint in the browser.

Flow for a call:
    POST /sessions                      -> {"session_id": ...}
    POST /sessions/{id}/audio  (file)   -> score update; send every ~5 s of audio
    POST /sessions/{id}/text   (json)   -> score update from text (testing)
    GET  /sessions/{id}                 -> latest state
    DELETE /sessions/{id}               -> end the call
"""

import io
import uuid
import wave

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from core import config, sms
from core.index import Index, embed
from core.session import CallSession
from core.transcribe import TranscriptionError, transcribe_bytes

app = FastAPI(title="BharatSecure RAG scam scorer")
index = Index.load()
embed(["warm up"], "query")  # load the embedding model before the first call
sessions: dict[str, CallSession] = {}


class TextIn(BaseModel):
    text: str


class SmsIn(BaseModel):
    sender: str = ""
    text: str
    in_contacts: bool = False
    rule_hints: list[str] = []   # on-device rule findings, e.g. "KYC_BLOCK_THREAT: ..."


try:
    sms_index = sms.load_index()
except FileNotFoundError:
    sms_index = None   # run: python -m scripts.build_sms_index


@app.post("/sms/classify")
def sms_classify(body: SmsIn):
    """One SMS in, verdict (SAFE / SUSPICIOUS / SCAM) + score + reason + advice out."""
    if sms_index is None:
        raise HTTPException(503, "SMS index not built: run python -m scripts.build_sms_index")
    if not body.text.strip():
        return dict(verdict="SAFE", score=0.0, type="safe", type_name="Safe", reason="", advice="", red_flags=[],
                    llm_used=False, llm_error=None, retrieval=None)
    return sms.classify(sms_index, body.sender, body.text, body.in_contacts, body.rule_hints)


@app.get("/health")
def health():
    return dict(ok=True, passages=len(index.passages), sms_passages=len(sms_index.passages) if sms_index else 0,
                groq_key=bool(config.GROQ_API_KEY),
                deepseek_key=bool(config.DEEPSEEK_API_KEY), whisper=config.WHISPER_MODEL,
                llm=config.DEEPSEEK_MODEL, embed=config.EMBED_MODEL)


@app.post("/sessions")
def start(use_llm: bool = True):
    sid = uuid.uuid4().hex[:12]
    sessions[sid] = CallSession(index, use_llm=use_llm)
    return {"session_id": sid}


def get(sid: str) -> CallSession:
    if sid not in sessions:
        raise HTTPException(404, "unknown session")
    return sessions[sid]


@app.post("/sessions/{sid}/audio")
async def audio(sid: str, file: UploadFile = File(...)):
    """A chunk of call audio. 16 kHz mono 16-bit WAV gets the speakerphone
    volume boost and silence check; any other format goes straight to Whisper."""
    s = get(sid)
    data = await file.read()
    try:
        with wave.open(io.BytesIO(data)) as w:
            if w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2:
                return s.add_audio(np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16))
    except wave.Error:
        pass
    try:
        result = transcribe_bytes(data, filename=file.filename or "chunk.wav")
    except TranscriptionError as e:
        raise HTTPException(502, str(e))
    return s.add_text(result["text"], stt_seconds=result["seconds"])


@app.post("/sessions/{sid}/text")
def text(sid: str, body: TextIn):
    return get(sid).add_text(body.text)


@app.get("/sessions/{sid}")
def state(sid: str):
    s = get(sid)
    return dict(transcript=s.transcript, score=round(s.score, 3), peak=round(s.peak, 3), history=s.history,
                llm=s.last_llm)


@app.delete("/sessions/{sid}")
def end(sid: str):
    s = sessions.pop(sid, None)
    return dict(ended=s is not None, peak=round(s.peak, 3) if s else None)
