"""scripts/revproc.py must reproduce, from the IRS text alone, every figure the registry holds."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import revproc  # noqa: E402

from fin_assist.registry import load  # noqa: E402

REG = load()
FIX = ROOT / "tests" / "fixtures"
TRACKED = [fid for fid in REG if fid.startswith(("tax.", "gift.", "health_fsa."))]
# Rev. Proc. 2024-40 printed the 2025 standard deduction before the 2025 tax law raised it;
# Rev. Proc. 2025-32 sec. 3.01 replaced those amounts, and the registry holds the replacements.
SUPERSEDED_2025 = {"tax.standard_deduction.single": 15_000, "tax.standard_deduction.married_separate": 15_000,
                   "tax.standard_deduction.married_joint": 30_000, "tax.standard_deduction.head_of_household": 22_500}


def extract(name, year):
    return revproc.figures((FIX / name).read_text(), year)


def test_2026_rev_proc_reproduces_every_registry_figure():
    found, problems = extract("rp-25-32.txt", 2026)
    assert problems == []
    assert {fid: REG[fid]["values"]["2026"] for fid in TRACKED} == {fid: found[fid] for fid in TRACKED}


def test_2025_rev_proc_reproduces_the_registry_except_the_superseded_deduction():
    found, problems = extract("rp-24-40.txt", 2025)
    assert problems == []
    for fid in TRACKED:
        if "2025" in REG[fid]["values"]:
            assert found[fid] == SUPERSEDED_2025.get(fid, REG[fid]["values"]["2025"]), fid


def test_a_misread_threshold_fails_the_base_tax_rebuild():
    text = (FIX / "rp-25-32.txt").read_text().replace("Not over $24,800", "Not over $24,900", 1)
    _, problems = revproc.figures(text, 2026)
    assert any("married_joint" in p and "base tax" in p for p in problems)


def test_year_is_read_from_the_document():
    for name, year in [("rp-24-40.txt", 2025), ("rp-25-32.txt", 2026)]:
        flat = revproc._flat((FIX / name).read_text())
        assert int(re.search(r"taxable years beginning in (20\d\d)", flat).group(1)) == year
