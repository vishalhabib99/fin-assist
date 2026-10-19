"""Contribution room: how much more a person can put into each account this year.

Deterministic, no model. Every number comes from data/facts.json and every line
carries its IRS source. Anything the facts table doesn't cover is listed under
"not_covered" instead of being guessed.
"""
from __future__ import annotations

from .checker import FACTS

SUPPORTED_YEARS = (2026,)
FILING_STATUSES = ("single", "head_of_household", "married_joint", "married_separate", "qualifying_surviving_spouse")
PLAN_TYPES = ("none", "401k", "simple")

_LIMITS = FACTS["contribution_limits"]
_ROTH = FACTS["income_phase_outs"]["roth_ira_contribution"]
_SRC = FACTS["sources"]


def _limit(key: str, year: int) -> int | None:
    return _LIMITS.get(key, {}).get(str(year))


def _line(label: str, amount: int | None, why: str, source: str) -> dict:
    return {"label": label, "amount": amount, "why": why, "source": _SRC[source]}


def _roth_range(year: int, status: str, lived_with_spouse: bool) -> list[int]:
    if status in ("married_joint", "qualifying_surviving_spouse"):
        return _ROTH["married_joint_or_qualifying_surviving_spouse"][str(year)]
    if status == "married_separate" and lived_with_spouse:
        return _ROTH["married_separate_lived_with_spouse"][str(year)]
    return _ROTH["single_hoh_mfs_not_lived_with_spouse"][str(year)]


