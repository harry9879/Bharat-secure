# BharatSecure — Judge Prep: Hardest Questions, Best Answers

No one can promise a 100% win — judging panels have tastes you can't control. What this
document *can* do is make sure you are never the team that gets caught out, and that every
answer lands on one of your five genuine strengths.

Everything here is checked against the code and the eval files in this repo.

---

## 0. The numbers cheat sheet — memorise these six

| Fact | Number | Where it lives |
|---|---|---|
| Scam calls caught (**recall**) | **86%** (51 of 59) | `data/eval_results_llm.json` |
| False alarms on genuine calls | **0 of 39** | same |
| **Accuracy** (if asked for that word) | **91.8%** (90 of 98) | computed from the same rows |
| Precision / F1 | **100%** / **92.7%** | same |
| Dial it hotter: catch everything | **100%** (59/59) at 5% false alarms | sweep, threshold 0.50 |
| Retrieval alone, matched comparison | 62% caught, **15% false alarms** | `eval_results_retrieval.json` |
| Scam *type* identified correctly | **83%** (49 of 59) | `eval_results_llm.json` |
| Knowledge base size | **96 passages**, zero retraining to add more | `rag/README.md` |

**Say "recall", not "accuracy".** 86% is the share of scam calls we flag. Accuracy over the
whole 98-call set is 91.8%. If a judge asks for accuracy, give 91.8% and immediately add the
0 false alarms — recall without its false-alarm rate is a meaningless number.

**The one sentence that carries the whole project** (matched: the same 94 calls, the same
0.65 threshold, only the judge layer switched off and on):

> "Retrieval alone catches 62% of scams and cries wolf on 15% of genuine calls. Add the
> retrieval-grounded LLM judge and the same 94 calls go to 85% caught with **zero** false
> alarms — and we can dial it to catch 100% if we accept 5% false alarms."

That is an *ablation*. Most hackathon teams cannot produce one. Lead with it.

**Two caveats to volunteer before they're found:**
- "Caught" means the call's **peak** score crossed the threshold at some point — the right
  metric for a product that only needs to warn once, but more generous than per-moment scoring.
- At the louder **SCAM** level (0.75) recall is 59% (35/59); the rest get a WARNING. Still 0
  false alarms.

---

## 1. Your five strongest cards

Steer every answer back to one of these.

1. **Honest evaluation.** Leave-one-out, with the hand-written cards held out of the search
   entirely because they were written after seeing the test calls (`scripts/evaluate.py:46`,
   `exclude_group=group, exclude_sources=("pattern",)`).
2. **We broke our own demo and fixed it.** A silent room scored a fake 84% "OTP scam". We
   found the cause, fixed it in four measured steps, and re-tested on silence, fan noise and
   sudden bangs. (§4.1 — this is your best story.)
3. **Deep platform work.** Android mutes the mic during calls; we found the accessibility
   exemption. Speakerphone audio is ~10× quieter than speech; we measured it (RMS 40–130 vs
   600–1300) and built an adaptive gain.
4. **RAG, not fine-tuning.** A new scam script is one new line of text. No retraining, no
   labelled corpus, no GPU. That is the difference between a demo and something that can
   keep up with scammers.
5. **Privacy by architecture.** Offline is the default, we run no backend, we collect nothing.

---

## 2. Tier 1 — the ML questions that sink most teams

### Q: "Did you test on your own training data?"
**This is the question that kills hackathon ML projects. You have a real answer.**

> "No — leave-one-out. When we score a call, that exact call is removed from the search index
> first. And the 38 hand-written pattern cards are excluded from every evaluation run, because
> we wrote them after reading the test calls — leaving them in would have flattered us. It's
> `exclude_group` and `exclude_sources` in `scripts/evaluate.py`, line 46. The 86% is what the
> system does on calls it has never seen."

Then offer the file. Judges rarely take you up on it; that you offered is the point.

### Q: "59 scam calls and 39 genuine ones is a tiny test set."
Do **not** get defensive. Concede precisely, then reframe.

