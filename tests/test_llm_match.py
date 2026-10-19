"""The opt-in model layer, tested with a fake model (no Ollama needed)."""
from fin_assist.llm_match import build_prompt, parse
from fin_assist.numcheck import FACTS, check_numbers

IDS = list(FACTS)


def fake(lines):
    return lambda prompt: "\n".join(lines)


def num(fid):
    return IDS.index(fid) + 1


def test_model_label_picks_the_fact_and_the_registry_supplies_the_value():
    r = check_numbers("The payroll tax ceiling for this year is $176,100.", 2026,
                      llm=fake([f"0 {num('ss.taxable_maximum')} 2026"]))
    assert r["llm"] == "used"
    assert [(c["span"], c["status"], c["expected"]) for c in r["claims"]] == [("$176,100", "stale", 184_500)]


def test_none_label_skips_the_number():
    r = check_numbers("Your salary is $176,100 and the 401(k) limit is $24,500.", 2026,
                      llm=fake(["0 0 -", f"1 {num('plan.elective_deferral')} 2026"]))
    assert [(c["span"], c["status"]) for c in r["claims"]] == [("$24,500", "match")]


def test_fact_outside_the_figures_options_counts_as_none():
    # an age fact can't label a dollar amount
    r = check_numbers("The IRA limit is $7,000.", 2026, llm=fake([f"0 {num('rmd.start_age')} 2026"]), llm_mode="label")
    assert r["claims"] == [] and r["decision"] == "PASS"


def test_add_mode_keeps_the_rules_answer_where_rules_judged():
    # the rules know this is the IRA limit; a model "none" doesn't hide it
    r = check_numbers("The IRA limit for 2026 is $7,000.", 2026, llm=fake(["0 0 -"]))
    assert [(c["span"], c["status"]) for c in r["claims"]] == [("$7,000", "stale")]


def test_add_mode_model_labels_what_the_rules_missed():
    r = check_numbers("$15,750 is what a single filer can deduct without itemizing in 2026.", 2026,
                      llm=fake([f"0 {num('tax.standard_deduction.single')} 2026"]))
    # the registry has only the 2026 figure ($16,100), so $15,750 is wrong, not provably stale
    assert [(c["span"], c["status"]) for c in r["claims"]] == [("$15,750", "wrong")]


def test_model_failure_falls_back_to_rules():
    def broken(prompt):
        raise TimeoutError("no model")
    r = check_numbers("For 2026 the 401(k) limit is $23,500.", 2026, llm=broken)
    assert r["llm"].startswith("failed, rules only")
    assert [(c["span"], c["status"]) for c in r["claims"]] == [("$23,500", "stale")]


def test_prompt_never_contains_registry_values():
    figures = [(0, "$24,500", "The 401(k) limit is $24,500.", ["plan.elective_deferral"])]
    prompt = build_prompt("The 401(k) limit is $24,500.", figures, FACTS, 2026)
    assert "23,500" not in prompt and "23500" not in prompt and "8,000" not in prompt


def test_parse_tolerates_noise_and_ignores_repeats():
    figures = [(0, "$1", "s", ["ira.limit"]), (1, "$2", "s", ["ira.limit"])]
    out = parse(f"Sure:\n0 {num('ira.limit')} 2026\n0 0 -\n1 0 -", figures, FACTS)
    assert out == {0: ("ira.limit", 2026), 1: (None, None)}
