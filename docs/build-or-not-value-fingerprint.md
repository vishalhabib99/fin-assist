# Build or not: flag figures that exactly match the wrong year or the wrong fact

**Idea.** Today a figure is judged only when the rules can tell which official figure it is about, from topic words next to it. Add one more rule, plain code with no model: when a dollar figure the rules didn't judge is *exactly* a registry value, but for a different year or a different fact (last year's limit, the single filer's amount in a joint answer, the 24% bracket top used as the QBI threshold), and the answer names that fact's topic anywhere, judge it against that fact.

**Why it might matter.** On fresh blind sets, recall has stayed near two in three: 31/46 on set 6, then 27/42 on set 7 after set 6's misses were fixed. Patching topic words fixes the set it was tuned on and not the next one. Most of set 7's misses are figures with no topic word next to them, and most of those are exact registry values: $626,350 (2025 AMT phase-out stated for 2026), $23,625 (2025 head-of-household deduction), $2,050 (the unmarried age-65 add-on in a joint answer), $403,550 (the joint 24% bracket top given as the QBI threshold). A wrong figure an AI writes is often a real figure from the wrong row; that is checkable without knowing the wording.

**Claim to test.** Exact-value matching adds clearly more catches on fresh wording than it adds false flags, with no model and no added time.

## Bars, set before building (2026-10-22)

The rule is scored by what it changes: rules-only vs rules + fingerprint, on the same set.

1. **Quality, on a fresh blind set 8.** 80 answers, written by a new agent that sees only the figures table, with the same brief as set 7. Both versions are scored on set 8's first run. The fingerprint ships only if all of these hold:
   - bad figures caught rise **at least 10 points** over rules-only;
   - figures the fingerprint itself wrongly flags are **≤ 1%** of correct figures;
   - clean answers → PASS drop by **at most 1** answer.
2. **Cost and speed.** No model, no network, no paid API; median added time per answer under 5 ms.
3. **Product targets, reported, not gating.** Bad figures caught ≥ 85%, correct figures wrongly flagged ≤ 1%, clean answers → PASS ≥ 95%, answers with a bad figure → REVIEW ≥ 90%. Set 7 missed the second and third without any fingerprint (9 false flags from other causes), so these measure the whole check, not this rule.

**Early stop.** Before set 8 is written, the rule runs on sets 1–7 (all already seen, so dev data). Stop without writing set 8 if, on set 7, catches rise less than 10 points, or if, across sets 1–7, the fingerprint wrongly flags more than 1% of correct figures.

## Design limits, fixed now so results can't move them

- Dollar figures only. Percentages, ages and day counts collide too often (10%, 20%, 65) to fingerprint.
- Only distinctive values: not a multiple of $1,000. Round figures ($2,000, $100,000, $500,000) are common customer and plan amounts, so they stay with the topic-word rules.
- The fact's topic must be named somewhere in the answer: at least one of its cue groups matches the whole answer.
- The existing skips still apply: customer amounts, company-plan figures, running totals and arithmetic are not judged.
- A figure that is right for the year the sentence means, for any fact it matches, passes. A fact with no value for that year is not judged (it may not be published yet).
- Sets 1–7 are dev data. Set 8 is not written until the rule is frozen and committed.
- Cost to Vishal: no model. Writing set 8 uses Claude Pro usage (one writer agent, the size of set 7's).

## Evidence

**Early stop: not triggered, on the third version.** Sets 1–7, dev data, 2026-10-22. Branch [`value-fingerprint`](https://github.com/vishalhabib99/fin-assist/tree/value-fingerprint). Three versions were tried, all inside the design limits above; all three are reported:

| Version | Set 7 caught (rules only: 27/42) | Fingerprint's own false flags, sets 1–7 | Clean PASS lost |
|---|---|---|---|
| 1. Another year's value, or a sibling fact's value for the same year | 34/42 (+17 pts) | 11 / 612 (1.8%): fails | 4 |
| 2. Only an earlier year's value (stale), skipping "from $X to $Y" and "$X → $Y" | 31/42 (+9.5 pts): fails | 0 / 612 | 0 |
| 3. Version 2 plus a later year's value (wrong year), skipping "$X more / left" | **32/42 (+11.9 pts)** | **0 / 612** | **0** |

Version 1's sibling rule misread whenever the topic words named an incomplete set of facts (the age-65 add-on in a head-of-household answer, the QBI phase-in end read as the threshold), so it was dropped. Version 3 is frozen for set 8. It was tuned until it cleared the early-stop bar on dev data, so the dev numbers flatter it; only set 8 counts.

## Decision

Pending.
