import pytest

from fin_assist.checker import FACTS
from fin_assist.room import contribution_room, roth_limit


def line(result, label):
    return next(l for l in result["lines"] if l["label"] == label)["amount"]


def test_irs_worked_example_pub_590a():
    ex = FACTS["income_phase_outs"]["roth_reduction_method"]["irs_worked_example"]
    assert roth_limit(ex["magi"], ex["base"], *ex["range"]) == ex["result"] == 6540


def test_roth_under_200_rounds_up_to_200():
    assert roth_limit(167_900, 7_500, 153_000, 168_000) == 200


def test_roth_phase_out_edges():
    assert roth_limit(153_000, 7_500, 153_000, 168_000) == 7_500
    assert roth_limit(168_000, 7_500, 153_000, 168_000) == 0


def test_under_50_with_401k():
    r = contribution_room(age_at_year_end=40, compensation=100_000, plan_type="401k",
                          plan_deferrals_so_far=10_000, magi=100_000)
    assert line(r, "401(k) / 403(b) / TSP limit") == 24_500
    assert line(r, "401(k) room left") == 14_500
    assert line(r, "IRA limit (traditional + Roth combined)") == 7_500
    assert line(r, "Roth IRA room left") == 7_500


def test_age_52_gets_50_plus_catch_up():
    r = contribution_room(age_at_year_end=52, compensation=100_000, plan_type="401k")
    assert line(r, "401(k) / 403(b) / TSP limit") == 32_500
    assert line(r, "IRA limit (traditional + Roth combined)") == 8_600


@pytest.mark.parametrize("age,cap", [(59, 32_500), (60, 35_750), (63, 35_750), (64, 32_500)])
def test_age_60_to_63_catch_up(age, cap):
    r = contribution_room(age_at_year_end=age, compensation=100_000, plan_type="401k")
    assert line(r, "401(k) / 403(b) / TSP limit") == cap


def test_ira_capped_at_compensation():
    r = contribution_room(age_at_year_end=30, compensation=4_000, magi=4_000)
    assert line(r, "IRA limit (traditional + Roth combined)") == 4_000
    assert line(r, "Roth IRA room left") == 4_000


def test_ira_limit_shared_between_traditional_and_roth():
    r = contribution_room(age_at_year_end=30, compensation=80_000, traditional_ira_so_far=3_000,
                          roth_ira_so_far=2_000, magi=80_000)
    assert line(r, "Traditional IRA room left") == 2_500
    assert line(r, "Roth IRA room left") == 2_500


def test_roth_phase_out_for_joint_filers():
    r = contribution_room(age_at_year_end=45, compensation=200_000, magi=247_000, filing_status="married_joint")
    assert line(r, "Roth IRA room left") == 3_750  # 7,500 - 0.5 * 7,500


def test_married_separate_lived_with_spouse():
    r = contribution_room(age_at_year_end=45, compensation=50_000, magi=12_000,
                          filing_status="married_separate", lived_with_spouse=True)
    assert line(r, "Roth IRA room left") == 0


def test_no_magi_means_no_roth_number():
    r = contribution_room(age_at_year_end=45, compensation=50_000)
    assert line(r, "Roth IRA room left") is None


def test_excess_ira_warns_with_fix():
    r = contribution_room(age_at_year_end=45, compensation=80_000, traditional_ira_so_far=8_000)
    assert line(r, "Traditional IRA room left") == 0
    assert any("$500 over" in w and "6%" in w for w in r["warnings"])


def test_simple_plan():
    r = contribution_room(age_at_year_end=55, compensation=60_000, plan_type="simple", plan_deferrals_so_far=5_000)
    assert line(r, "SIMPLE IRA limit") == 21_000
    assert line(r, "SIMPLE IRA room left") == 16_000


def test_rmd_note_at_73():
    assert any("minimum distributions" in n for n in contribution_room(age_at_year_end=73, compensation=0)["notes"])
    assert not any("minimum distributions" in n for n in contribution_room(age_at_year_end=72, compensation=0)["notes"])


def test_every_line_has_an_irs_source():
    r = contribution_room(age_at_year_end=61, compensation=90_000, plan_type="401k", magi=160_000)
    assert all(l["source"].startswith("https://www.irs.gov/") for l in r["lines"])


@pytest.mark.parametrize("kwargs", [{"year": 2027}, {"plan_type": "403x"}, {"filing_status": "jointly"}, {"compensation": -1}])
def test_bad_input_raises(kwargs):
    with pytest.raises(ValueError):
        contribution_room(**{"age_at_year_end": 40, "compensation": 50_000, **kwargs})
