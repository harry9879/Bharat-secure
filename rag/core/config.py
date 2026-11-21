"""Paths, model names and tunable settings for the RAG pipeline, in one place."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent          # rag/
REPO = ROOT.parent                                     # bharatsecure/
load_dotenv(ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()

# --- Speech-to-text -----------------------------------------------------------
GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
WHISPER_MODEL = "whisper-large-v3-turbo"   # Groq's fastest Whisper
# No prompt. Whisper repeats its prompt on silence AND inside real speech: a
# prompt with "account block ho jayega, OTP bata dijiye" turned a silent room
# into a fake 84% scam, and even a neutral one ("Achha, bataiye") showed up in
# the middle of real recordings. Without a prompt, language is fixed to Hindi so
# Hinglish isn't translated to English or written in Urdu script; Devanagari is
# then converted to Roman Hinglish by core/translit.py.
WHISPER_PROMPT = ""
WHISPER_LANGUAGE = "hi"
# Whisper's confidence, per segment. Measured on Groq: no_speech_prob is always 0,
# and avg_logprob overlaps (real speech -0.1 to -2.0, invented "jhaal" -0.4), so
# these only drop garbage; the room-noise check in session.py is the real guard.
MAX_NO_SPEECH_PROB = 0.5
MIN_AVG_LOGPROB = -2.5
MAX_COMPRESSION_RATIO = 3.0   # higher = repetitive loops ("hello hello hello …")
# Anything Whisper says is not one of these is noise turned into words
# ("tunggu", "proprio para").
ALLOWED_LANGUAGES = {"hindi", "english", "urdu", "punjabi", "hi", "en", "ur", "pa"}
# Speech detection: a 100 ms frame counts as speech when it is this many times
# louder than the room's noise floor (measured as the call goes), and above 30.
SPEECH_OVER_NOISE = 2.5
# A sudden bang passes any loudness check and Whisper turns it into one or two
# random words ("prachchh", "kar do"). Pieces shorter than this are ignored;
# 5 s of real speech nearly always has more, and "haan ji" carries no scam signal.
MIN_PIECE_WORDS = 3

# --- LLM judge ----------------------------------------------------------------
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# --- Retrieval ----------------------------------------------------------------
EMBED_MODEL = "intfloat/multilingual-e5-small"   # 118M params, Hindi/English/Hinglish
INDEX_DIR = ROOT / "index"
KNOWLEDGE_DIR = ROOT / "knowledge"
DATA_DIR = ROOT / "data"
TOP_K = 10
# Neighbours are weighted by exp((similarity - best) / TEMPERATURE): the
# closest examples count most.
KNN_TEMPERATURE = 0.03
# Retrieval looks at the most recent part of the call, where a scam turn shows.
QUERY_WINDOW_WORDS = 90

# --- Continuous score -----------------------------------------------------------
LLM_EVERY_SECONDS = 15        # DeepSeek is asked at most this often…
LLM_ON_JUMP = 0.20            # …or sooner when the retrieval score jumps this much
LLM_WEIGHT = 0.65             # final = (1 - w) * retrieval + w * LLM, once the LLM has spoken
RISE, FALL = 0.6, 0.15        # smoothing: the shown score rises fast, falls slowly
# Levels on the 0..1 score. WARNING was 0.45; set to 0.65 at the team's request
# (see README "Results": 51/59 scams and 1/39 genuine calls then reach WARNING).
WARN_AT, SCAM_AT = 0.65, 0.75

SCAM_TYPES = ["phishing_otp", "digital_arrest", "banking", "other_scam"]
TYPE_NAMES = {"safe": "Safe", "phishing_otp": "Phishing / OTP", "digital_arrest": "Digital arrest",
              "banking": "Banking fraud", "other_scam": "Other scam"}
