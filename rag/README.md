# BharatSecure RAG: real-time scam-call scoring

Listens to a call as it happens, writes it down in **Roman Hinglish**, and gives a
**continuous scam score (0–100%)** with a level (SAFE / WARNING / SCAM), the scam
type (Phishing/OTP, Digital arrest, Banking, Other) and a plain-language reason.

```
call audio ─► Whisper large-v3-turbo (Groq) ─► Roman Hinglish
                                                   │
         ┌─────────────────────────────────────────┘
         ├─► ① retrieval: nearest labelled scam / genuine examples   (every ~5 s)
         └─► ② DeepSeek judge: transcript + retrieved examples + red-flag guide  (every ~15 s or on a jump)
                    ▼
            continuous score = blend of ① and ②, rises fast, falls slowly
```


---

## 1. One-time setup

Open a terminal in the `rag` folder.

**a. Python environment** (already done on this laptop; `.venv` exists):
```bash
python -m venv .venv
.venv/Scripts/pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv/Scripts/pip install -r requirements.txt
```

**b. Your API keys.** Copy `.env.example` to `.env` and paste your keys after the `=`:
```
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
```
`.env` stays on this laptop and is ignored by git. Never put keys in the app or in chat.

**c. Build the knowledge index** (about 1 minute; downloads the 470 MB embedding model the first time):
```bash
.venv/Scripts/python -m scripts.build_index
```

## 2. Add your scam recordings to the dataset

Transcribes every file in `C:\Users\asus\Desktop\ML\audiodata` with the same model used
for live calls, labels them as scams (type suggested by DeepSeek), copies them to `data/audio/`
and writes `data/audio_labels.csv`:
```bash
.venv/Scripts/python -m scripts.label_audio
```
Open `data/audio_labels.csv`, check each `type` (phishing_otp / digital_arrest / banking /
other_scam). If you change one, set its `type_source` to `manual` so re-runs keep it.
Then rebuild the index:
```bash
.venv/Scripts/python -m scripts.build_index
```
New recordings later: drop them in the folder and run both commands again.

## 3. Use it

**Live demo on the laptop:** put the phone call on speaker next to the laptop:
```bash
.venv/Scripts/python -m scripts.live_mic
```
Every 5 seconds it prints the new words and a coloured score bar; when it's a scam it shows
why and what to do. Ctrl+C stops it and saves the call to `data/live/`.

**Type a call to test** (no audio needed):
```bash
.venv/Scripts/python -m scripts.try_text
```

**Server for the phone app** (phone and laptop on the same Wi-Fi):
```bash
.venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Open `http://<laptop-ip>:8000/docs` to try it in a browser. A call is
`POST /sessions` → many `POST /sessions/{id}/audio` (a 16 kHz mono WAV every ~5 s) →
`DELETE /sessions/{id}`. Each response has `score`, `level`, `type_name`, `new_text`,
`transcript` and, once DeepSeek has spoken, `details.llm.reason` / `advice`.

## 3b. Connect the BharatSecure phone app

The app transcribes the call itself (online Whisper) and sends **each new sentence as text**
to this server, which replies with the score, level, type and DeepSeek's reason.

1. Phone and laptop on the **same phone hotspot** (college/library Wi-Fi blocks devices from
   reaching each other).
2. Laptop IP: `ipconfig` → "IPv4 Address" under Wi-Fi.
3. Start the server: `.venv/Scripts/python -m uvicorn server:app --host 0.0.0.0 --port 8000`
4. In the app, **Laptop AI (RAG server)** card: type `<laptop-ip>:8000`, tap **Save**, then
   **Test connection**. It should say "✅ Connected · 11096 examples · DeepSeek on".
5. Start Protection Mode on a call. The Protection card shows a **💻 Laptop AI (RAG)** panel with
   the live score, level, type, "Why" and "What to do"; a rise to WARNING or SCAM raises an alert.
   If the laptop can't be reached the panel says "Laptop offline" and no scam check runs.

## 4. Check how well it works
```bash
.venv/Scripts/python -m scripts.evaluate --no-llm   # retrieval only, free and fast
.venv/Scripts/python -m scripts.evaluate            # with DeepSeek (a few hundred API calls)
```
Tests the team's 54 calls in `data/scams_call.txt`, the recordings, and 40 hand-written calls,
each streamed in 10-word pieces, without letting the system look itself up.

## Results

Index: team calls, recordings and pattern cards, built in 93 s on the
RTX 3050. Thresholds fixed in advance (WARNING 0.45, SCAM 0.75), **not** tuned on these tests.

**Retrieval only** (`scripts.evaluate --no-llm`):

| Test set | Scams caught (WARNING / SCAM) | False alarms on genuine calls (WARNING / SCAM) |
|---|---:|---:|
| Team calls, `scams_call.txt` (leave-one-out) | 26/31 · 8/31 | 2/23 · 1/23 |
| 40 hand-written calls | **20/24** · 14/24 | 5/16 · 3/16 |
| *For comparison: trained ML model + rules (on the phone), hand-written* | *10/24* | *0/16* |

