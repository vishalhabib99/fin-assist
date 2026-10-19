"""Score the checker against a case file. Usage: python evals/run.py [cases.jsonl] [judge.json]

Pass --strict to exit 1 on any failure.
A case passes when the decision matches and every expected flag type is present.
Optional judge.json ({case_id: [flag types]}) merges in the model-judgment layer.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fin_assist import check  # noqa: E402

args = [a for a in sys.argv[1:] if a != "--strict"]
path = Path(args[0] if args else Path(__file__).parent / "cases.jsonl")
judge = json.loads(Path(args[1]).read_text()) if len(args) > 1 else {}
cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
by_slice = defaultdict(lambda: [0, 0])
fails = []
for c in cases:
    r = check(c["question"], c["answer"])
    got = {f["type"] for f in r["flags"]} | set(judge.get(c["id"], []))
    decision = "REVIEW" if got else "SEND"
    ok = decision == c["expected"] and set(c["expected_flags"]) <= got
    by_slice[c["slice"]][0] += ok
    by_slice[c["slice"]][1] += 1
    if not ok:
        fails.append((c["id"], c["expected"], decision, sorted(got), c.get("note", "")))
    unsourced = [f for f in r["flags"] if f["type"] in ("wrong_fact",) and not f["source"]]
    if unsourced:
        fails.append((c["id"], "sourced flags", "unsourced wrong_fact", [], ""))
print(f"{path.name}: {sum(v[0] for v in by_slice.values())}/{len(cases)} pass")
for k, (p, n) in by_slice.items():
    print(f"  {k:15} {p}/{n}")
for f in fails:
    print("  FAIL", *f)
if "--strict" in sys.argv and fails:
    sys.exit(1)
