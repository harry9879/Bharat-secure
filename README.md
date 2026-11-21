# BharatSecure

Scam protection for Indian phone users, covering the two channels scammers actually
use: **voice calls** and **SMS**. This repository holds both halves of the project,
which until now lived in two separate repositories.

| | Calls | SMS |
|---|---|---|
| App | **BharatSecure** | **ScamShield SMS** |
| Package | `com.bharatsecure.app` | `com.scamshield.sms` |
| Source | [`app/`](app/) | [`scamshield/android/`](scamshield/android/) |
| Server | [`rag/`](rag/) — retrieval + LLM judge | [`scamshield/backend/`](scamshield/backend/) — FastAPI scoring |
| minSdk | 26 | 29 (needs `RoleManager.ROLE_SMS`) |

The two install as **two APKs** and hand off to each other: BharatSecure's menu opens
ScamShield through `SmsShield.kt`, which is why `com.scamshield.sms` is declared under
`<queries>` in [`app/src/main/AndroidManifest.xml`](app/src/main/AndroidManifest.xml).
Keeping them separate is deliberate — Android only grants the default-SMS role to an app
whose whole manifest is built for it, and the call side needs a microphone foreground
service and an accessibility service that an SMS app has no business requesting.

## Layout

```
app/                  BharatSecure call-protection app (Kotlin + Compose, offline Vosk speech)
rag/                  Retrieval-grounded scam judge for calls (Python, runs on a laptop)
scamshield/android/   ScamShield default-SMS app (Kotlin + Compose, Room + WorkManager)
scamshield/backend/   SMS scoring API, deep URL analysis, auto-reports (FastAPI, Python 3.12)
scamshield/sandbox/   Isolated Playwright browser that opens suspect links
scamshield/shared/    rules.yaml + brands.yaml — the single source of scam keywords and brands
scamshield/deploy/    docker-compose, Nginx snippet (prepared, not deployed)
scamshield/tools/     rule export, Kotlin-vs-Python parity check, demo report
JUDGE_PREP.md         Evaluation numbers and the hardest questions, with answers
SECURITY_QA.md        Security and privacy posture
```

## Build the call app

Needs JDK 21 — Android Studio's bundled JBR works; a system JDK 8 on `PATH` will not.

```bash
./gradlew :app:assembleDebug      # root project = BharatSecure only
./gradlew :app:testDebugUnitTest
```

The call judge runs on a laptop the phone reaches over a hotspot; see
[`rag/README.md`](rag/README.md). Plain `http://` on the LAN is why the manifest sets
`usesCleartextTraffic`.

## Build the SMS app

`scamshield/android/` is its **own** Gradle project — open that folder in Android Studio,
not the repository root.

```bash
cd scamshield/android && ./gradlew assembleDebug
```

It needs `scamshield/android/local.properties` (never committed) with `scamshield.apiBaseUrl`
and `scamshield.apiKey`. Full instructions, backend setup and the default-SMS walkthrough are
in [`scamshield/README.md`](scamshield/README.md).

## Status

Runs locally only — nothing is deployed. Before switching the SMS backend to
`REPORT_MODE=live`, every address in `scamshield/backend/data/authorities.yaml` must be
checked against the official nodal-officer list on cybercrime.gov.in.
