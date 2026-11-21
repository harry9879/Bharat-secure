# BharatSecure — Security & Privacy Q&A

Prepared for judging. Every answer below is grounded in the code in this repo;
file references are given so a claim can be checked on the spot.

---

## 1. Data flow — the one-slide answer

**Q: Where does call audio go?**

Three modes, and the user picks:

| Mode | Audio leaves the phone? | Who sees it |
|---|---|---|
| **Offline** (default) | No | Nobody. Vosk runs on the device. |
| **Online** | Yes — 6-second WAV chunks | Groq, over HTTPS (`api.groq.com`) |
| **Laptop AI (RAG)** | No audio — **text only** | Our own laptop on the same hotspot |

The `.wav` recording is always written locally and is never uploaded as a whole
file. The laptop RAG link receives *transcript lines*, not audio
(`ProtectionService.kt` → `rag.send(lines[ragSent++])`).

**Q: Is the audio encrypted in transit?**

To Groq, yes — `ENDPOINT = "https://api.groq.com/openai/v1/audio/translations"`
(`CloudTranscriber.kt:163`), standard TLS.
To our laptop server, **no** — see §5.1, a limitation we own.

---

## 2. Permissions — why each one exists

From `app/src/main/AndroidManifest.xml`:

| Permission | Why it is needed | What we *don't* do with it |
|---|---|---|
| `RECORD_AUDIO` | The entire product: hear the scam call | Only while Protection Mode is on, never in the background |
| `READ_PHONE_STATE` | Know a call started/ended, to offer protection and stop cleanly | No dialling, no call control |
| `READ_CALL_LOG` | Android only puts the caller's number in the `PHONE_STATE` broadcast if this is held | We never read call history; the number labels the notification |
| `POST_NOTIFICATIONS` | The scam alert and the ongoing-recording notification | No marketing, no remote push — there is no push server |
| `FOREGROUND_SERVICE` + `_MICROPHONE` | Android 14 requires a typed foreground service to use the mic | — |
| `INTERNET` | Vosk model download, Groq, the laptop server | — |

**Not requested:** contacts, SMS, storage, location, camera.

`android:allowBackup="false"` on the `<application>` tag — recordings and the API
key are excluded from Android cloud backup.

---

## 3. "You asked for an Accessibility Service. That's the #1 Android malware vector."

This is the sharpest question we expect, and the answer is clean.

Android **mutes the microphone for ordinary apps during a phone call**. An app
with an enabled accessibility service that has a window on screen is exempt.
That exemption — not screen reading — is the only reason the service exists.

The service is deliberately declawed in `res/xml/accessibility_config.xml`:

```xml
android:canRetrieveWindowContent="false"
android:accessibilityEventTypes="typeAnnouncement"
```

`canRetrieveWindowContent="false"` means **the OS will not hand us screen content
at all**, even if we asked for it. And in `CallAudioAccessibilityService.kt`:

```kotlin
override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit
```

The event handler is an empty function. The service's whole job is to show a small
red "🛡 Protection ON" badge — which doubles as the user's visible, unmissable
indicator that recording is happening.

---

## 4. The API key

**Q: Where is the Groq key stored?**

In app-private `SharedPreferences` (`SpeechModels.kt`, `MODE_PRIVATE`), readable
only by this app's UID under the Android sandbox. It is entered by the user, is
*their* key, and is sent only to Groq in an `Authorization: Bearer` header. No key
is compiled into the APK — grep the repo, there is no hard-coded secret.

**Q: Is it encrypted at rest?**

No, and we'll say so plainly: it is plaintext inside the app sandbox. On a
non-rooted phone the OS protects it, but a rooted device could read it.
**Fix for v2:** `EncryptedSharedPreferences` backed by the Android Keystore —
roughly a 10-line change; we prioritised the detection pipeline for the hackathon.

---

## 5. Known weaknesses (better named by us than found by you)

### 5.1 The laptop RAG link is plain HTTP with no authentication
`android:usesCleartextTraffic="true"` in the manifest; `RagSettings.normalize()`
prefixes `http://`. The server (`rag/server.py`) binds `0.0.0.0:8000` with no auth,
so anyone on the same hotspot could reach it or read transcript lines off the air.
*Mitigation today:* it runs on a private phone hotspot we control, and it is off by
default (empty URL = feature disabled).
*Fix:* self-signed TLS plus a shared bearer token pinned in the app. A demo-rig
shortcut, not an architectural choice.

