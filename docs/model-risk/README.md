# Model risk pack

How fin-doctor would be governed if a regulated financial firm deployed it. It's written the way a model risk function would review it, and it applies the April 2026 rules.

| Document | What it answers |
|---|---|
| [Inventory](inventory.md) | What the components are, which framework governs each one, and how material each one is |
| [Model card](model-card.md) | What it's for and not for, how it performs, and its limits |
| [Validation report](validation-report.md) | Is it sound? The conclusion, 11 findings with severities, and the generative AI risk mapping |
| [Monitoring plan](monitoring-plan.md) | Metrics, thresholds, triggers, scheduled reviews and change control |

## The key point: current guidance excludes the generative parts

On **April 17, 2026**, the Federal Reserve, OCC and FDIC replaced SR 11-7 with **[SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm)** (OCC [Bulletin 2026-13](https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html)). The new guidance puts **generative and agentic AI out of scope**, and the agencies say a request for information on AI is coming. It also says firms should still use their own risk practices to set controls for what isn't covered.

This system is a hybrid, so the pack governs each part under the framework that fits it:

- **Deterministic components** (pattern rules, the calculator, the facts table) follow SR 26-2's principles: materiality, effective challenge, conceptual soundness, outcomes analysis, ongoing monitoring and inventory.
- **Generative components** (the two LLM judges) are governed under the **[NIST AI RMF Generative AI Profile (AI 600-1)](https://doi.org/10.6028/NIST.AI.600-1)**, alongside FINRA's position ([Regulatory Notice 24-09](https://www.finra.org/rules-guidance/notices/24-09)) that its rules, including Rule 3110 on supervision and Rule 2210 on communications, apply to generative AI just as they do to any other tool.

SR 26-2 applies to banking organizations. Broker-dealers and asset managers face FINRA and SEC expectations instead, but it's the reference point most model risk teams use.

## Results

**Verdict: approved for shadow mode only.** The design is sound, and every blocking gate passed on synthetic data. Customer-facing SEND is blocked by two High findings:

1. **No independent validation.** The builder also wrote and ran the validation.
2. **No real-traffic evidence.** All test cases are synthetic.

**Closed since:** F-11, prompt injection. Two red-team sets, [set up the same way as the other evals](validation-report.md#prompt-injection-f-11): on the fresh set, 0 of 12 injected defects and 0 of 4 injections got through, in all 3 runs. The regex part of the defense caught none of that set, so the judges carry it. F-12 has since closed for disguised characters (zero-width, soft hyphens, fullwidth, look-alike letters); other languages, base64 and similar stay judge-only.

**Closed while writing this pack:** F-10. The installed package had been missing its facts file. A new CI job installs the built package the way users do, and I confirmed it fails on the old bug.

This isn't legal or compliance advice. It's a worked example of the documents a model risk function expects to see.
