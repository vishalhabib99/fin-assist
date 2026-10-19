# Model inventory

Each component is recorded separately, because each one is governed under a different framework.

**Why the split matters:** in April 2026 the U.S. banking agencies replaced SR 11-7 with [SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm) (OCC [Bulletin 2026-13](https://www.occ.gov/news-issuances/bulletins/2026/bulletin-2026-13.html)). Footnote 3 of SR 26-2 says: *"Generative AI and agentic AI models are novel and rapidly evolving. As such, they are not within the scope of this guidance."* It also says the firm's own risk management practices should still decide the controls for anything not covered. So this system is governed in two parts: the deterministic components follow SR 26-2's principles, and the generative components follow the [NIST AI RMF Generative AI Profile (NIST AI 600-1)](https://doi.org/10.6028/NIST.AI.600-1).

| ID | Component | What it does | Type | Framework | Materiality* | Owner |
|---|---|---|---|---|---|---|
| RAC-1 | Pattern rules ([`checker.py`](../../src/fin_assist/checker.py)) | First pass: numbers, rules, scope and phrasing checked against the facts table | Deterministic, rule-based | SR 26-2 principles | High | Product owner |
| RAC-2 | fact-judge ([skill](../../skills/fact-judge/SKILL.md)) | Checks every claim against the facts table, including claims that aren't numbers | **Generative (LLM)** | NIST AI 600-1 | High | Product owner |
| RAC-3 | advice-judge ([skill](../../skills/advice-judge/SKILL.md)) | Flags personal recommendations and promissory language (FINRA 2210(d)(1)) | **Generative (LLM)** | NIST AI 600-1 | High | Product owner |
| RAC-4 | Contribution room ([`room.py`](../../src/fin_assist/room.py), [`room.js`](../../docs/room/room.js)) | Computes remaining contribution room from IRS limits | Deterministic calculation | SR 26-2 principles | Medium | Product owner |
| RAC-D1 | Facts table ([`facts.json`](../../data/facts.json)) | IRS-sourced limits and rules that RAC-1, 2 and 4 depend on | Data dependency | Both | High (shared) | Product owner |
| RAC-V1 | Claude (Anthropic) | The model behind RAC-2 and RAC-3, and behind the eval case writers | Third-party model | SR 26-2 §VII (vendor) + NIST AI 600-1 | High (shared) | Vendor. Oversight: product owner |

\* Materiality is rated for a **hypothetical production deployment** at a retirement-plan provider, where answers reach customers. SR 26-2 defines materiality as exposure plus purpose. Here the purpose is regulatory: the answers are communications with the public under FINRA Rule 2210. For **this reference build**, which serves no customers, every component is immaterial.

**Aggregate risk (SR 26-2 §III):** RAC-1, 2 and 4 all depend on RAC-D1, so one wrong entry in the facts table would get past every layer at once. RAC-2, RAC-3 and the eval case writers all depend on RAC-V1, so a blind spot in that one model family can show up in both the system and its tests. See validation findings [F-3](validation-report.md#findings) and [F-9](validation-report.md#findings).
