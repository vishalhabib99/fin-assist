"""The pre-send gate: run fin-assist on a draft before the customer sees it.

    from fin_assist.gate import gate

Three outcomes:
  send     no problems found; send the draft as written
  fixed    only stale or early figures, each with one known right value: those figures were
           replaced, and every replacement is listed so you can log it
  review   anything else (a wrong figure, an unpublished year, advice or promissory wording,
           text aimed at the checker): hold the draft and send the holding message instead
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fin_assist import check
from fin_assist.numcheck import check_numbers

# Advice-boundary flags from the retirement checker. Its fact flags are left out here because
# check_numbers covers figures across every area (HSA, Social Security, tax), not just retirement.
ADVICE_FLAGS = {"personal_recommendation", "promissory", "injection_attempt", "empty_answer"}
HOLDING_MESSAGE = "Thanks for your question. A specialist will review this answer and follow up shortly."


@dataclass
class Verdict:
    outcome: str                      # "send" | "fixed" | "review"
    text: str                         # what to show the customer
    fixes: list[dict] = field(default_factory=list)
    reasons: list[dict] = field(default_factory=list)


def _money(value: float, span: str) -> str:
    if span.endswith("%"):
        return f"{value:g}%"
    if span.startswith("$"):
        return f"${value:,.0f}"
    return f"{value:g}"


def gate(question: str, draft: str, year: int | None = None) -> Verdict:
    numbers = check_numbers(draft, year)
    advice = [f for f in check(question, draft)["flags"] if f["type"] in ADVICE_FLAGS]
    fixable = [c for c in numbers["claims"]
               if c["status"] in ("stale", "wrong_year") and isinstance(c.get("expected"), (int, float))]
    blocking = [c for c in numbers["claims"] if c["status"] != "match" and c not in fixable]

    if advice or blocking:
        return Verdict("review", HOLDING_MESSAGE, reasons=advice + blocking)
    if not fixable:
        return Verdict("send", draft)

    text = draft
    for c in fixable:
        right = _money(c["expected"], c["span"])
        text = text.replace(c["span"], right, 1)
        c["replacement"] = right
    return Verdict("fixed", text, fixes=fixable)
