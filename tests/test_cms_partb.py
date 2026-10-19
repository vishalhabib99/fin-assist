"""scripts/cms_partb.py must reproduce, from the CMS fact sheet alone, every Medicare figure the registry holds."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cms_partb  # noqa: E402

from fin_assist.registry import load  # noqa: E402

REG = load()
FIX = ROOT / "tests" / "fixtures"
TRACKED = [fid for fid in REG if fid.startswith("medicare.")]


def test_both_fact_sheets_reproduce_the_registry():
    for year in (2025, 2026):
        got_year, found, before, problems = cms_partb.figures((FIX / f"cms-{year}.txt").read_text())
        assert got_year == year and problems == []
        assert found == {fid: REG[fid]["values"][str(year)] for fid in TRACKED}
        for fid, (y, v) in before.items():  # "an increase of $17.90 from $185.00 in 2025"
            assert REG[fid]["values"][str(y)] == v


def test_a_misread_premium_fails_the_stated_change():
    text = (FIX / "cms-2026.txt").read_text().replace("will be $202.90 for 2026", "will be $203.90 for 2026", 1)
    _, _, _, problems = cms_partb.figures(text)
    assert any("premium" in p for p in problems)
