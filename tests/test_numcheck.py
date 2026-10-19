import pytest

from fin_assist.numcheck import check_numbers


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
    assert statuses("For 2026 the standard deduction for single filers is $15,750.") == [("$15,750", "stale")]  # the 2025 figure


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
        ("$16,100", "match"), ("$31,500", "stale")]  # $31,500 is the 2025 joint figure


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


def test_topic_from_first_line_and_headings():
    text = "Here's a summary of the 2026 limits for your 401(k):\n\n- Employee deferral limit: $24,500\n- Super catch-up (ages 60-63): $10,000"
    assert statuses(text) == [("$24,500", "match"), ("$10,000", "wrong")]
    faq = "**IRAs at Pioneer**\n\n**How much can I contribute in 2026?**\nThe limit is $7,500.\n\n**I'm over 50. Can I contribute more?**\nYes, a catch-up contribution of $1,000."
    assert statuses(faq) == [("$7,500", "match"), ("$1,000", "wrong")]


def test_exact_official_figure_after_you_earn():
    assert statuses("In 2026, Social Security will withhold $1 for every $2 you earn above $23,400.") == [("$23,400", "stale")]


def test_running_totals_and_our_plan_are_skipped():
    assert statuses("For 2026 the IRA limit is $7,500.\n- Remaining room including the catch-up: $5,400") == [("$7,500", "match")]
    assert statuses("**HSA (family)**\n- IRS limit: $8,750\n\n**Our plan's numbers**\n- Family out-of-pocket max: $9,000") == [("$8,750", "match")]


def test_percentages_need_their_topic_in_the_sentence():
    text = "Your plan must withhold 20% when the distribution is paid to you. Your plan allows loans up to 50% of your vested balance at prime + 1%."
    assert statuses(text) == [("20%", "match")]
    assert statuses("Social Security tax is withheld at 6.2% up to the 2026 taxable maximum of $184,500; Medicare tax is 1.45%.") == [
        ("6.2%", "match"), ("$184,500", "match"), ("1.45%", "match")]


def test_carryover_into_next_year_is_this_years_figure():
    assert statuses("Health Care FSA for 2026: $3,400. Carryover into 2027: up to $680.") == [("$3,400", "match"), ("$680", "match")]


def test_range_continues_a_list():
    assert statuses("**2026 Head of Household**\n- 12% bracket: taxable income from $17,700 to $66,200") == [
        ("$17,700", "match"), ("$66,200", "wrong")]


# Fixes from blind set 5 (each written as a new sentence, not the set's own wording)

def test_defer_names_a_workplace_plan():
    assert statuses("This year you may defer $23,500, with a $7,500 catch-up at 50.") == [
        ("$23,500", "stale"), ("$7,500", "stale")]


def test_wage_base_applies_up_to():
    assert statuses("The Social Security payroll tax applies up to $176,100 of wages in 2026.") == [("$176,100", "stale")]


def test_able_to_contribute_states_a_limit_but_room_left_does_not():
    assert statuses("Next year you'll be able to contribute $25,000 to your 401(k).", 2026) == [("$25,000", "unknown_year")]
    assert statuses("You can contribute $9,000 more to your 401(k) this year.") == []


def test_required_distributions_at_old_age():
    assert statuses("Required distributions start at 70½ for most savers.") == [("start at 70½", "wrong")]


def test_employees_pay_medicare_rate():
    assert statuses("Employees pay 6.2% for Social Security and 2.9% for Medicare.") == [("6.2%", "match"), ("2.9%", "wrong")]


def test_roll_the_money_into_an_ira():
    assert statuses("You must roll the funds into an IRA within 30 days.") == [("30 days", "wrong")]


def test_fsa_rollover_named_after_the_figure():
    assert statuses("For 2026 your FSA allows a $640 rollover.") == [("$640", "wrong")]


