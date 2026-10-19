"""Read CMS's yearly Medicare Part B fact sheet and propose registry values for the year it covers.

    python scripts/cms_partb.py page.html      # saved from cms.gov/newsroom/fact-sheets/<year>-medicare-parts-b-premiums-...
    python scripts/cms_partb.py page.txt

Same rules as scripts/revproc.py: writes nothing, every value is checked on the page before it
goes into registry/medicare.json. The sheet states last year's premium and deductible too
("an increase of $17.90 from $185.00 in 2025"), and those are checked against the registry.
"""
from __future__ import annotations

import argparse
import html as _html
import re
import sys
from pathlib import Path

from revproc import N, _flat, _num, report


def text_of(path: Path) -> str:
    raw = path.read_text(errors="ignore")
    if path.suffix.lower() in (".html", ".htm"):
        raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
        raw = _html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return _flat(raw)


def figures(text: str) -> tuple[int | None, dict, dict, list[str]]:
    """(year, {fact id: value}, {fact id: (last year, value)}, problems)."""
    flat = _flat(text)
    found, before, problems = {}, {}, []
    prem = re.search(rf"standard monthly premium for Medicare Part B enrollees will be {N} for (20\d\d),"
                     rf" an (?:increase|decrease) of {N} from {N} in (20\d\d)", flat)
    year = int(prem.group(2)) if prem else None
    if prem:
        found["medicare.part_b.standard_premium"] = _num(prem.group(1))
        before["medicare.part_b.standard_premium"] = (int(prem.group(5)), _num(prem.group(4)))
        if abs(_num(prem.group(1)) - _num(prem.group(4)) - _num(prem.group(3))) > 0.005:
            problems.append("premium: this year minus last year doesn't equal the stated change")
    else:
        problems.append("medicare.part_b.standard_premium: not found")
    ded = re.search(rf"annual deductible for all Medicare Part B beneficiaries will be {N} in (20\d\d),"
                    rf" an (?:increase|decrease) of {N} from the annual deductible of {N} in (20\d\d)", flat)
    if ded and (year is None or int(ded.group(2)) == year):
        found["medicare.part_b.deductible"] = _num(ded.group(1))
        before["medicare.part_b.deductible"] = (int(ded.group(5)), _num(ded.group(4)))
        if abs(_num(ded.group(1)) - _num(ded.group(4)) - _num(ded.group(3))) > 0.005:
            problems.append("deductible: this year minus last year doesn't equal the stated change")
    else:
        problems.append("medicare.part_b.deductible: not found")
    # IRMAA table, full Part B coverage: the first row is where the surcharge starts
    tier = re.search(rf"Less than or equal to {N} Less than or equal to {N} \$?0\.00 \$?([\d.]+)", flat)
    if tier:
        found["medicare.irmaa.start.single"] = _num(tier.group(1))
        found["medicare.irmaa.start.married_joint"] = _num(tier.group(2))
        if "medicare.part_b.standard_premium" in found and abs(_num(tier.group(3)) - found["medicare.part_b.standard_premium"]) > 0.005:
            problems.append("IRMAA table's first row doesn't show the standard premium; wrong table?")
    else:
        problems.append("IRMAA table: not found")
    return year, found, before, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    args = ap.parse_args(argv)
    year, found, before, problems = figures(text_of(args.path))
    if year is None:
        print("could not read the year from the premium sentence")
        return 1
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from fin_assist.registry import load
    reg = load()
    for fid, (y, v) in before.items():
        ours = reg.get(fid, {}).get("values", {}).get(str(y))
        if ours is not None and abs(ours - v) > 0.005:
            problems.append(f"{fid}: sheet says {y} was {v:,}, registry has {ours:,}")
    return report(args.path.name, found, problems, year, ("medicare.",))


if __name__ == "__main__":
    raise SystemExit(main())
