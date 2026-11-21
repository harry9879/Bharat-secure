"""Real-time demo on the laptop: listens to the microphone (put the phone call
on speaker next to the laptop), transcribes every few seconds and prints the
continuous scam score.

Run from rag/:  .venv/Scripts/python -m scripts.live_mic [--seconds 5] [--no-llm]
Stop with Ctrl+C; the transcript and score history are saved in data/live/.
"""

import argparse
import json
import queue
import time

import numpy as np
import sounddevice as sd

from core import config
from core.index import Index, embed
from core.session import CallSession

COLOURS = {"SAFE": "\033[92m", "WARNING": "\033[93m", "SCAM": "\033[91m"}
RESET = "\033[0m"


def bar(score: float, width: int = 30) -> str:
    filled = int(round(score * width))
    return "█" * filled + "·" * (width - filled)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=5.0, help="audio per chunk")
    ap.add_argument("--no-llm", action="store_true", help="retrieval score only (no DeepSeek)")
    args = ap.parse_args()

    print("loading index and embedding model…")
    index = Index.load()
    embed(["warm up"], "query")
    session = CallSession(index, use_llm=not args.no_llm)
    print(f"LLM judge: {'on' if session.use_llm else 'off'}  |  speak or play the call on speaker. Ctrl+C to stop.\n")

    rate, chunk = 16000, int(16000 * args.seconds)
    audio_q: queue.Queue = queue.Queue()
    sd.InputStream(samplerate=rate, channels=1, dtype="int16",
                   callback=lambda data, frames, t, status: audio_q.put(data.copy())).start()
    buf = np.zeros(0, dtype=np.int16)
    try:
        while True:
            buf = np.concatenate([buf, audio_q.get()[:, 0]])
            if len(buf) < chunk:
                continue
            piece, buf = buf[:chunk], buf[chunk:]
            start = time.time()
            u = session.add_audio(piece, rate)
            took = time.time() - start
            colour = COLOURS[u["level"]]
            label = u["level"] + (f" · {u['type_name']}" if u["type_name"] else "")
            print(f"{colour}[{bar(u['score'])}] {u['score']*100:5.1f}%  {label}{RESET}   ({took:.1f}s)")
            if u["new_text"]:
                print(f"   “{u['new_text']}”")
            llm = (u.get("details") or {}).get("llm")
            if llm and u["level"] != "SAFE":
                print(f"   why: {llm['reason']}  |  {llm['advice']}")
            if u["note"] and u["note"] != "silence":
                print(f"   note: {u['note']}")
    except KeyboardInterrupt:
        out = config.DATA_DIR / "live"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"call_{time.strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(dict(transcript=session.transcript, peak=session.peak,
                                        history=session.history, llm=session.last_llm),
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nstopped. peak score {session.peak*100:.1f}%  ->  saved {path}")


if __name__ == "__main__":
    main()