def roth_limit(magi: float, base: int, range_start: int, range_end: int, other_ira: int = 0) -> int:
    """Pub 590-A Worksheet 2-2. `base` is the lesser of the IRA limit or taxable compensation;
    `other_ira` is this year's contributions to traditional IRAs."""
    if magi >= range_end:
        reduced = 0
    elif magi <= range_start:
        reduced = base
    else:
        # Integer math so this matches docs/room/room.js exactly (no float or banker's rounding drift).
        span, over = range_end - range_start, int(magi) - range_start
        ratio_milli = (2 * over * 1000 + span) // (2 * span)        # line 5, 3 places, half up
        reduced = -(-(base * (1000 - ratio_milli)) // 10_000) * 10  # lines 7-8, up to the next $10
        if 0 < reduced < 200:
            reduced = 200
    return max(0, min(reduced, base - other_ira))                           # lines 10-11


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
    if year not in SUPPORTED_YEARS:
        raise ValueError(f"year {year} isn't supported; supported: {SUPPORTED_YEARS}")
    if plan_type not in PLAN_TYPES:
        raise ValueError(f"plan_type must be one of {PLAN_TYPES}")
    if filing_status not in FILING_STATUSES:
        raise ValueError(f"filing_status must be one of {FILING_STATUSES}")
    if age_at_year_end < 0 or compensation < 0 or min(plan_deferrals_so_far, traditional_ira_so_far, roth_ira_so_far) < 0:
        raise ValueError("age, compensation and amounts so far can't be negative")

    lines, warnings = [], []
    not_covered = [
        "Spousal IRA (contributing on a spouse's compensation)",
        "Traditional IRA deductibility (you can contribute, but the deduction may be limited)",
        "Roth catch-up requirement for higher earners in workplace plans",
        "Employer contributions and the overall plan limit",
        "457(b) plans, and having more than one workplace plan",
        "Whether your plan offers catch-up contributions",
    ]
    catch_up_50 = age_at_year_end >= 50

    # Workplace plan
    if plan_type == "401k":
        base = _limit("401k_403b_457_tsp_elective_deferral", year)
        if 60 <= age_at_year_end <= 63:
            cu, cu_why = _limit("401k_catch_up_60_to_63", year), "age 60-63 catch-up"
        elif catch_up_50:
            cu, cu_why = _limit("401k_catch_up_50_plus", year), "age 50+ catch-up"
        else:
            cu, cu_why = 0, "no catch-up under age 50"
        cap = base + cu
        lines.append(_line("401(k) / 403(b) / TSP limit", cap, f"${base:,} + ${cu:,} {cu_why}" if cu else cu_why, "irs_2026_limits"))
        lines.append(_line("401(k) room left", max(0, int(cap - plan_deferrals_so_far)),
                           "limit minus what you've deferred so far this year", "irs_2026_limits"))
        if plan_deferrals_so_far > cap:
            warnings.append(f"You've deferred ${plan_deferrals_so_far - cap:,.0f} over the limit. Ask your plan to return the excess.")
    elif plan_type == "simple":
        base = _limit("simple_limit", year)
        cu = _limit("simple_catch_up_50_plus", year) if catch_up_50 else 0
        cap = base + cu
        lines.append(_line("SIMPLE IRA limit", cap, f"${base:,} + ${cu:,} catch-up" if cu else f"${base:,}", "irs_2026_limits"))
        lines.append(_line("SIMPLE IRA room left", max(0, int(cap - plan_deferrals_so_far)),
                           "limit minus what you've deferred so far this year", "irs_2026_limits"))
        not_covered.append("SIMPLE higher limits for some employers, and the SIMPLE age 60-63 catch-up")

    # IRA (one limit across traditional + Roth)
    ira_dollar = _limit("ira_limit_50_plus_total" if catch_up_50 else "ira_limit", year)
    ira_base = int(min(ira_dollar, compensation))
    ira_used = traditional_ira_so_far + roth_ira_so_far
    why = "age 50+ limit, including the catch-up" if catch_up_50 else "standard limit"
    if compensation < ira_dollar:
        why += f", capped at your earned income of ${compensation:,.0f}"
    lines.append(_line("IRA limit (traditional + Roth combined)", ira_base, why, "irs_ira_limits"))
    lines.append(_line("Traditional IRA room left", max(0, int(ira_base - ira_used)),
                       "combined limit minus all IRA contributions so far", "irs_ira_limits"))
    if ira_used > ira_base:
        excess = FACTS["excess_ira_contribution"]
        warnings.append(f"Your IRA contributions are ${ira_used - ira_base:,.0f} over the limit. A "
                        f"{excess['excise_pct_per_year']['value']}% tax applies each year it stays; to avoid it, "
                        f"{excess['avoid_by']['value']}.")

    if magi is None:
        lines.append(_line("Roth IRA room left", None, "enter your modified AGI to check the Roth income limit", "irs_2026_limits"))
    else:
        start, end = _roth_range(year, filing_status, lived_with_spouse)
        roth_cap = roth_limit(magi, ira_base, start, end, int(traditional_ira_so_far))
        if magi >= end:
            rwhy = f"modified AGI is at or above ${end:,}, so no Roth contribution is allowed"
        elif magi > start:
            rwhy = f"reduced: modified AGI is in the ${start:,}-${end:,} phase-out (IRS Pub 590-A Worksheet 2-2)"
        else:
            rwhy = f"full amount: modified AGI is below ${start:,}"
        lines.append(_line("Roth IRA room left", max(0, min(roth_cap - int(roth_ira_so_far), ira_base - int(ira_used))),
                           rwhy, "irs_2026_limits" if magi <= start or magi >= end else "irs_p590a"))

    deadline = _LIMITS["ira_contribution_deadline"]["value"]
    notes = [f"IRA contributions for {year} can be made until {deadline} (IRS Pub 590-A)."]
    if age_at_year_end >= FACTS["rmd"]["start_age"]["value"]:
        notes.append(f"At {age_at_year_end}, required minimum distributions apply to traditional IRAs and workplace plans. "
                     f"The first is due {FACTS['rmd']['first_rmd_deadline']['value']}.")

    return {"year": year, "lines": lines, "warnings": warnings, "notes": notes, "not_covered": not_covered,
            "facts_verified_on": FACTS["_verified_on"],
            "disclaimer": "General IRS rules, not tax or financial advice."}
