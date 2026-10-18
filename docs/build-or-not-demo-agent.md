# Build or not: a demo agent gated by fin-doctor

**Idea.** An education-only retirement and tax Q&A agent (no personalized advice) that runs every draft through fin-doctor (`check_numbers`, then `check_answer`) before replying: stale figures corrected or sent to REVIEW, advice-like wording sent to REVIEW. Shipped as a copyable integration example and a hosted demo.

**Why it might matter.** fin-doctor has no outside users yet. A working agent shows the product end to end and gives finance AI teams a pattern to copy.

## Bars, set before looking (2026-10-17)

1. **Integration examples drive adoption for tools like this.** Of 8 comparable open-source guardrail and eval tools, at least 5 ship runnable example agents or integration examples, AND at least 3 show users engaging with those examples (issues, discussions or PRs about them). Fewer → don't build.
2. **The demo would be copyable by the people fin-doctor is for.** Of 6 open-source finance AI agents found in the fin-doctor demand check, at least 3 have a single place where a draft answer passes before it reaches the user, so an example could show a ~10-line hook. Fewer → don't build.
3. **Not already done.** If an open-source finance Q&A agent with a figure-verification gate already exists and is maintained → don't build; link to it instead.

Decision rule: build only if bars 1 and 2 pass and bar 3 does not trigger.

## Evidence

(filled in after the checks)

## Decision

(filled in after the checks)