> "Agreed — the 95% confidence interval on 51 of 59 is 75% to 93%, so the honest claim is
> 'high 70s to low 90s', not 'exactly 86%'. What the small set *can* establish is the
> ablation: the same 94 calls, two configurations, 15% false alarms down to zero. That
> comparison is internally valid regardless of sample size. Scaling the test set is exactly
> what we'd spend the next month on, and because it's RAG, more data makes us better without
> retraining anything."

### Q: "Why not just keyword rules? 'Arrest', 'OTP', 'safe account' — that's a regex."
> "We built that too — `ScamRules.kt` — and deliberately left it out of the main path.
> Keywords break two ways. A genuine bank fraud-alert call says 'account', 'blocked',
> 'verify' and trips every rule. And a scammer who says 'aapka naam ek case mein aaya hai'
> never uses the word 'arrest' at all. Our retrieval layer is the semantic version of
> keywords, and on its own it's 62% with 15% false alarms. The judge layer is what makes it
> usable."

### Q: "Why RAG? Why not fine-tune a classifier?"
> "Scam scripts change weekly. A fine-tuned model needs a fresh labelled corpus and a retrain
> every time; we need one line of text. Our knowledge base is 96 passages and adding the 97th
> is a file edit and a one-minute index rebuild. For a threat that mutates, retrieval is the
> right architecture — and it's also why the system can explain itself, because it can show
> the three real calls that looked like this one."

### Q: "What's your false-positive cost? You'll terrify a grandmother during a real bank call."
> "That's the failure we care about most, which is why we tuned for it rather than for
> headline accuracy. Our genuine-call set deliberately includes the hard cases — real bank
> fraud warnings, police calling about your own complaint, courier calls — and at our
> operating threshold we raise zero alarms on all 39. We also made the score asymmetric: it
> rises at 0.6 and falls at 0.15, so a call that looks bad stays flagged. We'd rather be
> slow to forgive than quick to panic."

### Q: "What happens when a scammer knows your app exists and adapts?"
> "Partially, yes — any detector can be evaded. But the scam has a structural floor: to take
> money, the caller must eventually create urgency, isolate the victim from family, and
> request a transfer or an OTP. You can reword those; you can't remove them. We retrieve on
> meaning, not wording, so paraphrase doesn't help as much as it would against keywords. And
> when a new script does emerge, our update cycle is adding a text line — not retraining."

---

## 3. Tier 2 — product and deployment

### Q: "Your detection runs on a laptop. That isn't a product."
Answer this before they ask, or it looks like you were hiding it.

> "Correct, and it's deliberate for today. The laptop is the *server tier* standing in for
> what would be a hosted API — it's an HTTP service, not a dev hack, so moving it to a
> container is a URL change. What we proved by splitting it this way is that the phone
> degrades gracefully: pull the laptop off the network mid-call and the app keeps recording,
> keeps transcribing, and retries per line. The phone is never dependent on it."

### Q: "Google Play will reject this. Call recording and accessibility are both restricted."
A judge who knows Android will ask this. Know it cold.

> "Right on both counts, and we've looked at it. Two paths. First, our accessibility service
> is already the narrowest possible: `canRetrieveWindowContent="false"` and an empty event
> handler — it exists only because Android exempts accessibility apps from the in-call mic
> mute, and it shows an on-screen badge, which is the opposite of hiding. That is defensible
> in a policy review in a way that a screen-reading service never is. Second, the real
> distribution answer for India is the OEM or telecom channel — this belongs preinstalled or
> in the dialler, not in a sideloaded app. Scam-call protection is a carrier-level feature."

### Q: "Truecaller already does this. Google's call screening already does this."
> "They block known bad *numbers* — a reputation lookup. Every number in a digital-arrest
> scam is fresh, often spoofed to look like a real police station, so reputation is blind to
> it. We don't look at who is calling. We look at **what is being said during the call**, and
> we score it continuously. A number nobody has ever reported, calling for the first time, is
> precisely the case we catch and they miss."

