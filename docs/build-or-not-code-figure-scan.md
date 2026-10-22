# Build or not: check the official figures written into code

**Idea.** The same registry that checks AI answers can check source code: a retirement or tax calculator that hard-codes IRS, SSA or Medicare figures, where last year's value stays in after the new year's figures come out. A `fin-assist scan <repo>` would list each figure it recognizes, the year the code means, and whether it matches the registry for that year, with the source.

**Why it might matter.** Checking ignidash's 2026 tax tables against the registry found a real error on 2026-10-22: the head-of-household 24% bracket ended at $201,775 (the single filer's figure) instead of $201,750 ([PR #69](https://github.com/schelskedevco/ignidash/pull/69)). Code wording doesn't vary the way answer wording does, so the recall ceiling the answer check hits (about two to three in four on fresh wording) may not apply. And it's the loop that worked for mcp-doctor: a finding, a fix PR, a maintainer's merge. One bug in one repo is an anecdote, so this test.

## Bars, set before looking (2026-10-22)

**A. The bug exists in the wild.** Of 10 repos chosen by the rule below, **at least 3** have at least one confirmed stale or wrong official figure. Confirmed means: checked by hand against the IRS, SSA or CMS source for the year the code says it means. ignidash doesn't count.

**B. A simple scanner finds them without crying wolf.** Of the hits the scanner below reports across the 10 repos, **at most 1 in 5** is a false alarm after the same hand check.

**Decision rule.** BUILD `fin-assist scan` only if A and B both pass. Otherwise don't build; the confirmed bugs still get one-off fix PRs, and this doc records the result.

## Repo selection, fixed now

- GitHub repository search, in this order: topics `retirement`, `fire`, `retirement-calculator`, `tax-calculator`, `personal-finance` with `tax`; then keyword searches `401k calculator`, `retirement calculator`, `federal income tax calculator`, `social security calculator`, `roth conversion`.
- Keep a repo if: public, not archived, pushed on or after 2026-07-01, at least 20 stars, US figures, not mine, not ignidash.
- Then it must hard-code figures: the scanner's first step finds **at least 3** literals equal to a registry dollar value (any year) with a topic word nearby. This is decided before any figure is judged right or wrong.
- Take the first 10 qualifying repos by stars, across all searches combined. The list and every repo skipped, with the reason, go in the evidence below.

## The scanner, fixed now (a throwaway prototype, not product code)

- Files: source and data files (`.py .ts .tsx .js .jsx .go .rb .java .cs .rs .json .yaml .yml .toml`), skipping tests, `node_modules`, vendored and lock files.
- Candidates: numeric literals of 100 or more (`24500`, `24_500`, `24,500`) equal to a registry dollar value for some year, with one of that fact's topic words within 5 lines.
- Year the code means: a year (2023–2030) on the same line, else the nearest one in the 5 lines above, else the latest year in the file; no year anywhere → not judged.
- Hit: the literal equals the fact's value for an earlier year than the year meant, and the registry has a different value for the year meant (stale); or it equals the value for a later year (wrong year).
- Not judged: years the registry doesn't have, and figures that match the registry for the year meant.

Cost: no model, no paid API, no writer agents. A session of searching and reading code.

## Evidence

Run 2026-10-22, by the rule and scanner above.

**Selection.** The ten fixed searches returned 25 repos (20+ stars, pushed since 2026-07-01). 13 were out before scanning: other countries' taxes (China ×2, Turkey, Spain, UK ×2, Germany ×2, India, Kazakhstan), not personal finance (forest-fire ratings, a game bot, a public-bodies dataset), and ignidash. Of the other 11, only **5 hard-code at least 3 registry figures**; 6 had 0–2 (caxete/crypto-tax-calculator, venil7/assets, moov-io/irs, googlarz/finance-assistant, binarycodes/calculators, nadimtuhin/tax-calculator). So the test ran on 5 repos, not 10, with bar A unchanged: 3 repos.

| Repo | Stars | Figures found | Scanner hits | Confirmed stale or wrong |
|---|---|---|---|---|
| mdlacasse/Owl | 89 | 207 | 67 | 0: year-keyed tables (`{2025: 23_500, 2026: 24_500}`) are current through 2026 |
| Gregable/social-security-tools | 98 | 15 | 0 | 0: wage base and quarter of coverage through 2027 |
| MikePiper/open-social-security | 75 | 5 | 2 | 0: wage base through 2026 |
| jamesmontemagno/app-fire-calculator | 49 | 64 | 0 | 0: $23,500 appears only as a demo user's editable contribution, not as a limit |
| wscott/fplan | 36 | 19 | 0 | **1**: the default maximum contribution is `19500 + 7000 * 2` (the 2020–21 401(k) limit and the 2024–25 IRA limit; 2026: $24,500 and $7,500) |

One scanner fix was made during the run, to match the spec rather than change it: test folders named like `MyFireNumber.Tests` weren't skipped; with the fix, app-fire-calculator's 13 hits (all in tests) went to 0.

**Bar A: fails.** 1 of 5 repos has a confirmed stale figure; the bar was 3.
**Bar B: fails.** 69 of 69 scanner hits were false alarms: values on a line keyed by two years (`{2025: 7_000, 2026: 7_500}`) read against the wrong one, round numbers that equal a registry value ($2,000, $10,000, $500,000) next to a topic word, state tax tables, and birth-year lists. The scanner also missed both real bugs seen so far: fplan's $19,500 predates the registry, and ignidash's was a sibling value (the single filer's bracket top in the head-of-household table), which the spec leaves out.

## Decision

**DON'T BUILD.** The maintained US calculators that hard-code figures mostly keep year-keyed tables and update them; the stale-figure bug in code is real but rare (2 found in 6 repos read, counting ignidash), and a value-matching scanner finds noise, not those bugs. Confirmed bugs get one-off fix PRs instead: ignidash [#69](https://github.com/schelskedevco/ignidash/pull/69) (sent), fplan (drafted, pending).

What would reopen it: a scanner that reads the structure of year-keyed tables and checks sibling values (filing status, coverage tier) within a table, re-run against the same bars on a fresh set of repos.
