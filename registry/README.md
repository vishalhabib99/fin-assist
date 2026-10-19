# Verified financial facts registry

Current-year figures an AI agent is likely to quote, each tied to the year it applies to and the primary source it was read from. One file per domain:

| File | Covers | Years |
|---|---|---|
| `retirement.json` | 401(k)/403(b)/457/TSP, IRA, SIMPLE limits; RMD age; early-distribution and rollover rules | 2025–2026 (IRS hasn't published 2027 yet) |
| `hsa.json` | HSA limits, HDHP deductibles and out-of-pocket maximums | 2025–2027 |
| `social_security.json` | COLA, taxable maximum, payroll tax rates, earnings test, max benefit, SGA, SSI payment standard and resource limits | 2025–2027 |
| `medicare.json` | Medicare Part B standard premium and deductible (2024–2026), where IRMAA starts for single and joint returns (2025–2026) | 2024–2026 |
| `tax.json` | Brackets (single, joint, head of household), standard deduction (2025 as amended by the 2025 tax law), additional aged/blind deduction, long-term capital gains 0% and 15% thresholds, AMT exemption, phase-out start and 28% threshold, QBI threshold and phase-in, estate and lifetime gift exemption; gift exclusion and gift splitting (2024–2026); health FSA (2026) | 2025–2026 |

Rules:

- A value is added only after it is read on the primary IRS, SSA or CMS page; `read_on` records the date.
- `values` are keyed by year, or `"any"` for figures that don't change by year. A missing year means unknown: `lookup()` returns `None`, never last year's number.
- `retirement.json` mirrors `data/facts.json`, and a test enforces parity.
- Tax bracket thresholds are cross-checked by rebuilding the IRS's printed base-tax amounts.

Check it: `python -m fin_assist.registry`

## New year's tax figures

The IRS publishes next year's tax figures in one Rev. Proc. each fall. `scripts/revproc.py` reads it and proposes every tax, gift and health FSA figure the registry tracks:

```bash
pip install pypdf
python scripts/revproc.py rp-26-XX.pdf     # the year is read from the document
```

It prints each figure with "same as registry", "new year (was X)" or "CHANGE", rebuilds every bracket table's printed base-tax amounts, and lists anything it couldn't find. It writes nothing: copy the reviewed values into `tax.json` with the new source, then run the tests. `tests/test_revproc.py` holds it to the two Rev. Procs already in the registry (2024-40 and 2025-32): it must reproduce every figure, so a change in the IRS's layout shows up as a failing test, not a wrong number.

## New year's retirement limits

The IRS publishes next year's retirement-plan limits in one notice each fall (Notice 2025-67 for 2026). `scripts/retirement_notice.py` reads it:

```bash
python scripts/retirement_notice.py n-26-XX.pdf
```

It finds each limit by the Code section the notice cites (402(g)(1) for the 401(k) deferral, 414(v)(2)(B)(i) for the 50+ catch-up, 219(b)(5)(A) for the IRA limit, and so on), and checks each "increased from $A" against the registry's figure for the year before. Same output and rules as the tax tool. `tests/test_retirement_notice.py` holds it to Notices 2024-80 and 2025-67.

## New year's Medicare figures

CMS publishes next year's Part B premium, deductible and IRMAA table in a fact sheet each fall. Save the page and run:

```bash
python scripts/cms_partb.py 2027-medicare-parts-b-premiums-deductibles.html
```

The year is read from the premium sentence. The sheet also states last year's premium and deductible and the change between them, and both are checked: last year's figure against the registry, and this year minus last year against the stated change. `tests/test_cms_partb.py` holds it to the 2025 and 2026 sheets.