### Q: "What's the latency? Can it warn in time?"
> "Transcription is 6-second chunks, retrieval is milliseconds, and the LLM judge runs every
> 15 seconds or immediately when the retrieval score jumps by 0.2. So a warning lands within
> roughly 15–20 seconds of the scam turn. Digital-arrest calls run 40 minutes to several
> hours — the victim is kept on the line deliberately. We don't need to be instant; we need
> to interrupt before the transfer, and we have minutes of margin."

### Q: "Cost at scale? 100 million users calling DeepSeek?"
> "Per call, today, it's a few hundred Whisper seconds and a handful of judge calls — cents.
> At national scale you wouldn't run it this way: the retrieval layer is 118M parameters and
> already runs on-device-class hardware, so the LLM judge becomes the escalation path for the
> ~15% of calls retrieval finds ambiguous, not the default. Our ablation data is exactly what
> tells you where to put that cutoff."

---

## 4. Tier 3 — the trap questions

### 4.1 Q: "How do you know it isn't just making things up?"
**Your single best story. Tell it as a story.**

> "Because it did, and we caught it. Early on we left a live session running in an empty room
> and it reported an 84% OTP scam. Whisper had hallucinated — and the cause was ours: we were
> passing it a hint prompt containing 'OTP bata dijiye', and it dutifully repeated our own
> prompt back as transcribed speech.
>
> We fixed it in four measured steps. We removed the prompt entirely — it turned out Whisper
> repeats the prompt inside real speech too, not just silence. We added a room-noise check:
> the quietest 20% of the last 30 seconds sets the floor, and a frame only counts as speech
> at 2.5× that. We drop known phantom phrases. And we ignore pieces under three words,
> because a door slam becomes one invented word.
>
> Then we re-tested on silence, steady fan noise and sudden bangs. All three hold at score 0.
> The reason I can tell you this is in `rag/core/config.py` — the comments document the
> failure, not just the fix."

Judges remember teams that debug honestly far longer than teams that claim nothing broke.

### 4.2 Q: "DeepSeek is a Chinese company. You're pitching an Indian security app."
Sharp, political, and entirely fair. Do not get flustered.

> "Fair challenge, and it's a deployment decision rather than an architectural one. The judge
> is one HTTP call behind an interface — swapping it for a sovereign or on-premise model is a
> config change, and `DEEPSEEK_URL` is in `config.py` for exactly that reason. For a
> production Indian deployment we'd expect to run an Indic open-weights model on local
> infrastructure. What we'd keep is the architecture: retrieval-grounded, so the judge is
> always reasoning over *our* vetted examples rather than its own priors."

### 4.3 Q: "You're uploading Indian citizens' call audio to a US company. DPDP Act?"
> "Which is why offline is the default and online is opt-in with the user's own key. In
> offline mode no audio leaves the device at all. For the online path at production scale,
> the DPDP Act requires notice and purpose limitation, and cross-border transfer rules would
> push us to in-country inference — which is the same answer as the DeepSeek question:
> the pipeline is provider-agnostic by design. We also just shipped a hard off-switch for the
> on-device engine, so a user can pin exactly which engine is allowed to run."

### 4.4 Q: "Is recording this call even legal?"
> "The user is recording their own call, on their own phone, as a participant — that's the
> party-to-the-call position, not interception. It's opt-in per call with a deliberate tap,
> never always-on, the call is on speaker, and a red badge sits on screen the whole time. For
> production we'd add a spoken consent notice, since all-party-consent rules vary."

### 4.5 Q: "What's the weakest part of your system?" / "What would you fix first?"
**Never say "nothing". Pick a real one — it reads as confidence.**

> "The test set size. 98 calls is enough to prove the ablation and not enough to quote a
> precise accuracy, and I'd rather say that than defend 86% as though it were measured on
> ten thousand calls. First thing we'd fix is the data, and because we're RAG, more data is
> a pure win with no retraining. Second is the laptop server's security — it's plain HTTP
> with no auth today, fine on our private hotspot, wrong for production; it needs TLS and a
> token."

