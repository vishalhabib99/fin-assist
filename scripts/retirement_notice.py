"""Read the IRS's yearly retirement-plan notice and propose registry values for the year it covers.

    python scripts/retirement_notice.py n-26-XX.pdf     # e.g. Notice 2025-67 for 2026

Same rules as scripts/revproc.py: needs pypdf for a .pdf (a .txt works without it), writes
nothing, and every value is checked against the PDF before it goes into the registry.

Each limit in the notice reads "The limitation under section X ... is increased from $A to $B"
(or "remains $B", or "is $B"), so figures are found by their Code section. The "from $A" is
checked against the registry's value for the year before.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from revproc import N, _flat, _num, report, text_of

# fact id -> the Code section the notice names it by
SECTIONS = {
    "plan.elective_deferral": r"section 402\(g\)\(1\)",
    "plan.catch_up_50_plus": r"section 414\(v\)\(2\)\(B\)\(i\)",
    "plan.catch_up_60_to_63": r"section 414\(v\)\(2\)\(E\)\(i\)",
    "plan.roth_catch_up_wage_threshold": r"section 414\(v\)\(7\)\(A\)",
    "simple.limit": r"section 408\(p\)\(2\)\(E\)\(i\)\(III\)",
    "simple.catch_up_50_plus": r"section 414\(v\)\(2\)\(B\)\(ii\)",
    "ira.limit": r"section 219\(b\)\(5\)\(A\)",
    "ira.catch_up_50_plus": r"section 219\(b\)\(5\)\(B\)\(ii\)",
}
_VALUE = re.compile(rf"(?:is increased from {N} to|is decreased from {N} to|remains|is) {N}")


def figures(text: str, year: int) -> tuple[dict, dict, list[str]]:
    """({fact id: value}, {fact id: last year's value the notice states}, problems)."""
    flat = _flat(text)
    found, before, problems = {}, {}, []
    for fid, section in SECTIONS.items():
        m = re.search(section + r"(?![\d(])", flat)
        # the sentence that cites the section, up to its figure
        v = _VALUE.search(flat, m.end(), m.end() + 600) if m else None
        if not v:
            problems.append(f"{fid}: not found")
            continue
        found[fid] = _num(v.group(3))
        if v.group(1) or v.group(2):
            before[fid] = _num(v.group(1) or v.group(2))
    if "ira.limit" in found and "ira.catch_up_50_plus" in found:
        found["ira.limit_50_plus_total"] = found["ira.limit"] + found["ira.catch_up_50_plus"]
    return found, before, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--year", type=int, help="the year the notice covers (default: read from its title)")
    args = ap.parse_args(argv)
    text = text_of(args.path)
    year = args.year or int(re.search(r"(20\d\d) Amounts Relating to Retirement Plans", _flat(text)).group(1))
    found, before, problems = figures(text, year)

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from fin_assist.registry import load
    reg = load()
    for fid, v in before.items():  # the notice's "increased from $A" should be our figure for the year before
        ours = reg.get(fid, {}).get("values", {}).get(str(year - 1))
        if ours is not None and ours != v:
            problems.append(f"{fid}: notice says {year - 1} was {v:,}, registry has {ours:,}")
    return report(args.path.name, found, problems, year, tuple(f + "" for f in SECTIONS) + ("ira.limit_50_plus_total",))


if __name__ == "__main__":
    raise SystemExit(main())
