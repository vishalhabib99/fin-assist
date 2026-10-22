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

Pending.

## Decision

Pending.