### 4.6 Q: "What did you *not* build?"
> "Speaker separation — we score the whole conversation, not the caller alone, so a victim
> repeating the scammer's words back adds signal. On-device LLM judging. Transcript redaction
> for card numbers. And automatic reporting to 1930 — we give the user the button, we don't
> file on their behalf, because a false report has a real cost."

---

## 5. The lines that actually win

Use these verbatim. Short, concrete, confident.

**Opening, 30 seconds — if you say nothing else, say this:**

> "Digital-arrest scams took thousands of crores from Indian families last year, and they
> work by keeping a victim on the phone for hours. Every existing defence checks *who* is
> calling — and these numbers are fresh and spoofed every time, so reputation is blind.
> BharatSecure listens to *what is being said*, in Hindi, English and Hinglish, and scores
> the call as it happens. 86% of scam calls caught, zero false alarms on 39 genuine bank,
> police and courier calls. It runs offline by default — the audio never leaves the phone."

**When asked what makes you different from every other team:**

> "Three things, and the third is the one I'd pick. One: we score meaning, not phone numbers.
> Two: adding a new scam is one line of text, no retraining. Three: we can show you our
> ablation and our leave-one-out methodology, and we can show you the bug where our own
> system hallucinated a scam in an empty room and what we did about it. We're not claiming
> it's perfect. We're claiming we measured it."

**Closing line:**

> "The scam works because a frightened person is alone on a call with nobody to tell them
> it's fake. We put something on that call that isn't frightened."

---

## 6. Demo script — and what to do when it breaks

**Before you start**
- Offline switch: decide **on or off** and set it beforehand. If the Groq key is saved and the
  hotspot is up, leave offline **off** — the judge sees only clean Whisper text.
- Run **Test connection** on the Laptop AI screen. Green before you present.
- Have the saved recording from a successful run open in the Recordings tab as a fallback.
- Airplane-mode contingency: know which parts still work (offline transcription, on-device
  rules) and say so rather than apologising.

**The 3-minute run**
1. Show the home screen — three tiles, state visible at a glance. *"Nothing runs until the user taps."*
2. Incoming call → the notification offers protection → one tap. *"Opt-in, every single call."*
3. Speaker on. Play the scam audio. Point at the score climbing and the red badge on screen.
4. The alert fires — read the **reason** aloud. *"It doesn't just say scam. It says why, and what to do."*
5. Open the saved transcript. *"Every call leaves evidence the user owns, on their own phone."*

**If the demo fails mid-run:** do not fight it live. Say this, and move:

> "That's the live-audio path and it's the brittle part of any voice demo. Let me show you the
> same call from a run we recorded, and then I'll tell you exactly why live audio is hard —
> it's the most interesting engineering in the project."

Then tell the hallucination story (§4.1). A recovered demo plus a real debugging story often
scores higher than a clean demo with nothing behind it.

---

## 7. What NOT to say

| Don't say | Say instead |
|---|---|
| "It's 100% accurate" | "86% caught, zero false alarms, on 98 calls — and here's the confidence interval" |
| "It works for every scam" | "It's strongest on digital-arrest and OTP scripts, which is where the money is" |
| "We use AI/ML" (vague) | "multilingual-e5-small for retrieval, a DeepSeek judge over the retrieved examples" |
| "Nothing's wrong with it" | "The test set is small and the laptop link needs TLS" |
| "We'll add blockchain/metaverse" | "We'd add more labelled calls, because RAG turns data straight into accuracy" |
| Blaming a teammate or the WiFi | "That's the brittle part of a live voice demo — here's the recorded run" |

---

## 8. If you only remember four things

1. **Lead with the ablation**, not the architecture. 62%/15% → 85%/0% on the same 94 calls.
2. **Say "leave-one-out" out loud.** It signals you know what overfitting is.
3. **Volunteer a weakness before they find one.** Test set size. Laptop TLS.
4. **Tell the empty-room hallucination story.** It is the most memorable thing you have.
