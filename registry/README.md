# Verified financial facts registry

Current-year figures an AI agent is likely to quote, each tied to the year it applies to and the primary source it was read from. One file per domain:

| File | Covers | Years |
|---|---|---|
| `retirement.json` | 401(k)/403(b)/457/TSP, IRA, SIMPLE limits; RMD age; early-distribution and rollover rules | 2025–2026 (IRS hasn't published 2027 yet) |
| `hsa.json` | HSA limits, HDHP deductibles and out-of-pocket maximums | 2025–2027 |
| `social_security.json` | COLA, taxable maximum, payroll tax rates, earnings test, max benefit, SGA, SSI payment standard and resource limits | 2025–2027 |
| `tax.json` | 2026 brackets (single, joint, head of household), standard deduction, gift exclusion and gift splitting (2024–2026), health FSA | 2026 |

Rules:

- A value is added only after it is read on the primary IRS or SSA page; `read_on` records the date.
- `values` are keyed by year, or `"any"` for figures that don't change by year. A missing year means unknown: `lookup()` returns `None`, never last year's number.
- `retirement.json` mirrors `data/facts.json`, and a test enforces parity.
- Tax bracket thresholds are cross-checked by rebuilding the IRS's printed base-tax amounts.

Check it: `python -m fin_doctor.registry`
