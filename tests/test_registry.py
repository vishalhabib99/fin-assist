import json
from pathlib import Path

import pytest

from retirement_answer_check.checker import FACTS
from retirement_answer_check.registry import load, lookup, validate

REG = load()


def test_registry_is_well_formed():
    assert validate() == []


def test_lookup_never_falls_back_to_another_year():
    assert lookup(REG, "plan.elective_deferral", 2026) == 24_500
    assert lookup(REG, "plan.elective_deferral", 2027) is None
    assert lookup(REG, "rmd.start_age", 2031) == 73


@pytest.mark.parametrize("fact_id,key", [
    ("plan.elective_deferral", "401k_403b_457_tsp_elective_deferral"),
    ("plan.catch_up_50_plus", "401k_catch_up_50_plus"),
    ("plan.catch_up_60_to_63", "401k_catch_up_60_to_63"),
    ("ira.limit", "ira_limit"),
    ("ira.limit_50_plus_total", "ira_limit_50_plus_total"),
    ("ira.catch_up_50_plus", "ira_catch_up_50_plus"),
    ("simple.limit", "simple_limit"),
    ("simple.catch_up_50_plus", "simple_catch_up_50_plus"),
])
def test_retirement_registry_matches_facts_json(fact_id, key):
    years = {y: v for y, v in FACTS["contribution_limits"][key].items() if y.isdigit()}
    assert REG[fact_id]["values"] == years


def test_rmd_and_penalties_match_facts_json():
    assert REG["rmd.start_age"]["values"]["any"] == FACTS["rmd"]["start_age"]["value"]
    assert REG["early.additional_tax_pct"]["values"]["any"] == FACTS["early_distribution"]["additional_tax_pct"]["value"]
    assert REG["rollover.window_days"]["values"]["any"] == FACTS["rollovers"]["window_days"]["value"]


# Rev. Proc. 2025-32 prints the tax owed at the bottom of each bracket. Rebuilding those
# amounts from the stored thresholds catches a threshold misread from the PDF.
BASE_TAX_2026 = {
    "single": [1_240, 5_800, 17_966, 41_024, 58_448, 192_979.25],
    "married_joint": [2_480, 11_600, 35_932, 82_048, 116_896, 206_583.50],
    "head_of_household": [1_770, 7_740, 16_155, 39_207, 56_631, 191_171],
}
RATES = [10, 12, 22, 24, 32, 35]


@pytest.mark.parametrize("status", BASE_TAX_2026)
def test_bracket_thresholds_reproduce_irs_base_tax(status):
    tops = [lookup(REG, f"tax.bracket.{status}.{r}_pct_top", 2026) for r in RATES]
    owed, prev = 0.0, 0
    for rate, top, expected in zip(RATES, tops, BASE_TAX_2026[status]):
        owed += (top - prev) * rate / 100
        prev = top
        assert owed == pytest.approx(expected, abs=0.01)


def test_values_rise_or_hold_year_over_year():
    for fid, fact in REG.items():
        years = sorted(y for y in fact["values"] if y != "any")
        vals = [fact["values"][y] for y in years]
        if fact["unit"].startswith("usd"):
            assert vals == sorted(vals), fid