### 5.2 Downloaded speech models are not signature-checked
`SpeechModels.download()` fetches a `.zip` over HTTPS from `alphacephei.com` and
trusts it. TLS protects the transport, but we verify no publisher signature or
SHA-256. *Fix:* pin a checksum per model — the `SpeechModel` enum is the natural
place for it.

**Already handled: Zip-Slip is defended.** `unzip()` canonicalises every entry and
refuses anything escaping the models folder:

```kotlin
if (!out.canonicalPath.startsWith(rootPath)) error("Bad zip entry: ${entry.name}")
```

### 5.3 Recordings sit in external app storage
`Android/data/com.bharatsecure.app/files/recordings` (`Recordings.kt`), so they can
be pulled over USB for debugging. They die on uninstall and never reach the media
scanner or gallery, but they are less protected than internal storage.
*Fix:* move to `filesDir`, encrypt, and add an explicit export action.

### 5.4 No transcript redaction
If a victim reads out a card number it lands in the `.txt`, and in Online mode it
transits Groq. *Fix:* mask long digit runs before storing or uploading.

---

## 6. Privacy by design — what we did right

- **Offline is the default.** `SpeechModels.engine()` returns `SpeechEngine.OFFLINE`
  when nothing is stored. A user who never opens settings never sends audio anywhere.
- **Nothing starts by itself.** An incoming call only produces a notification
  *offering* protection; the user must tap it (`ProtectionLauncherActivity`). There
  is no silent always-on recorder.
- **Visible while recording** — a foreground-service notification *and* the on-screen
  red badge. The user cannot be unaware.
- **No account, no telemetry, no analytics SDK, no ad SDK.** We operate no backend
  that user data is sent to; the only server is one the user runs themselves.
- **Kill switches for both engines.** Laptop AI is off unless a URL is entered, and
  the offline engine has an explicit **Offline transcript** switch
  (`SpeechModels.offlineEnabled`). With it off, Vosk is never loaded and no on-device
  transcript is produced at all.
- **Alerts only escalate.** The scam level never drops during a call (`ragRank` in
  `ProtectionService.kt`) — a scammer turning polite later doesn't make the call safe.
- **Whisper hallucination guard.** Near-silent chunks are dropped and canned phrases
  filtered (`isHallucination()`), so the app doesn't invent speech.

---

## 7. Legal / consent

**Q: Is recording the call legal?**

The design keeps us on the safe side:

- The **user records their own call**, on their own device, as a participant — the
  party-to-the-call position, not third-party interception.
- It is **per call and opt-in**: one deliberate tap each time, never blanket recording.
- The call is on **speakerphone**, with a visible badge on screen throughout.
- Audio stays on the device by default and is deletable in-app (`Recordings.delete`).

For a production release we would add a spoken consent notice and a jurisdiction
check, since all-party-consent rules vary.

---

## 8. Threat model in one line each

| Threat | Our position |
|---|---|
| Malicious app reads our recordings | Blocked by the app sandbox; uninstall wipes them |
| Attacker on the same Wi-Fi | Can reach the laptop RAG server — real gap, §5.1 |
| Stolen or rooted phone | Recordings and API key readable — fix is Keystore encryption |
| Our servers leaking user data | **We have none.** Nothing is centrally collected |
| Scammer evading detection | Layered: on-device rules + retrieval + LLM; level only escalates |
| Supply chain (Vosk model swap) | TLS download, Zip-Slip safe, but unsigned — §5.2 |

---

## 9. Rapid-fire answers

**Does this work without internet?**
Yes. Offline mode and the on-device rules need no network. The laptop RAG adds
accuracy when available, and the app keeps working when it disappears (`RagLink`
retries per line and never blocks the call).

**What if Groq goes down mid-call?**
The error surfaces in the UI, the `.wav` keeps recording, and `lastError` is written
into the saved transcript. With the offline switch on, Vosk covers the gap.

**How much data does Online mode use?**
About 6 s of 16 kHz mono PCM per upload ≈ 190 KB per chunk, and silent chunks are
skipped entirely.

**Can BharatSecure read my WhatsApp messages?**
No. `WhatsAppCallListener` matches *call* notifications only and reads one field —
the caller's display name — to label the notification. It never touches message
notifications.

**What's the worst a bug in this app could do?**
Record audio it shouldn't. That is why recording is user-initiated, visibly
indicated, scoped to a foreground service that stops with the call, and why the
audio's default destination is nowhere but the phone.
