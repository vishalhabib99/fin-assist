"""Score the number check on a labeled JSONL set (id, answer, bad_figures, good_figures)."""
import json
import sys

from retirement_answer_check.numcheck import check_numbers


def main(path: str, year: int = 2026) -> None:
    rows = [json.loads(l) for l in open(path) if l.strip()]
    bad_hit = bad_total = good_flag = good_total = 0
    ans = {"bad_caught": 0, "bad": 0, "clean_pass": 0, "clean": 0}
    misses = []
    for r in rows:
        res = check_numbers(r["answer"], year)
        flagged = [c["span"] for c in res["claims"] if c["status"] != "match"]
        hit = lambda fig: any(fig in s or s in fig for s in flagged)
        for fig in r["bad_figures"]:
            bad_total += 1
            if hit(fig):
                bad_hit += 1
            else:
                misses.append((r["id"], "missed bad", fig))
        for fig in r["good_figures"]:
            good_total += 1
            if hit(fig):
                good_flag += 1
                misses.append((r["id"], "false flag", fig))
        key = "bad" if r["bad_figures"] else "clean"
        ans[key] += 1
        if (res["decision"] == "REVIEW") == (key == "bad"):
            ans["bad_caught" if key == "bad" else "clean_pass"] += 1
        elif key == "clean":
            misses.append((r["id"], "clean answer sent to REVIEW", flagged))
    print(f"bad figures caught: {bad_hit}/{bad_total}")
    print(f"good figures falsely flagged: {good_flag}/{good_total}")
    print(f"answers with a bad figure -> REVIEW: {ans['bad_caught']}/{ans['bad']}")
    print(f"clean answers -> PASS: {ans['clean_pass']}/{ans['clean']}")
    for m in misses:
        print("  ", *m)


if __name__ == "__main__":
    main(sys.argv[1])
