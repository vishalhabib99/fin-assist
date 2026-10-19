"""Read an IRS inflation-adjustment Rev. Proc. and propose registry values for the year it covers.

    python scripts/revproc.py rp-26-XX.pdf            # proposed values, checks, and a diff vs the registry
    python scripts/revproc.py rp-26-XX.txt --year 2027

Maintainer tool, not part of the package. Reading a PDF needs pypdf (`pip install pypdf`);
a .txt of the PDF's text works without it. Nothing is written: the output is a diff to review,
and every value still gets checked against the PDF before it goes into registry/tax.json.

Checks before anything is trusted:
  - each bracket table's printed base-tax amounts are rebuilt from the extracted thresholds;
  - every fact the registry tracks for the year is either found or listed as not found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

N = r"\$\s?([\d,]+(?:\.\d+)?)"
RATES = [10, 12, 22, 24, 32, 35]
# Rev. Proc. order of the four tax rate tables in pypdf's text: joint, head of household, single, separate
TABLE_STATUS = ["married_joint", "head_of_household", "single", "married_separate"]


def _num(s: str) -> float:
    v = float(s.replace(",", ""))
    return int(v) if v.is_integer() else v


def text_of(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import pypdf  # maintainer-only dependency
        return "\n".join(p.extract_text() for p in pypdf.PdfReader(str(path)).pages)
    return path.read_text()


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _section(flat: str, heading: str, year: int, span: int = 3000) -> str | None:
    """The body of '.NN <heading>' that says 'beginning in <year>' (skips the table of contents)."""
    for m in re.finditer(r"\.\d\d ?" + heading, flat):
        body = flat[m.end():m.end() + span]
        if re.search(rf"(?:beginning in|calendar year|dying in calendar year) {year}\b", body[:400]):
            return body
    return None


def brackets(text: str, year: int) -> tuple[dict, list[str]]:
    flat = _flat(text)
    start = re.search(rf"\.01 ?Tax Rate Tables\. ?For taxable years beginning in {year}", flat)
    if not start:
        return {}, [f"tax rate tables for {year}: not found"]
    end = flat.find(".02", start.end())
    blocks = flat[start.end():end].split("If Taxable Income Is:")[1:]
    out, problems = {}, []
    for status, block in zip(TABLE_STATUS, blocks):
        tops = [_num(x) for x in re.findall(r"[Nn]ot over " + N, block)][:6]
        base = [_num(b) for b, _ in re.findall(N + r" plus (\d+)% of", block)]
        if status == "married_separate":
            continue  # not tracked yet
        if len(tops) != 6:
            problems.append(f"{status} brackets: found {len(tops)} thresholds, expected 6")
            continue
        owed, prev = 0.0, 0
        for rate, top, printed in zip(RATES, tops, base):
            owed += (top - prev) * rate / 100
            prev = top
            if abs(owed - printed) > 0.01:
                problems.append(f"{status} {rate}% top {top:,}: base tax rebuilds to {owed:,.2f}, IRS prints {printed:,.2f}")
        for rate, top in zip(RATES, tops):
            out[f"tax.bracket.{status}.{rate}_pct_top"] = top
    return out, problems


def _row(body: str, label: str, count: int = 1) -> list[float] | None:
    m = re.search(label + r"[^$]{0,80}?" + r"\s*".join([N] * count), body)
    return [_num(g) for g in m.groups()] if m else None


def figures(text: str, year: int) -> tuple[dict, list[str]]:
    """{fact id: value} for the year, plus a list of problems."""
    flat = _flat(text)
    out, problems = brackets(text, year)

    def put(fid, vals, i=0):
        if vals:
            out[fid] = vals[i]
        else:
            problems.append(f"{fid}: not found")

    # Standard deduction: the section for the year (later Rev. Procs. can restate an earlier year)
    std = None
    for m in re.finditer(rf"standard deduction amounts under § 63\(c\)\(2\) (?:for any taxable year beginning in {year}|are as follows)", flat):
        before = flat[max(0, m.start() - 200):m.start()]
        if f"beginning in {year}" in flat[m.start():m.end()] or f"beginning in {year}" in before:
            std = flat[m.end():m.end() + 600]
            break
    if std:
        put("tax.standard_deduction.married_joint", _row(std, r"Married Individuals Filing Joint Returns and Surviving Spouses"))
        put("tax.standard_deduction.head_of_household", _row(std, r"Heads of Households"))
        put("tax.standard_deduction.single", _row(std, r"Unmarried Individuals"))
        put("tax.standard_deduction.married_separate", _row(std, r"Married Individuals Filing Separate Returns"))
    else:
        problems.append(f"standard deduction for {year}: not found")

    aged = re.search(rf"beginning in {year}, the additional standard deduction amount under § 63\(f\) for the aged or the blind is {N}\. "
                     rf"The additional standard deduction amount is increased to {N}", flat)
    put("tax.additional_std_deduction_aged_blind_married", [_num(aged.group(1))] if aged else None)
    put("tax.additional_std_deduction_aged_blind_unmarried", [_num(aged.group(2))] if aged else None)

    cg = _section(flat, r"Maximum Capital Gains Rate", year)
    if cg:
        for fid, label in [("married_joint", r"Married Individuals Filing Joint Returns and Surviving Spouses?"),
                           ("head_of_household", r"Heads of Households?"), ("single", r"All Other Individuals")]:
            row = _row(cg, label, 2)
            put(f"tax.ltcg.{fid}.0_pct_top", row, 0)
            put(f"tax.ltcg.{fid}.15_pct_top", row, 1)
    else:
        problems.append(f"capital gains for {year}: not found")

    amt = _section(flat, r"E ?xemption Amounts for Alternative Minimum Tax", year)
    if amt:
        put("tax.amt.exemption.married_joint", _row(amt, r"Joint Returns or Surviving Spouses"))
        put("tax.amt.exemption.unmarried", _row(amt, r"Unmarried Individuals \(other than Surviving Spouses\)"))
        put("tax.amt.28_pct_threshold", _row(amt, r"All Other Taxpayers"))
        phase = amt[amt.find("phaseout of the exemption"):]
        put("tax.amt.phaseout_start.married_joint", _row(phase, r"Joint Returns or Surviving Spouses", 2), 0)
        put("tax.amt.phaseout_start.unmarried", _row(phase, r"Unmarried Individuals \(other than Surviving Spouses\)", 2), 0)
    else:
        problems.append(f"AMT for {year}: not found")

    qbi = _section(flat, r"Q ?ualified Business Income", year)
    if qbi:
        mfj, other = _row(qbi, r"Married Individuals Filing Joint Returns", 2), _row(qbi, r"All Other Returns", 2)
        put("tax.qbi.threshold.married_joint", mfj, 0)
        put("tax.qbi.phase_in_end.married_joint", mfj, 1)
        put("tax.qbi.threshold.unmarried", other, 0)
        put("tax.qbi.phase_in_end.unmarried", other, 1)
    else:
        problems.append(f"QBI for {year}: not found")

    est = re.search(rf"(?:dying in calendar year {year}, the basic exclusion amount is|basic exclusion amount to) {N}(?: for calendar year {year})?", flat)
    if est and (f"calendar year {year}" in flat[est.start() - 80:est.end() + 30]):
        out["tax.estate.basic_exclusion"] = _num(est.group(1))
    else:
        problems.append("tax.estate.basic_exclusion: not found")

    gift = re.search(rf"For calendar year {year}, the first {N} of gifts to any person", flat)
    put("gift.annual_exclusion", [_num(gift.group(1))] if gift else None)
    if gift:
        out["gift.annual_exclusion_split_spouses"] = 2 * _num(gift.group(1))

    # "health flexible 19 spending": a PDF page number can land inside the phrase
    fsa = re.search(rf"beginning in {year}, the dollar limitation under § 125\(i\) on voluntary employee salary reductions "
                    rf"for contributions to health flexible (?:\d+ )?spending arrangements is {N}", flat)
    put("health_fsa.salary_reduction_limit", [_num(fsa.group(1))] if fsa else None)
    carry = re.search(rf"maximum carryover amount (?:under Notice 2013-71 )?is {N}", flat[fsa.end():fsa.end() + 400] if fsa else "")
    put("health_fsa.max_carryover", [_num(carry.group(1))] if carry else None)
    return out, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--year", type=int, help="the year the Rev. Proc. covers (default: read from its first lines)")
    args = ap.parse_args(argv)
    text = text_of(args.path)
    year = args.year or int(re.search(r"taxable years beginning in (20\d\d)", _flat(text)).group(1))
    found, problems = figures(text, year)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from fin_assist.registry import load
    reg = load()
    print(f"{args.path.name}: {len(found)} figures for {year}")
    for fid, v in found.items():
        old = reg.get(fid, {}).get("values", {})
        now = old.get(str(year))
        prev = old.get(str(year - 1))
        note = "same as registry" if now == v else (f"CHANGE registry has {now:,}" if now is not None else
                                                    f"new year (was {prev:,} for {year - 1})" if prev is not None else "new")
        print(f"  {fid:52} {v:>14,}  {note}")
    tracked = [fid for fid, f in reg.items() if fid.startswith(("tax.", "gift.", "health_fsa.")) and fid not in found]
    for fid in tracked:
        problems.append(f"{fid}: tracked but not extracted")
    for p in problems:
        print("  PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
