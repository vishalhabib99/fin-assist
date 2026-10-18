import pytest

from fin_doctor.numcheck import check_numbers


def statuses(text, year=2026):
    return [(c["span"], c["status"]) for c in check_numbers(text, year)["claims"]]


def test_stale_401k_and_catch_up_quoted_as_this_year():
    r = check_numbers("For 2026 you can put up to $23,500 in your 401(k), plus a $7,500 catch-up if you're 50 or older.", 2026)
    assert r["decision"] == "REVIEW"
    assert [(c["status"], c["figure_year"], c["expected"]) for c in r["claims"]] == [("stale", 2025, 24_500), ("stale", 2025, 8_000)]


def test_year_over_year_sentence_reads_each_figure_with_its_own_year():
    r = check_numbers("The 401(k) limit rose from $23,500 in 2025 to $24,500 in 2026. The IRA limit is $7,500.", 2026)
    assert r["decision"] == "PASS" and [c["year"] for c in r["claims"]] == [2025, 2026, 2026]


def test_stale_hsa():
    assert statuses("HSA limits for 2026 are $4,300 for self-only coverage and $8,550 for family coverage.") == [
        ("$4,300", "stale"), ("$8,550", "stale")]


def test_hsa_2027_is_known():
    assert statuses("For 2027 the HSA limit is $4,500 for self-only coverage and $9,000 for family coverage.") == [
        ("$4,500", "match"), ("$9,000", "match")]


def test_next_years_figure_quoted_for_this_year():
    assert statuses("Your 2026 HSA limit with self-only coverage is $4,500.") == [("$4,500", "wrong_year")]


def test_old_rmd_age_is_wrong_and_age_75_is_unverified():
    assert statuses("RMDs start at age 72.") == [("age 72", "wrong")]
    assert statuses("If you were born in 1960 or later, RMDs start at age 75.") == [("age 75", "unverified")]


def test_unpublished_year_is_unknown_not_stale():
    assert statuses("In 2027 the 401(k) limit is $24,500.") == [("$24,500", "unknown_year")]


def test_customer_amounts_are_not_judged():
    r = check_numbers("If you earn $100,000 and have $250,000 saved, your 401(k) limit for 2026 is $24,500.", 2026)
    assert [c["span"] for c in r["claims"]] == ["$24,500"] and r["decision"] == "PASS"


def test_social_security_and_tax():
    assert statuses("In 2026 Social Security taxes earnings up to $176,100.") == [("$176,100", "stale")]
    assert statuses("The 2027 COLA is 3.6%.") == [("3.6%", "match")]
    assert statuses("For 2026 the standard deduction is $32,200 for married couples filing jointly.") == [("$32,200", "match")]
    assert statuses("For 2026 the standard deduction for single filers is $15,750.") == [("$15,750", "wrong")]


def test_year_carries_from_an_earlier_sentence():
    r = check_numbers("Here are the 2027 numbers. The HSA limit for family coverage is $8,750.", 2026)
    assert [(c["year"], c["status"]) for c in r["claims"]] == [(2027, "stale")]


def test_k_and_dollars_spellings():
    assert statuses("The 2026 IRA limit is $7.5k.") == [("$7.5k", "match")]
    assert statuses("The 2026 IRA limit is 7,000 dollars.") == [("7,000 dollars", "stale")]


def test_every_flag_carries_a_source():
    for c in check_numbers("RMDs start at age 72. In 2026 the IRA limit is $7,000.", 2026)["claims"]:
        assert c["source"].startswith("https://")


def test_empty_answer_passes_with_no_claims():
    assert check_numbers("", 2026) == {"decision": "PASS", "year": 2026, "claims": []}


def test_topic_named_in_the_previous_sentence():
    assert statuses("TSP participants aged 60-63 get a super catch-up. For 2026 that's $10,000 on top of the regular limit.") == [
        ("$10,000", "wrong")]


def test_year_after_the_topic_word():
    assert statuses("SSA has announced a 3.6% COLA for 2027.") == [("3.6%", "match")]


def test_customer_amounts_near_a_limit_are_skipped():
    assert statuses("The 2026 401(k) limit is $24,500, and you're on pace for about $16,800.") == [("$24,500", "match")]
    assert statuses("You can give $19,000 per recipient in 2026 without filing a gift tax return. Since you're planning to give your daughter $25,000, you'd file Form 709.") == [
        ("$19,000", "match")]


def test_arithmetic_and_plans_are_not_judged():
    assert statuses("You said you're saving $500 a month into your Roth IRA. That's $6,000 for the year.") == []
    assert statuses("The 2026 IRA limit is $7,500, so the $5,000 you planned to put in this year is fine.") == [("$7,500", "match")]


def test_one_topic_word_covers_a_list():
    assert statuses("For 2026, the standard deduction is $16,100 for single filers and $31,500 for married couples filing jointly.") == [
        ("$16,100", "match"), ("$31,500", "wrong")]


def test_old_rmd_rules():
    assert statuses("You need to start RMDs at age 70½.") == [("age 70½", "wrong")]
    assert statuses("Required minimum distributions begin at 73. If you miss one, the IRS penalty is 50% of the shortfall.") == [
        ("begin at 73", "match"), ("50%", "wrong")]
    assert statuses("Traditional IRA owners must begin RMDs at 70½.") == [("RMDs at 70½", "wrong")]


def test_markdown_table_takes_topic_and_year_from_headers():
    table = "| Account | 2026 | 2027 |\n|---|---|---|\n| 401(k) deferral | $24,500 | $25.5k |\n| HSA (self-only) | $4,400 | $4,500 |"
    assert statuses(table) == [("$24,500", "match"), ("$25.5k", "unknown_year"), ("$4,400", "match"), ("$4,500", "match")]


def test_our_plan_and_estimates_are_not_judged():
    assert statuses("Our Bronze HSA plan has a $2,000 individual deductible and a $7,250 out-of-pocket max.") == []
    assert statuses("Your estimated benefit at 67, based on your earnings record, is $2,880/month.") == []


def test_from_to_pairs_take_the_years_in_order():
    r = check_numbers("The self-only HSA limit rises from $4,400 in 2026 to $4,500 in 2027, and the family limit goes from $8,750 to $9,000.", 2026)
    assert [(c["span"], c["year"], c["status"]) for c in r["claims"]] == [
        ("$4,400", 2026, "match"), ("$4,500", 2027, "match"), ("$8,750", 2026, "match"), ("$9,000", 2027, "match")]


def test_gift_splitting():
    assert statuses("In 2026 a married couple splitting gifts can give each grandchild up to $38,000 without filing.") == [("$38,000", "match")]
