# PRD: fin-doctor

**Status:** v0.2 (2026-09-26). v0.2 changed the design after blind evals; see §1 "Why an agent".
**Author:** Vishal Habib
**Template:** [agentic-product-playbook / agent-prd](https://github.com/vishalhabib99/agentic-product-playbook/blob/main/templates/agent-prd.md)

A pre-send checker for AI-drafted answers to retirement-account questions. It sits between a customer-service AI assistant and the customer, and it decides whether each draft answer can go out or must go to a human reviewer.

It is a checker, not an advisor. It never writes answers and never gives financial advice.

---

## 1. Problem and user

- **User:** The product owner of an AI customer-service assistant at a retirement-plan provider, and the compliance reviewer who signs off on what that assistant says.
- **Job to be done:** "Let the assistant answer routine retirement questions without me reading every answer, while making sure nothing wrong, non-compliant, or advice-like reaches a customer."
- **Today:** Either every AI answer goes through human review (safe, slow, and it cancels out the assistant's value), or answers go out with a generic LLM guardrail that isn't tuned to retirement rules and can't show *why* it passed something.
- **Why an agent:** v0.1 said wrong facts could be caught by plain code alone, with a model only for the advice boundary. **Blind evals proved that wrong:** pattern rules marked 5 of 15 planted wrong facts SEND, because many wrong claims aren't numbers ("yes, that's exempt", "due by December 31", "up to two a year"). v0.2 keeps the code layer as a fast first pass and adds a model **fact judge** that checks every claim against the same sourced facts table, never against its own memory. A pure rules engine misses meaning; a pure LLM judge without the table can't be trusted on numbers. Each layer covers the other's gap.

## 2. Scope

| The checker WILL | The checker WILL NOT (even if asked) |
|---|---|
| Flag factual errors about contribution limits, catch-up contributions, RMD ages, early-withdrawal penalties and exceptions, rollover timing | Rewrite or "fix" the answer. It flags; a human or the assistant revises |
| Flag answers that cross from general education into a personalized recommendation | Give its own view on what the customer should do |
| Flag promissory or misleading language ("guaranteed returns", "you can't lose") and missing required framing | Judge anything outside retirement accounts (taxes in general, insurance, estate planning). Out of scope → routed to a human |
| Cite the source for every fact flag (IRS publication, rule text) | See or store real customer data. Eval data is synthetic |
| Return one decision per answer: **SEND** / **REVIEW** | Send anything to a customer itself |

## 3. Autonomy levels

| Action | Level | Why this level |
|---|---|---|
| Mark an answer **SEND** | **Acts alone** | Only when all three checks pass with no uncertainty. Every SEND is logged with its check results |
| Mark an answer **REVIEW** | **Acts alone** | Holding an answer is always safe; the cost is reviewer time, not customer harm |
| Suggest a correction for a fact flag | **Proposes, human confirms** | The reviewer sees the sourced correct value and decides |
| Anything the checker is unsure about | **Hands off to a human** | Uncertainty defaults to REVIEW, never to SEND |

## 4. Top-harm error

- **The single most harmful thing:** marking SEND on an answer that has a wrong number or a personalized recommendation in it.
- **Who gets hurt, and how badly:** The customer acts on it. For example, excess IRA contributions are taxed at 6% for each year they stay in the IRA ([IRS](https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-ira-contribution-limits)), and an RMD not taken in full can be hit with a 25% excise tax on the shortfall, 10% if corrected within two years ([IRS RMD FAQs](https://www.irs.gov/retirement-plans/retirement-plan-and-ira-required-minimum-distributions-faqs)). The provider takes on regulatory exposure for advice it never meant to give.
- **Maximum acceptable rate:** 0 missed wrong-fact cases in the eval set (these are deterministic, so anything above 0 is a bug). For the advice boundary, recall ≥ 95% on the eval set, with every miss written up.
- **How it's prevented (not just detected):**
  - Numbers are never judged by a model. Any number in the answer that the facts table covers is checked by code.
  - A number the checker can't match to a fact it knows (for example, a limit for a year not in the table) is REVIEW, not SEND.
  - The facts table is versioned by tax year, and every entry cites its source.

## 5. Handoff to a human

- **Triggers:** any flag, any out-of-scope topic, any unrecognized number, any low-confidence advice-boundary call.
- **What the human receives:** the draft answer, the customer's question, each flag with its type, the exact span flagged, the source, and a suggested correction where there is one.
- **Is the review itself working:** known-answer checks are mixed into the queue, including bad answers shown with no flag, and each reviewer is scored on them (`review/`). Added 2026-09-26 after a [build-or-not check](docs/build-or-not-human-review.md).
- **The user never has to repeat themselves:** Yes. The customer never sees the checker. The reviewer works from the original question.

## 6. Success metrics

| Metric | Definition | Target | Guardrail it must not break |
|---|---|---|---|
| Wrong-fact recall | Planted fact errors caught / planted fact errors | 100% | — |
| Advice-boundary recall | Planted recommendations caught / planted | ≥ 95% | — |
| Disclosure recall | Planted promissory or missing-framing errors caught / planted | ≥ 95% | — |
| False-REVIEW rate | Clean answers sent to REVIEW / clean answers | ≤ 20% at v1 | This is the reviewer-burden metric. If it's too high, the assistant is no faster than human review and the product fails even though it's "safe" |
| Explainability | Flags with a cited source or rule / all flags | 100% | — |

## 7. Evals and launch gates

- **Eval set (v1):** about 40 synthetic question + draft-answer pairs. Half are clean. Half have one planted error, split across the three flag types. A small number are out of scope, to test routing.
- **Thresholds above are set before the first run** and won't be moved to fit the results.
- **Release gate:** the MCP server must get **SHIP** from [mcp-trust-check](https://github.com/vishalhabib99/mcp-trust-check) before v1 is published. Whatever decision it gives gets published, including FIX-FIRST or BLOCK.
- Full plan: `EVAL_PLAN.md` (next step, written with `/eval-plan`).

## 8. Rollout (for a real deployment; this repo is a reference build)

- **Stages:** shadow mode (the checker runs, a human still reviews everything, and the two are compared) → SEND allowed for one topic (contribution limits) → all in-scope topics.
- **Kill switch:** one config flag that turns every decision into REVIEW. The product owner or compliance can flip it.
- **Rollback trigger:** any SEND that a human reviewer later finds had a wrong fact, or advice-boundary recall in shadow mode below 95% over a week.

**Shadow-mode exit rule (set before shadow mode starts).** Bar: answers with a wrong fact get marked SEND less than 1% of the time, at 95% confidence (one-sided exact binomial). A miss is an answer the checker marked SEND that the reviewer found had a wrong fact. Each run uses one fixed checker version. The run exits when the number of reviewed cases reaches the count for the misses so far:

| Misses so far | Exit at this many reviewed cases |
|---|---|
| 0 | 381 |
| 1 | 571 |
| 2 | 738 |
| 3 | 894 |
| 4 or more | The run fails. Fix the checker and start a new run |

- **Why not stop at the first clean count:** taken alone, 0 misses in 299 meets the bar. But checking at each row in turn gives the checker four chances to pass, and a checker whose true rate is exactly 1% would then exit about 11% of the time instead of 5%. The counts above are set so the whole schedule, all four chances together, stays at 5% (exact, summed over every path a run can take). The price is 82 more cases on a clean run.
- **A miss doesn't restart the count.** If a miss leads to a change in the checker, that's a new version and a new run starting from 0, and the stopped run stays in the report with its count and its misses. Restarting would keep only the runs that happened to finish clean.
- **The result covers only what the run sampled**, which is live traffic. Blind-set and red-team results are bounds on other populations and are reported next to it, not merged into it.
- The continuation rule came out of [a reader's review](https://dev.to/arhancanli/comment/3g81b) of the "0 of N" write-up.

## 9. Open risks

| Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|
| Facts table goes stale when limits change for a new tax year | High (every year) | High | Product owner | Entries are keyed by tax year; an unknown year → REVIEW. Annual update checklist |
| Advice-boundary judgment is inconsistent between runs | Medium | High | Builder | Run each case several times and report variance; disagreement → REVIEW |
| Synthetic eval set is easier than real traffic | High | Medium | Builder | Say so in the README. Include adversarial phrasings (hedged advice, "most people in your situation…") |
| False-REVIEW rate too high to be useful | Medium | High | Product owner | Tracked as a guardrail metric, not hidden |
| Reader takes the repo as financial advice | Low | Medium | Author | Clear README disclaimer; the checker never produces advice |

## Non-goals

- Not a product of, or based on the internal practices of, any real financial firm. Public rules and IRS publications only.
- Not a general-purpose LLM guardrail.
- No hosted service. It runs locally as an MCP server plus a Claude Code skill, with no paid API calls.

## Sources the facts table and rules will cite

- IRS Publication 590-A (IRA contributions) and 590-B (IRA distributions, RMDs)
- IRS annual contribution-limit announcements for 401(k)/403(b)/IRA
- [FINRA Rule 2210](https://www.finra.org/rules-guidance/rulebooks/finra-rules/2210)(d)(1): communications must be fair and balanced; no "false, exaggerated, unwarranted, promissory or misleading" statements; no predicting or projecting performance
- SEC Regulation Best Interest (context for where "recommendation" begins)

Every number goes into the facts table only after it has been checked against the current IRS source. None are in this PRD on purpose.
