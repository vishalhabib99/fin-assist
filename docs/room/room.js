// Contribution room, same rules as src/fin_assist/room.py.
// tests/test_room_parity.py runs both on the same inputs and fails on any difference.
(function (root) {
  "use strict";
  const SUPPORTED_YEARS = [2026];

  function rothLimit(magi, base, start, end, otherIra) {
    otherIra = otherIra || 0;
    let reduced;
    if (magi >= end) reduced = 0;
    else if (magi <= start) reduced = base;
    else {
      // Integer math so this matches room.py exactly.
      const span = end - start, over = Math.trunc(magi) - start;
      const ratioMilli = Math.floor((2 * over * 1000 + span) / (2 * span)); // line 5, 3 places, half up
      reduced = Math.ceil((base * (1000 - ratioMilli)) / 10000) * 10;         // lines 7-8, up to the next $10
      if (reduced > 0 && reduced < 200) reduced = 200;
    }
    return Math.max(0, Math.min(reduced, base - otherIra));                   // lines 10-11
  }

  function rothRange(facts, year, status, lived) {
    const r = facts.income_phase_outs.roth_ira_contribution;
    if (status === "married_joint" || status === "qualifying_surviving_spouse") return r.married_joint_or_qualifying_surviving_spouse[year];
    if (status === "married_separate" && lived) return r.married_separate_lived_with_spouse[year];
    return r.single_hoh_mfs_not_lived_with_spouse[year];
  }

  const fmt = n => "$" + Math.round(n).toLocaleString("en-US");

  function contributionRoom(facts, i) {
    const year = i.year || 2026, age = i.age_at_year_end, comp = i.compensation;
    const planType = i.plan_type || "none", deferred = i.plan_deferrals_so_far || 0;
    const trad = i.traditional_ira_so_far || 0, roth = i.roth_ira_so_far || 0;
    const magi = i.magi == null ? null : i.magi, status = i.filing_status || "single";
    if (!SUPPORTED_YEARS.includes(year)) throw new Error("year " + year + " isn't supported");
    if (age < 0 || comp < 0 || Math.min(deferred, trad, roth) < 0) throw new Error("amounts can't be negative");
    const L = facts.contribution_limits, S = facts.sources, lim = k => (L[k] || {})[String(year)];
    const line = (label, amount, why, src) => ({ label, amount, why, source: S[src] });
    const lines = [], warnings = [], notCovered = [
      "Spousal IRA (contributing on a spouse's compensation)",
      "Traditional IRA deductibility (you can contribute, but the deduction may be limited)",
      "Roth catch-up requirement for higher earners in workplace plans",
      "Employer contributions and the overall plan limit",
      "457(b) plans, and having more than one workplace plan",
      "Whether your plan offers catch-up contributions",
    ];
    const cu50 = age >= 50;

    if (planType === "401k") {
      const base = lim("401k_403b_457_tsp_elective_deferral");
      let cu, cuWhy;
      if (age >= 60 && age <= 63) { cu = lim("401k_catch_up_60_to_63"); cuWhy = "age 60-63 catch-up"; }
      else if (cu50) { cu = lim("401k_catch_up_50_plus"); cuWhy = "age 50+ catch-up"; }
      else { cu = 0; cuWhy = "no catch-up under age 50"; }
      const cap = base + cu;
      lines.push(line("401(k) / 403(b) / TSP limit", cap, (cu ? fmt(base) + " + " + fmt(cu) + " " + cuWhy : cuWhy), "irs_2026_limits"));
      lines.push(line("401(k) room left", Math.max(0, Math.trunc(cap - deferred)), "limit minus what you've deferred so far this year", "irs_2026_limits"));
      if (deferred > cap) warnings.push("You've deferred " + fmt(deferred - cap) + " over the limit. Ask your plan to return the excess.");
    } else if (planType === "simple") {
      const base = lim("simple_limit"), cu = cu50 ? lim("simple_catch_up_50_plus") : 0, cap = base + cu;
      lines.push(line("SIMPLE IRA limit", cap, cu ? fmt(base) + " + " + fmt(cu) + " catch-up" : fmt(base), "irs_2026_limits"));
      lines.push(line("SIMPLE IRA room left", Math.max(0, Math.trunc(cap - deferred)), "limit minus what you've deferred so far this year", "irs_2026_limits"));
      notCovered.push("SIMPLE higher limits for some employers, and the SIMPLE age 60-63 catch-up");
    }

    const iraDollar = lim(cu50 ? "ira_limit_50_plus_total" : "ira_limit");
    const iraBase = Math.trunc(Math.min(iraDollar, comp)), used = trad + roth;
    let why = cu50 ? "age 50+ limit, including the catch-up" : "standard limit";
    if (comp < iraDollar) why += ", capped at your earned income of " + fmt(comp);
    lines.push(line("IRA limit (traditional + Roth combined)", iraBase, why, "irs_ira_limits"));
    lines.push(line("Traditional IRA room left", Math.max(0, Math.trunc(iraBase - used)), "combined limit minus all IRA contributions so far", "irs_ira_limits"));
    if (used > iraBase) {
      const ex = facts.excess_ira_contribution;
      warnings.push("Your IRA contributions are " + fmt(used - iraBase) + " over the limit. A " + ex.excise_pct_per_year.value +
        "% tax applies each year it stays; to avoid it, " + ex.avoid_by.value + ".");
    }

    if (magi === null) {
      lines.push(line("Roth IRA room left", null, "enter your modified AGI to check the Roth income limit", "irs_2026_limits"));
    } else {
      const [start, end] = rothRange(facts, year, status, !!i.lived_with_spouse);
      const cap = rothLimit(magi, iraBase, start, end, Math.trunc(trad));
      let rwhy;
      if (magi >= end) rwhy = "modified AGI is at or above " + fmt(end) + ", so no Roth contribution is allowed";
      else if (magi > start) rwhy = "reduced: modified AGI is in the " + fmt(start) + "-" + fmt(end) + " phase-out (IRS Pub 590-A Worksheet 2-2)";
      else rwhy = "full amount: modified AGI is below " + fmt(start);
      lines.push(line("Roth IRA room left", Math.max(0, Math.min(cap - Math.trunc(roth), iraBase - Math.trunc(used))), rwhy,
        magi <= start || magi >= end ? "irs_2026_limits" : "irs_p590a"));
    }

    const notes = ["IRA contributions for " + year + " can be made until " + L.ira_contribution_deadline.value + " (IRS Pub 590-A)."];
    if (age >= facts.rmd.start_age.value) notes.push("At " + age + ", required minimum distributions apply to traditional IRAs and workplace plans. The first is due " + facts.rmd.first_rmd_deadline.value + ".");
    return { year, lines, warnings, notes, not_covered: notCovered, facts_verified_on: facts._verified_on,
      disclaimer: "General IRS rules, not tax or financial advice." };
  }

  const api = { contributionRoom, rothLimit };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.Room = api;
})(this);
