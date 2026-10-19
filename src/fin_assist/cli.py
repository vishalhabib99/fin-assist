"""fin-assist command line: check the figures in an answer, or list the registry."""
from __future__ import annotations

import argparse
import json
import sys

from .numcheck import FACTS, check_numbers

_MARK = {"match": "ok", "stale": "STALE", "wrong_year": "WRONG YEAR", "wrong": "WRONG",
         "unknown_year": "UNKNOWN YEAR", "unverified": "UNVERIFIED"}


def _why(c: dict) -> str:
    if c["status"] == "stale":
        return f"that's the {c['figure_year']} figure; {c['year']} is {c['expected']:,g}"
    if c["status"] == "wrong_year":
        return f"that's the {c['figure_year']} figure, quoted for {c['year']}; {c['year']} is {c['expected']:,g}"
    if c["status"] == "wrong":
        exp = c.get("expected") or {}
        return "expected " + " or ".join(f"{v:,g} ({FACTS[k]['label']})" for k, v in exp.items())
    if c["status"] == "unknown_year":
        return f"no verified {c['year']} figure yet; not guessing"
    if c["status"] == "unverified":
        return "a real rule the registry doesn't cover yet; check by hand"
    return c["label"] or ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fin-assist", description="Check the official financial figures in an AI answer.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check an answer (text argument, or stdin)")
    c.add_argument("answer", nargs="?", help="the answer text; reads stdin when omitted")
    c.add_argument("--year", type=int, help="tax year when a sentence doesn't say (default: this year)")
    c.add_argument("--json", action="store_true", help="print the raw result")
    f = sub.add_parser("facts", help="list registry figures")
    f.add_argument("query", nargs="?", default="", help="filter by id or label")
    args = ap.parse_args(argv)

    if args.cmd == "facts":
        for fid, fact in FACTS.items():
            if args.query.lower() in (fid + " " + fact["label"]).lower():
                vals = ", ".join(f"{y}: {v:,g}" for y, v in fact["values"].items())
                print(f"{fid:48} {vals}")
        return 0

    text = args.answer if args.answer is not None else sys.stdin.read()
    result = check_numbers(text, args.year)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["decision"])
        for claim in result["claims"]:
            print(f"  {_MARK[claim['status']]:12} {claim['span']:14} ({claim['year']}) {_why(claim)}")
            if claim["status"] != "match" and claim["source"]:
                print(f"  {'':12} source: {claim['source']}")
    return 0 if result["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