def test_total_of_two_figures_is_arithmetic():
    assert check_numbers("With the $24,500 401(k) limit and the $8,000 catch-up, you can defer up to $32,500.", 2026)["decision"] == "PASS"


# Capital gains, AMT and QBI (Rev. Proc. 2024-40 for 2025, 2025-32 for 2026)

def test_capital_gains_zero_rate_stale_and_current():
    assert statuses("For 2026, single filers pay 0% on long-term capital gains up to $48,350 of taxable income.") == [
        ("$48,350", "stale")]
    assert statuses("In 2026 the 0% capital gains rate covers married filing jointly couples up to $98,900, "
                    "and the 15% rate runs to $613,700.") == [("$98,900", "match"), ("$613,700", "match")]


def test_amt_phaseout_start_dropped_in_2026():
    # The 2026 law cut the phase-out start from $626,350 to $500,000 for single filers
    r = check_numbers("For 2026, the AMT exemption for single filers is $90,100 and starts to phase out at $626,350.", 2026)
    assert [(c["span"], c["status"], c.get("expected")) for c in r["claims"]] == [
        ("$90,100", "match", None), ("$626,350", "stale", 500_000)]


def test_qbi_threshold_and_phase_in():
    assert statuses("For 2026, the QBI deduction limits start above $197,300 for single filers.") == [("$197,300", "stale")]
    assert statuses("Married filing jointly, the 2026 QBI threshold is $403,500 and it's fully phased in at $553,500.") == [
        ("$403,500", "match"), ("$553,500", "match")]


def test_2025_bracket_quoted_for_2026_is_stale():
    r = check_numbers("For 2026, the 10% bracket for single filers covers taxable income up to $11,925.", 2026)
    assert [(c["status"], c["figure_year"], c["expected"]) for c in r["claims"]] == [("stale", 2025, 12_400)]


# Estate exemption, Medicare Part B and the Roth catch-up wage threshold

def test_estate_exemption_millions():
    assert statuses("For 2026 the federal estate tax exemption is $13.99 million per person.") == [("$13.99 million", "stale")]
    assert statuses("In 2026 the lifetime gift exemption is $15 million.") == [("$15 million", "match")]


def test_medicare_part_b_premium_deductible_and_irmaa():
    assert statuses("The 2026 Medicare Part B premium is $185.00 a month and the deductible is $257.") == [
        ("$185.00", "stale"), ("$257", "stale")]
    assert statuses("In 2026, Medicare Part B IRMAA surcharges start above $109,000 for single filers "
                    "and $218,000 for married couples filing jointly.") == [("$109,000", "match"), ("$218,000", "match")]


def test_roth_catch_up_wage_threshold():
    assert statuses("Starting in 2026, the Roth catch-up wage threshold is $145,000.") == [("$145,000", "wrong")]


def test_wrong_thresholds_stated_with_a_figure_word():
    assert statuses("For 2026, the Medicare Part B IRMAA threshold for single filers is $103,000.") == [("$103,000", "wrong")]
    assert statuses("For 2026, the estate tax exemption is $14.5 million per person.") == [("$14.5 million", "wrong")]


def test_customer_amounts_next_to_thresholds_are_not_judged():
    # "Your taxable income of $230,000": the customer's number, even in a sentence about a threshold
    for text in ["Your taxable income of $230,000 is above the 2026 QBI threshold of $201,750 for single filers.",
                 "Your estate is worth about $9 million, under the 2026 estate tax exemption of $15 million.",
                 "At $120,000 of MAGI as a single filer, you will pay a Medicare Part B IRMAA surcharge in 2026.",
                 "Your AMT income of $600,000 as a single filer is above the 2026 phase-out start."]:
        assert check_numbers(text, 2026)["decision"] == "PASS", text


def test_amount_followed_by_total_is_arithmetic():
    assert check_numbers("The lifetime gift exemption is $15 million in 2026. Three gifts of $25,000 each: "
                         "that's $75,000 total.", 2026)["decision"] == "PASS"
