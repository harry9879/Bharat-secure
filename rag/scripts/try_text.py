"""Type a call line by line and watch the score move (no audio, no Groq).

Run from rag/:  .venv/Scripts/python -m scripts.try_text [--no-llm]
Each line you type is one more piece of the call. Empty line = new call.
"""

import argparse

from core.index import Index, embed
from core.session import CallSession


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()
    index = Index.load()
    embed(["warm up"], "query")
    session = CallSession(index, use_llm=not args.no_llm)
    print("Type what the caller says, one line at a time. Empty line starts a new call. Ctrl+C to quit.")
    while True:
        line = input("> ").strip()
        if not line:
            session = CallSession(index, use_llm=not args.no_llm)
            print("-- new call --")
            continue
        u = session.add_text(line)
        d = u["details"]
        print(f"   score {u['score']*100:5.1f}%  {u['level']}  {u['type_name'] or ''}"
              f"   (retrieval {d['retrieval']*100:.0f}%" +
              (f", llm {d['llm']['score']*100:.0f}%)" if d.get("llm") else ")"))
        if d.get("llm") and u["level"] != "SAFE":
            print(f"   why: {d['llm']['reason']}")


if __name__ == "__main__":
    main()
