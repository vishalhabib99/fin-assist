"""A minimal education-only Q&A agent with fin-doctor as its last step.

    python examples/plain_agent.py                      # canned drafts, no model, no setup
    python examples/plain_agent.py --ollama llama3.2    # a local model via Ollama (free)
    OPENAI_BASE_URL=... OPENAI_API_KEY=... python examples/plain_agent.py --openai gpt-4o-mini

The model never decides what the customer sees: gate() does.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from fin_doctor.gate import gate

SYSTEM = ("You answer general questions about US retirement accounts, HSAs, Social Security and federal tax. "
          "Give education only: explain rules and figures, never tell the person what they should do. "
          "Keep answers to three sentences.")


def ask_ollama(model: str, question: str) -> str:
    body = {"model": model, "stream": False,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]}
    req = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["message"]["content"]


def ask_openai(model: str, question: str) -> str:
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]}
    req = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    return json.load(urllib.request.urlopen(req, timeout=120))["choices"][0]["message"]["content"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama", metavar="MODEL")
    ap.add_argument("--openai", metavar="MODEL", help="any OpenAI-compatible endpoint (OPENAI_BASE_URL)")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("question", nargs="?")
    args = ap.parse_args()

    if args.question and (args.ollama or args.openai):
        pairs = [(args.question, None)]
    else:
        rows = [json.loads(l) for l in (Path(__file__).parent / "canned_drafts.jsonl").read_text().splitlines() if l.strip()]
        pairs = [(r["question"], r["draft"]) for r in rows]

    for question, draft in pairs:
        if draft is None:
            draft = ask_ollama(args.ollama, question) if args.ollama else ask_openai(args.openai, question)
        verdict = gate(question, draft, args.year)
        print(f"Q: {question}\n   draft:   {draft}\n   [{verdict.outcome.upper()}]")
        for f in verdict.fixes:
            print(f"   fixed:   {f['span']} -> {f['replacement']} ({f['figure_year']} figure; {f['source']})")
        for r in verdict.reasons:
            print(f"   held:    {r.get('span')}: {r.get('reason') or r.get('status')}")
        print(f"   sent:    {verdict.text}\n")


if __name__ == "__main__":
    main()
