"""Build a human-review queue with known-answer checks mixed in.

Usage: python review/build_queue.py [--live FILE.jsonl] [--known FILE.jsonl]
                                    [--audit-rate 0.15] [--per-kind 2] [--seed 7] [--out DIR]

Live answers go through the checker: REVIEW answers enter the queue with their
flags, and a random audit sample of SEND answers enters with none. Known-answer
items come from a labeled case file and look exactly like live items:

  bad_flagged    a bad answer shown with the checker's flags      -> should be rejected
  bad_unflagged  a bad answer shown as an audit sample, no flags  -> should be rejected
  good           a good answer shown as an audit sample           -> should be approved

bad_unflagged is the automation-bias check: a reviewer who only acts on flags
approves it. Writes review.html (the reviewer's page, no labels) and key.json
(the answer key, which the page never loads; keep it away from reviewers).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fin_assist import check  # noqa: E402

KINDS = ("bad_flagged", "bad_unflagged", "good")


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _item(case: dict, flags: list[dict], reason: str) -> dict:
    return {"question": case["question"], "answer": case["answer"], "reason": reason,
            "flags": [{k: f[k] for k in ("type", "span", "reason", "source")} for f in flags]}


def build(live: list[dict], known: list[dict], audit_rate: float, per_kind: int, seed: int):
    rng = random.Random(seed)
    items: list[tuple[dict, dict]] = []  # (queue item, key entry)

    for c in live:
        r = check(c["question"], c["answer"])
        if r["decision"] == "REVIEW":
            items.append((_item(c, r["flags"], "flagged"), {"known": False, "source_case": c.get("id")}))
        elif rng.random() < audit_rate:
            items.append((_item(c, [], "audit"), {"known": False, "source_case": c.get("id")}))

    pools = {k: [] for k in KINDS}
    for c in known:
        if not c["answer"].strip():
            continue  # an empty draft is caught by code; it tells us nothing about a reviewer
        r = check(c["question"], c["answer"])
        if c["expected"] == "REVIEW":
            if r["decision"] == "REVIEW":
                pools["bad_flagged"].append((c, r["flags"], "flagged"))
            pools["bad_unflagged"].append((c, [], "audit"))
        elif r["decision"] == "SEND":
            pools["good"].append((c, [], "audit"))
    used: set[str] = set()
    for kind in KINDS:
        picks = [p for p in pools[kind] if p[0]["id"] not in used]
        for c, flags, reason in rng.sample(picks, min(per_kind, len(picks))):
            used.add(c["id"])
            items.append((_item(c, flags, reason), {
                "known": True, "kind": kind, "source_case": c["id"],
                "expected_action": "approve" if kind == "good" else "reject"}))

    rng.shuffle(items)
    queue, key = [], {}
    for n, (item, entry) in enumerate(items, 1):
        item_id = f"item-{n:02d}"
        queue.append({"id": item_id, **item})
        key[item_id] = entry
    return queue, key


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", type=Path, nargs="*", default=[ROOT / "evals/heldout.jsonl", ROOT / "evals/heldout2.jsonl"])
    ap.add_argument("--known", type=Path, default=ROOT / "evals/cases.jsonl")
    ap.add_argument("--audit-rate", type=float, default=0.15)
    ap.add_argument("--per-kind", type=int, default=2)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path, default=ROOT / "review/out")
    a = ap.parse_args()

    live = [c for p in a.live for c in _load(p)]
    queue, key = build(live, _load(a.known), a.audit_rate, a.per_kind, a.seed)
    a.out.mkdir(parents=True, exist_ok=True)
    page = (ROOT / "review/template.html").read_text()
    payload = json.dumps(queue).replace("</", "<\\/")
    qid = hashlib.sha256(payload.encode()).hexdigest()[:12]
    (a.out / "review.html").write_text(page.replace("__QUEUE__", payload).replace("__QID__", qid))
    (a.out / "key.json").write_text(json.dumps(key, indent=1))
    known = sum(e["known"] for e in key.values())
    print(f"{len(queue)} items ({known} known-answer checks) -> {a.out}/review.html; key -> {a.out}/key.json")


if __name__ == "__main__":
    main()
