"""scripts/retirement_notice.py must reproduce, from the IRS notice alone, every limit the registry holds."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import retirement_notice as rn  # noqa: E402

from fin_assist.registry import load  # noqa: E402

REG = load()
FIX = ROOT / "tests" / "fixtures"
TRACKED = list(rn.SECTIONS) + ["ira.limit_50_plus_total"]


def test_every_tracked_limit_matches_the_registry_for_every_notice():
    for name, year in [("n-24-80.txt", 2025), ("n-25-67.txt", 2026), ("n-26-66.txt", 2027)]:
        found, _, problems = rn.figures((FIX / name).read_text(), year)
        assert problems == [], name
        assert found == {fid: REG[fid]["values"][str(year)] for fid in TRACKED}, name


def test_increased_from_matches_last_years_registry_figure():
    _, before, _ = rn.figures((FIX / "n-25-67.txt").read_text(), 2026)
    assert before and all(REG[fid]["values"]["2025"] == v for fid, v in before.items())


def test_the_catch_up_50_section_does_not_match_its_sub_section():
    # 414(v)(2)(B)(i) is the 401(k) catch-up; (B)(ii) is the SIMPLE one, cited later in the notice
    found, _, _ = rn.figures((FIX / "n-25-67.txt").read_text(), 2026)
    assert found["plan.catch_up_50_plus"] == 8_000 and found["simple.catch_up_50_plus"] == 4_000


def test_reads_increases_from_wording():
    # Notice 2026-66 words the 60-63 catch-up "increases from $11,250 to $11,750"; the old pattern
    # skipped it and took the next sentence's Roth wage threshold ($155,000) instead
    found, before, problems = rn.figures((FIX / "n-26-66.txt").read_text(), 2027)
    assert problems == []
    assert found["plan.catch_up_60_to_63"] == 11_750 and before["plan.catch_up_60_to_63"] == 11_250
