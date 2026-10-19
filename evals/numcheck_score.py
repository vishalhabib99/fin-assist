"""Score the number check on a labeled JSONL set (id, answer, bad_figures, good_figures)."""
"""Usage: numcheck_score.py <set.jsonl> [year] [--llm ollama:qwen3:8b] [--mode add|label]"""
import json
import statistics
import sys
import time

from fin_assist.numcheck import check_numbers


def main(path: str, year: int = 2026, llm=None, mode: str = "add") -> None:
    rows = [json.loads(l) for l in open(path) if l.strip()]
    bad_hit = bad_total = good_flag = good_total = 0
    ans = {"bad_caught": 0, "bad": 0, "clean_pass": 0, "clean": 0}
    misses, secs, failed = [], [], 0
    for r in rows:
        t = time.perf_counter()
        res = check_numbers(r["answer"], year, llm=llm, llm_mode=mode)
        secs.append(time.perf_counter() - t)
        if res.get("llm", "used") != "used":
            failed += 1
            misses.append((r["id"], "model failed", res["llm"]))
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
    if llm:
        print(f"seconds per answer: median {statistics.median(secs):.2f}, max {max(secs):.2f}; model failures: {failed}")
    for m in misses:
        print("  ", *m)


if __name__ == "__main__":
    args = sys.argv[1:]
    llm = None
    if "--llm" in args:
        spec = args.pop(args.index("--llm") + 1)
        args.remove("--llm")
        from fin_assist.llm_match import ollama
        llm = ollama(spec.split(":", 1)[1]) if spec.startswith("ollama:") else None
    mode = "add"
    if "--mode" in args:
        mode = args.pop(args.index("--mode") + 1)
        args.remove("--mode")
    main(args[0], int(args[1]) if len(args) > 1 else 2026, llm, mode)
