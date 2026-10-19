## Build or not: a measured human-review layer for fin-assist

*Method: [/build-or-not](https://github.com/vishalhabib99/ai-pm-skills). Sections 1–3 were written and saved before any example was checked.*

**Proposal:** When the checker says REVIEW, give the reviewer a screen with each flag and its source, and **measure whether the review itself works**: whether reviewers catch errors or just approve.

**Narrowed to one checkable claim:** Widely used tools for human review of AI/LLM output do not document any built-in way to measure whether reviewers catch errors: no known-answer ("gold") items, no reviewer-accuracy metric, no agreement between reviewers.

**Precondition (the problem is real):** at least 2 published studies or official sources show people reviewing AI output miss its errors (automation bias). If fewer than 2, the decision is "don't build" regardless of the gap.

**Sample (chosen before checking):** 6 real, publicly documented human-review features, one or two per category:
1. Amazon Augmented AI (A2I), cloud platform
2. Label Studio, open-source labeling and review
3. LangSmith annotation queues, LLM observability
4. Langfuse annotation queues, open-source LLM observability
5. Arize Phoenix human annotations, open-source LLM observability
6. Braintrust human review, LLM eval platform

Selection rule: the best-known human-review features in each category that an AI team would actually pick up, named before any docs were read.

**Bar (set before checking):**
- **Hit** = the tool's official docs show **no** built-in reviewer-quality measurement (gold items, reviewer accuracy, or inter-reviewer agreement) for its review workflow. A feature that exists only in a paid tier still counts as present (not a hit).
- **Build** if the precondition holds **and** ≥ 4 of 6 are hits (the gap is common).
- **Narrow** if 2–3 are hits: the gap is partly filled, so look for what's still missing (for example, domain-sourced flags or catching rubber-stamping specifically).
- **Don't build** the measurement part if ≤ 1 is a hit: existing tools already cover it.
- **What would change my mind:** tools with gold items or reviewer-accuracy features for LLM review specifically.

---

## Round 1 results (checked 2026-09-26)

**Precondition: met.** Three independent sources:
- EU AI Act [Art. 14(4)(b)](https://artificialintelligenceact.eu/article/14/): people overseeing high-risk AI must "remain aware of the possible tendency of automatically relying or over-relying on the output… (automation bias)".
- Dell'Acqua et al. 2023 ([paper](https://mitsloan.mit.edu/sites/default/files/2023-10/SSRN-id4573321.pdf)), 758 BCG consultants: on a task outside the frontier, "consultants using AI were 19 percentage points less likely to produce" correct solutions (control ~84.5% correct vs 60–70% with AI).
- Goddard, Roudsari & Wyatt, [JAMIA 2012](https://academic.oup.com/jamia/article-abstract/19/1/121/732254), systematic review of 74 studies: users often fail "to recognize the new errors that CDSS can introduce."

| # | Tool | Result | Evidence |
|---|---|---|---|
| 1 | Amazon A2I | **N/A** | [Docs](https://docs.aws.amazon.com/sagemaker/latest/dg/a2i-create-flow-definition.html): "no longer open to new customers… we do not plan to introduce new features." A team starting today can't adopt it. Not replaced. |
| 2 | Label Studio | Miss | [Docs](https://docs.humansignal.com/guide/ground_truths): Enterprise "compares annotations from annotators… against the ground truth annotations… to calculate an accuracy score". Enterprise-only, which the bar counts as present. |
| 3 | LangSmith annotation queues | **Hit** | [Docs](https://docs.langchain.com/langsmith/annotation-queues): multiple reviewers per run, but no gold items, reviewer accuracy, or agreement metric. |
| 4 | Langfuse annotation queues | **Hit** | [Docs](https://langfuse.com/docs/evaluation/evaluation-methods/annotation-queues): measures human-vs-LLM-judge agreement (to calibrate the judge), not reviewer quality. |
| 5 | Arize Phoenix annotations | **Hit** | [Docs](https://arize.com/docs/phoenix/tracing/concepts-tracing/annotations-concepts): none documented. |
| 6 | Braintrust human review | Miss | [Docs](https://www.braintrust.dev/docs/annotate/human-review/multiple-reviewers): per span, shows how many reviews match vs diverge "to gauge consensus". A basic agreement signal, so counted as present (the conservative call). |

**Result:** 3 hits of 5 valid examples (1 N/A). Falls in the pre-set 2–3 band.
**Decision: Narrow and re-check** (round 1 of at most 2).
**What's partly filled:** general labeling tools (Label Studio, paid) score reviewers against gold answers; Braintrust shows per-item consensus. **What looks open:** the LLM-observability review queues AI teams actually use for production output don't check whether reviewers catch errors.

---

## Round 2 (bar and new sample saved before checking)

**Narrowed claim:** Review tools built for *LLM production output* don't document a way to test reviewers with known answers: seeding items whose correct verdict is already known and scoring reviewers on them. That's the direct measure of whether a reviewer catches an AI error or rubber-stamps it.

**New sample (none from round 1):** 5 LLM-output review features: W&B Weave (human feedback), Comet Opik (annotation queues), MLflow / Databricks (review app / labeling sessions), Argilla (Hugging Face), Datadog LLM Observability (annotation queues). Selection rule: the other well-known LLM-eval and LLM-observability products with a human-review feature, named before reading their docs.

**Bar:** hit = official docs show no known-answer/gold reviewer scoring for LLM-output review. Agreement-only features still count as a hit here, since agreement between two reviewers who both rubber-stamp says nothing about catching errors. **Build if ≥ 3 of 5 hits. Don't build if ≤ 2.** No further narrowing after this round.

## Round 2 results (checked 2026-09-26)

| # | Tool | Result | Evidence |
|---|---|---|---|
| 1 | W&B Weave | **Hit** | [Docs](https://docs.wandb.ai/weave/guides/tracking/feedback): human-annotation scorers and queues; nothing on scoring reviewers against known answers or agreement. |
| 2 | Comet Opik | **Hit** | [Docs](https://www.comet.com/docs/opik/evaluation/annotation_queues): multiple reviewers can score the same trace; no reviewer-quality measurement. |
| 3 | MLflow / Databricks | **Hit** | [Docs](https://docs.databricks.com/aws/en/mlflow3/genai/human-feedback/concepts/labeling-sessions): labeling sessions and review app; nothing on reviewer accuracy or agreement. |
| 4 | Datadog LLM Observability | **Hit** | [Docs](https://docs.datadoghq.com/llm_observability/evaluations/annotation_queues/): "the value for each label is aggregated across them by consensus". Consensus only, which the bar counts as a hit. |
| 5 | Argilla | Miss | [v1 docs](https://docs.v1.argilla.io/en/latest/reference/python/python_annotation_metrics.html): a metric mode "where suggestions are the ground truths and the responses are compared against them", per annotator. These are legacy v1 docs, and I couldn't confirm it in 2.x. Counted as present, the conservative call. |

**Result:** 4 of 5 hits. Clears the pre-set bar (≥ 3).
**Decision: Build**, narrowed.
**Why, in one sentence:** people who review AI output measurably miss its errors, and 7 of the 10 review tools that could be checked across both rounds give no way to test whether reviewers catch them. The general labeling tools that do (Label Studio Enterprise, Argilla v1) aren't where production LLM answers get reviewed.

**Smallest version to build:** a review queue for fin-assist that mixes in **known-answer items**, cases whose correct verdict is already known, drawn from the existing 83 labeled eval cases. It reports, per reviewer:
- the catch rate on known-bad answers (rubber-stamping shows up here),
- the false-reject rate on known-good answers,
- time per item.

**First test cases:** the 83 cases in `evals/`, already labeled.
**Honest limit:** the tool can be built and tested here, but whether it changes reviewer behavior needs real reviewers. The plan is 2–3 people from the outreach, with results reported as-is.
**What would reopen this:** evidence that LangSmith, Langfuse, Phoenix, Weave, Opik, MLflow or Datadog ship known-answer reviewer scoring, or that teams already run this in-house as standard practice.
