import importlib
import json
import sys
from pathlib import Path

import pytest

from fin_doctor.gate import HOLDING_MESSAGE, gate

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_stale_figure_is_fixed_and_logged():
    v = gate("401(k) limit?", "For 2026 you can defer up to $23,500 into your 401(k).", 2026)
    assert v.outcome == "fixed" and "$24,500" in v.text and "$23,500" not in v.text
    assert v.fixes[0]["figure_year"] == 2025 and v.fixes[0]["source"].startswith("https://www.irs.gov")


def test_wrong_figure_unpublished_year_and_advice_are_held():
    assert gate("RMDs?", "RMDs start at age 72.", 2026).outcome == "review"
    assert gate("2027?", "The 401(k) limit for 2027 is $25,500.", 2026).outcome == "review"
    v = gate("Roll over?", "Most people in your situation roll it over, so that's the right move for you.", 2026)
    assert v.outcome == "review" and v.text == HOLDING_MESSAGE


def test_clean_answer_is_sent_unchanged():
    draft = "For 2026 the HSA limit for family coverage is $8,750."
    assert gate("HSA?", draft, 2026).text == draft


def test_canned_drafts_run_end_to_end():
    outcomes = []
    for line in (EXAMPLES / "canned_drafts.jsonl").read_text().splitlines():
        row = json.loads(line)
        outcomes.append(gate(row["question"], row["draft"], 2026).outcome)
    assert outcomes == ["fixed", "send", "review", "review", "fixed", "review"]


def test_streaming_hold_and_correct():
    sys.path.insert(0, str(EXAMPLES))
    s = importlib.import_module("streaming_agent")
    stream = lambda: iter(["For 2026 the IRA limit ", "is $7,000."])
    assert s.hold("IRA?", stream()) == "For 2026 the IRA limit is $7,500."
    shown, replaced = [], []
    s.correct("IRA?", stream(), shown.append, replaced.append)
    assert "".join(shown) == "For 2026 the IRA limit is $7,000." and replaced == ["For 2026 the IRA limit is $7,500."]


def test_langchain_example():
    pytest.importorskip("langchain_core")
    sys.path.insert(0, str(EXAMPLES))
    lc = importlib.import_module("langchain_agent")
    assert lc.chain.invoke({"question": "IRA limit?"}) == "For 2026 the IRA contribution limit is $7,500, or $8,600 if you're 50 or older."