Retrieval alone catches twice as many realistic Hinglish scams as the trained model, but it
also flags genuine calls that *sound* like scams: a real cyber-cell refund, a real income-tax
refund, a delivery boy, a courier, a society maintenance reminder. Word-meaning similarity
can't separate "the cyber cell froze the fraudster's account" from a cyber-cell scam; the
DeepSeek judge, with its genuine-call guide, is meant to. Missed scams were mostly
"other" (fake relative, task jobs, extortion) and one vague "account frozen" call.

Threshold trade-off, all 94 test calls (55 scams, 39 genuine), retrieval only:

| WARNING at | 0.35 | 0.45 | 0.55 | 0.65 | 0.75 |
|---|---:|---:|---:|---:|---:|
| scams caught | 51 | 46 | 40 | 34 | 22 |
| genuine calls flagged | 12 | 7 | 6 | 6 | 4 |

**Retrieval + DeepSeek judge** (`scripts.evaluate`; index now also has the 4 recordings,
11,096 passages):

| Test set | Scams caught (WARNING / SCAM) | False alarms on genuine calls (WARNING / SCAM) | Type right |
|---|---:|---:|---:|
| Real scam recordings (leave-one-out) | **4/4** · 4/4 | n/a | 4/4 |
| Team calls, `scams_call.txt` (leave-one-out) | **31/31** · 13/31 | 1/23 · **0/23** | 28/31 |
| 40 hand-written calls | **24/24** · 18/24 | 2/16 · **0/16** | 24/24 |
| *Trained ML model + rules (on the phone), hand-written* | *10/24* | *0/16* | |

Every one of the 59 scams reaches WARNING, and **no genuine call reaches SCAM**. The three
genuine calls that reach WARNING are refund/complaint calls that sound official: an order refund
(peak 0.48), a real cyber-cell refund (0.54) and a real income-tax refund (0.69). DeepSeek removed
most of retrieval's false alarms (delivery boy, courier, society maintenance) while catching more.

Threshold trade-off with DeepSeek, all 98 calls (59 scams, 39 genuine):

| WARNING at | 0.45 | 0.55 | 0.65 | 0.70 | 0.75 |
|---|---:|---:|---:|---:|---:|
| scams caught | 59 | 58 | 51 | 44 | 35 |
| genuine calls flagged | 3 | 1 | 1 | 0 | 0 |

The tables above used WARNING 0.45 / SCAM 0.75, set before testing.

**Current setting: WARNING at 0.65** (SCAM unchanged at 0.75), chosen by the team after
seeing the trade-off, to warn on fewer genuine calls.

After the hallucination fix (no Whisper prompt, Hindi forced, room-noise check; recordings
re-transcribed and index rebuilt), re-run with DeepSeek:

| Test set | Scams caught (WARNING / SCAM) | False alarms on genuine calls (WARNING / SCAM) | Type right |
|---|---:|---:|---:|
| Real scam recordings | 4/4 · 4/4 | n/a | 4/4 |
| Team calls, `scams_call.txt` | 25/31 · 13/31 | **0/23** · 0/23 | 23/25 |
| 40 hand-written calls | 22/24 · 18/24 | **0/16** · 0/16 | 22/22 |
| **All** | **51/59** · 35/59 | **0/39** · 0/39 | |

Missed at WARNING (peak 0.51–0.64, just under the line): a vague "account verification pending",
a YouTube task job, "serious complaint registered", "account frozen", an income-tax PAN call, a
passport fee, a "sent by mistake" UPI call and a fake-son emergency. Because 0.65 was
picked looking at these same calls, this result is optimistic: a fresh set of
calls is needed to confirm it. Caution: these test sets are small (98 calls), so a single call
moves a rate by 1–6%, and the recordings are only 4.

## Files

| Path | What |
|---|---|
| `core/config.py` | every setting: models, thresholds, smoothing |
| `core/transcribe.py` | Whisper turbo on Groq, volume boost, silence check |
| `core/translit.py`, `core/text.py` | Devanagari → Roman Hinglish, text cleanup |
| `core/knowledge.py` | collects all labelled examples |
| `core/index.py`, `core/retrieval.py` | embeddings, search, retrieval score |
| `core/judge.py` | DeepSeek judge |
| `core/session.py` | one call → continuous score |
| `knowledge/red_flags.md` | the red-flag guide the LLM reads |
| `knowledge/patterns.jsonl` | hand-written scam / genuine example cards |
| `data/scams_call.txt`, `data/scams_call_types.csv` | team's calls and their scam types |
| `data/audio/`, `data/audio_labels.csv` | real scam recordings and transcripts |
| `server.py`, `scripts/` | server, live demo, text tester, labelling, evaluation |

## Privacy
In this mode, call audio goes to Groq and the transcript to DeepSeek.
