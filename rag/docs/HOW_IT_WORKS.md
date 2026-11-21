# How the RAG scam scorer works

## The problem
During a phone or WhatsApp call, decide continuously whether the caller is running a scam,
which kind (Phishing/OTP, Digital arrest, Banking, Other), and tell the user why, without
flagging genuine bank, police, delivery or family calls.

## Why RAG instead of a trained model
A trained model needs lots of new labelled calls to retrain. RAG (Retrieval-Augmented Generation) needs none:
- **Retrieval** finds the labelled examples most similar in *meaning* to what is being said,
  across Hindi, English and Hinglish (a multilingual embedding model).
- **Generation**: an LLM (DeepSeek) reads the call, those examples and a red-flag guide,
  and explains its verdict in plain words.
- **New scam scripts are added by adding examples** (a text line or an audio file), with no
  retraining.

## Pipeline, step by step

### 1. Speech to Roman Hinglish (`core/transcribe.py`, `core/translit.py`)
- Every ~5 s of call audio is sent to **Whisper large-v3-turbo on Groq**, the fastest hosted
  Whisper; it understands Hindi, English and code-mixed speech.
- **Speakerphone audio is ~10× quieter** than normal speech (measured on our phone tests:
  RMS 40–130 vs 600–1300), so it is boosted up to normal loudness first.
- Language is fixed to Hindi (`language=hi`), so Hinglish is neither translated to English nor
  written in Urdu script (both happened with auto-detection). The Devanagari output goes through
  our converter (dictionary for common words and English loanwords, plus letter-by-letter
  conversion with Hindi schwa deletion):
  `हम आपको अरेस्ट कर रहे हैं` → `hum aapko arrest kar rahe hain`.

**Guarding against made-up words (hallucinations).** Whisper invents text from silence and
noise. A live test in an empty room produced a fake 84% "OTP scam", because the first version
gave Whisper a hint prompt containing "account block ho jayega, OTP bata dijiye" and Whisper
repeated it. Measured fixes, in order:
1. **No prompt at all.** Whisper repeats its prompt on silence *and* inside real speech (a
   neutral "Achha, bataiye" turned up in the middle of real recordings).
2. **Room-noise check** before calling Whisper: the quietest 20% of the last ~30 s is the room's
   noise level, and only 100 ms frames 2.5× louder than that (and above 30) count as speech; a
   chunk needs 0.6 s of them. Digital silence is ignored when measuring the room, so steady fan
   noise sets the level and is rejected.
3. **Known phantom phrases** are dropped ("Thank you.", "झाल"/"jhaal", …), and segments Whisper
   scores as garbage (very low confidence, repetitive loops).
4. **Pieces under 3 words are ignored**: a sudden bang passes any loudness check and becomes one
   or two random words ("prachchh").
Note: on Groq, `no_speech_prob` is always 0 and confidence scores overlap between real Hinglish
(down to −2.0) and invented words (−0.4), so the room-noise check (2) does most of the work.
Tested: silence, steady fan noise and sudden loud noise all leave the score at 0.
- The **same** transcriber is used for the labelled recordings and for live calls, so the
  knowledge base and live text look alike.

### 2. Knowledge base (`core/knowledge.py`)
| Source | Passages | Notes |
|---|---:|---|
| `data/scams_call.txt` | 54 | team-supplied: 31 scams (types in `scams_call_types.csv`) + 23 genuine |
| `data/audio/` | 4 | real scam recordings, transcribed as above, type suggested by DeepSeek |
| `knowledge/patterns.jsonl` | 38 | hand-written cards: 24 scam, 14 genuine (incl. real bank warnings, police about your own complaint) |

Every passage is cleaned to the same form (Roman, lowercase, no punctuation) and embedded with
**multilingual-e5-small** ("passage: …" / "query: …" prefixes, as that model expects).

### 3. Retrieval score (`core/retrieval.py`)
The last ~90 words of the call (where a scam turn shows up) are embedded and the 10 nearest
passages are found by cosine similarity. Each neighbour votes with weight
`exp((similarity − best) / 0.03)`, so the closest examples count most.
**Retrieval score = scam weight / total weight**; the type is the scam type with the most
weight. It takes a few milliseconds and runs on every chunk.

### 4. DeepSeek judge (`core/judge.py`)
Gets the whole call so far, the top 6 retrieved examples (with labels) and the red-flag guide
(`knowledge/red_flags.md`, including what genuine calls look like), and must answer in JSON:
`scam_probability`, `type`, `red_flags`, `reason`, `advice`. Temperature 0.
To keep it fast and cheap, it is asked at most every 15 s, or sooner when the retrieval
score jumps by 0.2 or more.

### 5. Continuous score (`core/session.py`)
```
raw   = retrieval                                    until DeepSeek has answered once
raw   = 0.35 × retrieval + 0.65 × DeepSeek           after that
score = score + 0.6 × (raw − score)    if raw is higher   (rises fast)
score = score + 0.15 × (raw − score)   if raw is lower    (falls slowly)
```
Level: SAFE < 65% ≤ WARNING < 75% ≤ SCAM (WARNING was 45% during the first evaluation). The slow fall means one polite sentence from a
scammer doesn't switch the alarm off. All numbers are in `core/config.py`.

### 6. Delivery
- `scripts/live_mic.py`: laptop microphone, prints the score bar live.
- `server.py`: HTTP API, so the phone app can send 5-second WAV chunks and show the score.

## How it is evaluated (`scripts/evaluate.py`)
- Calls are streamed in 10-word pieces; a call counts as flagged if its score ever reaches
  the level.
- **Leave-one-out:** while a team call or recording is being tested, it is removed from the
  search; otherwise it would just find itself.
- The hand-written pattern cards are left out of all tests, because they were written after
  seeing the test calls.
- Test sets: the team's 54 calls and the recordings.
Results are in the README section "Results".

## Limits
- Needs internet; call audio goes to Groq and text to DeepSeek. There is no offline scam check.
- Test sets are small (≈100 calls), so each number moves a few percent per call.
- An LLM can still be fooled or over-cautious; the retrieval score and the slow-falling
  smoothing make single bad answers less harmful.
- The 4 recordings are labelled "scam" by the team; their scam types come from DeepSeek and
  should be checked by hand.
