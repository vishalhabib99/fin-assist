# Model card: fin-assist v0.2.0

## Intended use

- **Decision:** before an AI assistant's draft answer to a US retirement-account question reaches a customer, return **SEND** or **REVIEW**. Every flag cites an IRS or FINRA source.
- **Users:** the product owner of a customer-service AI assistant and the compliance reviewer who signs off on what it says ([PRD §1](../../PRD.md#1-problem-and-user)).
- **Autonomy:** it can mark SEND or REVIEW on its own. Any uncertainty defaults to REVIEW. It never writes or edits answers ([PRD §3](../../PRD.md#3-autonomy-levels)).

## Out of scope: do not use for

- Writing answers, or any personalized financial, tax or legal advice.
- Estate planning, insurance, Social Security, and state tax rules. These are routed to REVIEW as out of scope.
- Tax years missing from the facts table. Answers about those years go to REVIEW, never SEND.
- Replacing human supervision under FINRA Rule 3110. It narrows what a person has to read; it doesn't remove the person.

## Design

Three layers, and any flag from any layer means REVIEW:

1. **Pattern rules (RAC-1):** deterministic and free, and the first pass.
2. **fact-judge (RAC-2):** an LLM reads the facts table and checks every claim against it, never against its own memory.
3. **advice-judge (RAC-3):** an LLM checks the advice boundary and promissory language.

**Why the hybrid design:** blind evals showed the rules layer alone marked 5 of 15 planted wrong facts SEND, because many wrong claims aren't numbers ("yes, that's exempt"). An LLM judge without the table can't be trusted on numbers either. Each layer covers the other's gap ([PRD §1](../../PRD.md#1-problem-and-user)).

## Performance

All results are on **synthetic** cases. Thresholds were [set before the first run](../../EVAL_PLAN.md).

| Metric | Result | Gate |
|---|---|---|
| Wrong facts marked SEND (full system, 3 blind judge runs each) | **0 of 25** | 0 |
| Personal recommendations caught | 9 of 9 | ≥ 95% |
| Promissory claims caught | 6 of 6 | ≥ 95% |
| Out of scope / unknown fact / empty draft routed to REVIEW | 4/4, 2/2, 1/1 | all |
| Clean answers sent to REVIEW (reviewer burden) | 2 of 36 (5.6%) | ≤ 20% |
| Rules alone, first blind run: wrong facts marked SEND | 1 of 5 (held-out 1), 4 of 10 (held-out 2) | *(why layers 2–3 exist)* |

## Known limitations

- All 83 eval cases are synthetic. It has never been tested on real traffic ([F-2](validation-report.md#findings)).
- The judges and the case writers are all Claude, so they may share blind spots ([F-3](validation-report.md#findings)).
- The judge model version isn't recorded with eval results, so results can't be tied to a model version ([F-7](validation-report.md#findings)).
- The rules layer flags dollar amounts derived from the question (such as "$500 over") as wrong limits. That costs extra reviews but never causes a harmful SEND ([F-4](validation-report.md#findings)).
- The facts table covers 2025–2026 and needs a manual update each November ([monitoring plan](monitoring-plan.md)).

## Validation status

**Approved for shadow mode only.** SEND on customer traffic waits on findings F-1 (independent validation) and F-2 (real-traffic evidence). F-11 (prompt injection) closed 2026-09-26 for the attack types tested. See the [validation report](validation-report.md).
