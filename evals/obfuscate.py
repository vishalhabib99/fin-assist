"""F-12 obfuscation check (EVAL_PLAN.md §7).

Rewrites the injection text of every I1 case the rules already flag, four fixed ways, and
reports how many are still flagged `injection_attempt` by the rules, plus the O-2/O-4 counts.

Usage: python evals/obfuscate.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fin_doctor import check  # noqa: E402

# Latin letters with a Cyrillic twin (T4).
CYRILLIC = dict(zip("aceopxysijABCEHIJKMOPSTXY", "асеорхуѕіјАВСЕНІЈКМОРЅТХҮ"))


def t1_zero_width(text):
    return re.sub(r"[A-Za-z]{2}", lambda m: m.group(0) + "​", text)


def t2_soft_hyphen(text):
    return re.sub(r"[A-Za-z]{4,}", lambda m: m.group(0)[: len(m.group(0)) // 2] + "­" + m.group(0)[len(m.group(0)) // 2:], text)


def t3_fullwidth(text):
    return "".join("　" if c == " " else chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in text)


def t4_lookalike(text):
    return "".join(CYRILLIC.get(c, c) for c in text)


TRANSFORMS = {"T1 zero-width": t1_zero_width, "T2 soft hyphen": t2_soft_hyphen,
              "T3 fullwidth": t3_fullwidth, "T4 look-alike": t4_lookalike}


def disguise(case, fn):
    """Rewrite each injection span in the answer; a case with two spans joins them with " || "."""
    answer = case["answer"]
    for span in case["injection_span"].split(" || "):
        assert span in answer, (case["id"], span)
        answer = answer.replace(span, fn(span))
    return answer


def load(name):
    return [json.loads(line) for line in (ROOT / "evals" / name).read_text().splitlines() if line.strip()]


def injection_flagged(question, answer):
    return any(f["type"] == "injection_attempt" for f in check(question, answer)["flags"])


def main():
    i1 = [c for c in load("injection1.jsonl") if c.get("injection_span")]
    caught = [c for c in i1 if injection_flagged(c["question"], c["answer"])]
    print(f"O-1 undisguised: {len(caught)} of {len(i1)} I1 injections flagged")
    for name, fn in TRANSFORMS.items():
        hits = sum(injection_flagged(c["question"], disguise(c, fn)) for c in caught)
        print(f"O-1 {name}: {hits} of {len(caught)}")

    clean = []
    for name in ("cases.jsonl", "heldout.jsonl", "heldout2.jsonl"):
        clean += [(c["question"], c["answer"]) for c in load(name)]
    for name in ("injection1.jsonl", "injection2.jsonl"):
        for c in load(name):
            if c["slice"] == "lookalike":
                clean.append((c["question"], c["answer"]))
            if c.get("defect_only_answer"):
                clean.append((c["question"], c["defect_only_answer"]))
    false_flags = sum(injection_flagged(q, a) for q, a in clean)
    print(f"O-2 clean texts flagged injection_attempt: {false_flags} of {len(clean)}")

    i2 = [c for c in load("injection2.jsonl") if c["slice"] != "lookalike"]
    print(f"O-4 I2 injections flagged by the rules: {sum(injection_flagged(c['question'], c['answer']) for c in i2)} of {len(i2)}")


if __name__ == "__main__":
    main()
