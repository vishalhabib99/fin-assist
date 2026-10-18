"""The streaming case: most chat UIs show tokens as they arrive. Two ways to gate them.

    python examples/streaming_agent.py hold      # buffer, check, then show (nothing unchecked is seen)
    python examples/streaming_agent.py correct   # show live, check at the end, replace if needed

`hold` is the safe default for money answers. `correct` keeps the typing feel, but the customer
briefly sees the unchecked text, so use it only where a UI can replace the message in place
(the pattern xiaoman's frontend uses with its `final` event).
"""
from __future__ import annotations

import sys
import time
from typing import Iterator

from fin_doctor.gate import gate

QUESTION = "How much can I put in my 401(k) this year?"
DRAFT = "For 2026 you can defer up to $23,500 into your 401(k), plus an $8,000 catch-up if you're 50 or older."


def model_stream(text: str) -> Iterator[str]:
    """Stand-in for a model's token stream (Ollama, OpenAI and LangChain all yield chunks like this)."""
    for word in text.split(" "):
        time.sleep(0.03 if __name__ == "__main__" else 0)
        yield word + " "


def hold(question: str, stream: Iterator[str], year: int = 2026) -> str:
    draft = "".join(stream).strip()         # 1. collect every chunk; show a typing indicator meanwhile
    verdict = gate(question, draft, year)   # 2. check the whole answer
    return verdict.text                     # 3. show only what passed (or was fixed, or the holding message)


def correct(question: str, stream: Iterator[str], show, replace, year: int = 2026) -> str:
    chunks = []
    for chunk in stream:                    # 1. show tokens live
        chunks.append(chunk)
        show(chunk)
    verdict = gate(question, "".join(chunks).strip(), year)
    if verdict.outcome != "send":           # 2. replace the shown message if anything changed
        replace(verdict.text)
    return verdict.text


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "hold"
    if mode == "hold":
        print("assistant is typing...", flush=True)
        print(hold(QUESTION, model_stream(DRAFT)))
    else:
        correct(QUESTION, model_stream(DRAFT),
                show=lambda c: print(c, end="", flush=True),
                replace=lambda text: print(f"\n[corrected] {text}"))


if __name__ == "__main__":
    main()
