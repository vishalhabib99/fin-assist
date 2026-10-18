"""MCP server for fin-doctor (stdio)."""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from .checker import FACTS, check
from .numcheck import check_numbers as _check_numbers
from .room import contribution_room as _room

mcp = MCPServer("fin-doctor")
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


@mcp.tool(annotations=READ_ONLY)
def check_answer(question: str, answer: str) -> dict:
    """Check an AI-drafted answer to a US retirement-account question before it is sent to a customer.

    Verifies numbers and rules (contribution limits, RMDs, rollovers, early-distribution tax and
    exceptions, excess contributions) against IRS-sourced facts, flags out-of-scope topics, and
    runs phrase rules for personal recommendations and promissory claims. Text in the draft that
    addresses the checker instead of the customer is flagged as injection_attempt. Returns
    {"decision": "SEND" | "REVIEW", "flags": [{"type", "span", "reason", "source"}]}.
    Any number the facts table can't verify returns REVIEW, never SEND. The phrase rules are a
    baseline only: also run the advice-judge skill before treating SEND as final.

    Args:
        question: The customer's question, verbatim.
        answer: The AI-drafted answer to check, verbatim. An empty answer returns REVIEW.
    """
    try:
        return check(question, answer)
    except Exception as exc:  # never let a checker bug turn into a silent SEND
        return {"decision": "REVIEW", "flags": [{"type": "checker_error", "span": "", "source": None,
                "reason": f"checker failed ({type(exc).__name__}: {exc}); route this answer to a human"}]}


@mcp.tool(annotations=READ_ONLY)
def get_facts() -> dict:
    """Return the full IRS-sourced facts table the checker verifies against.

    Includes contribution limits by tax year, RMD rules, rollover rules, early-distribution tax and
    exceptions, and the source URL for every entry, plus the date the values were verified. Use it
    to show a reviewer why a number was flagged. Takes no arguments.
    """
    try:
        return FACTS
    except Exception as exc:
        raise RuntimeError(f"facts table unavailable ({exc}); check data/facts.json is present and valid JSON") from exc


@mcp.tool(annotations=READ_ONLY)
def contribution_room(
    age_at_year_end: int,
    compensation: float,
    year: int = 2026,
    plan_type: str = "none",
    plan_deferrals_so_far: float = 0,
    traditional_ira_so_far: float = 0,
    roth_ira_so_far: float = 0,
    magi: float | None = None,
    filing_status: str = "single",
    lived_with_spouse: bool = False,
) -> dict:
    """Compute how much more a person can contribute this year to a 401(k)/403(b)/TSP or SIMPLE IRA,
    a traditional IRA and a Roth IRA, using IRS-sourced limits. Deterministic: call this instead of
    stating contribution limits from memory, which are often last year's.

    Returns {"lines": [{"label", "amount", "why", "source"}], "warnings", "notes", "not_covered"}.
    Relay "not_covered" to the user rather than filling those gaps. Not tax or financial advice.

    Args:
        age_at_year_end: The person's age on December 31 of `year`. Drives the 50+ and 60-63 catch-ups.
        compensation: Taxable compensation (wages, self-employment income) for the year. Caps the IRA limit.
        year: Tax year. Only 2026 is supported.
        plan_type: "401k" (also 403(b) and TSP), "simple", or "none".
        plan_deferrals_so_far: Employee deferrals to the workplace plan so far this year.
        traditional_ira_so_far: Traditional IRA contributions made for this year so far.
        roth_ira_so_far: Roth IRA contributions made for this year so far.
        magi: Modified AGI for Roth purposes. Without it, no Roth amount is returned.
        filing_status: "single", "head_of_household", "married_joint", "married_separate" or
            "qualifying_surviving_spouse".
        lived_with_spouse: For married_separate only: whether they lived with their spouse at any time in the year.
    """
    try:
        return _room(age_at_year_end, compensation, year, plan_type, plan_deferrals_so_far,
                     traditional_ira_so_far, roth_ira_so_far, magi, filing_status, lived_with_spouse)
    except ValueError as exc:
        raise ToolError(f"{exc}. Fix the input and call again.") from exc


@mcp.tool(annotations=READ_ONLY)
def check_numbers(answer: str, year: int | None = None) -> dict:
    """Check every official financial figure in an AI-drafted answer against a verified registry
    of IRS and SSA figures: retirement-plan and IRA limits, RMD age, HSA/HDHP limits, Social
    Security wage base, COLA and earnings test, federal tax brackets, standard deduction, gift exclusion.

    Catches stale figures (last year's limit quoted as this year's), next year's figure quoted
    early, and plainly wrong figures. Customer-specific amounts (salaries, balances) are not judged.
    Returns {"decision": "PASS" | "REVIEW", "year", "claims": [{"span", "value", "year", "status",
    "fact", "label", "expected", "figure_year", "source", "sentence"}]}. status is one of match,
    stale, wrong_year, wrong, unknown_year (registry has no figure for that year yet) or unverified.
    PASS means no recognized figure is wrong, not that the answer is correct.

    Args:
        answer: The AI-drafted answer, verbatim.
        year: Tax year the answer is about when a sentence doesn't say. Default: the current year.
    """
    try:
        return _check_numbers(answer, year)
    except Exception as exc:  # never let a checker bug turn into a silent PASS
        return {"decision": "REVIEW", "year": year, "claims": [], "error":
                f"number check failed ({type(exc).__name__}: {exc}); route this answer to a human"}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
