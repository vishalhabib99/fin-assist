# Build or not: a model that matches each figure to its fact

**Idea.** Keep the registry as the only source of right values, and keep the value comparison in plain code. Replace only the pattern rules that decide *which* official figure a number is about with a small model: for each number in a draft, the model picks one registry fact (or none) and the year the sentence means. Opt-in (`check_numbers(..., llm=...)`); the rules-only check stays the default.

**Why it might matter.** Recall on fresh blind sets has been flat or falling: 38/43, 44/52, 45/55, then 31/46 (67%) on set 6, written with harder phrasing. Each round of pattern fixes covered the last set's wording and not the next one's: the set-5 fixes took set 5 to 52/55 and set 6 still came in at 67%. Set 6's misses are mostly about *which* figure a number refers to ("the payroll tax ceiling", "$15,750 is what a single filer can deduct", a SIMPLE limit in an IRA row), the part rules keep missing.

**Claim to test.** A small local model that only maps numbers to registry facts, plus the existing deterministic comparison, catches clearly more stale or wrong figures on fresh, hard phrasing than the pattern rules, without more false flags, at a cost and speed an agent builder would accept.

## Bars, set before looking (2026-10-19)

1. **Quality, on a fresh blind set 7.** 80 answers written by a new agent that sees only the figures table (labels and values, no code, no cues), with the same brief as set 6. Rules-only and rules + model are both scored on set 7's first run. The model runs at temperature 0, three times; the worst run counts. Rules + model must reach all of:
   - bad figures caught **≥ 85%**, and **at least 10 points above rules-only** on the same set;
   - correct figures wrongly flagged **≤ 1%**;
   - clean answers → PASS **≥ 95%**;
   - answers with a bad figure → REVIEW **≥ 90%**.
2. **Cost and speed.** No paid API: the default is a local model (qwen3:8b through Ollama), or the builder's own OpenAI-compatible endpoint. Median added time **≤ 3 seconds per answer** on an Apple M5 laptop, measured over set 7. With the local default, nothing in the answer leaves the machine.
3. **Not already done.** If a maintained open-source tool already uses a model to map the figures in an LLM answer to a year-versioned table of official figures, don't build; link to it or integrate it. Checked against 8 named tools: Guardrails AI hub validators, NeMo Guardrails fact-checking rails, promptfoo `financial:*` plugins, deepeval, Llama Guard, Vals TaxEval, FinGuard-RAG, and a GitHub search for figure-table checkers.
4. **Fits the people fin-assist is for.** Of the 4 finance agents the demo-agent check found hookable (dexter, sure, WeFinance, xiaoman), **at least 3** already call a chat model through something fin-assist could reuse (an OpenAI-compatible client or a LangChain chat model), so the model layer adds no new service for them. Fewer → the layer ships local-only, and the README says so.

**Decision rule.** Ship the model layer, opt-in, only if bars 1, 2 and 4 pass and bar 3 does not trigger. If any part of bar 1 fails, don't ship; publish the set-7 result and the prototype's numbers as they came out.

**Early stop.** Before writing set 7, the prototype is run on sets 1–6 (all already seen, so dev data only). If it can't reach 85% caught and ≤ 1% false flags there, stop without writing set 7, and record that as the result.

## Design limits, fixed now so results can't move them

- The model returns, for each number span, a registry fact id from the list it's given or `none`, plus the year if the sentence states or implies one. It never writes a value; every value comes from the registry.
- Customer numbers, company-plan numbers and arithmetic stay unjudged: the model is told to answer `none` for them, and the rules' existing skips still apply.
- If the model errors, times out or returns an id not in the list, that answer is checked rules-only, and the result says so.
- Sets 1–6 are dev data. Set 7 is not opened until the prototype is frozen and committed.
- Cost to Vishal: the local model is free; writing set 7 uses Claude Pro usage (one writer agent, about the size of set 6's).

## Evidence

**Bar 3: not triggered (0 of 8 hits, 2 near-misses).** Read-only research, 2026-10-19; GitHub search was not rate-limited.

| # | Tool | Verdict | Why |
|---|---|---|---|
| 1 | Guardrails AI hub | Miss | `financial_tone` is tone only; MiniCheck and "source of truth" validators compare to supplied context, not a year-keyed table |
| 2 | NeMo Guardrails | Miss | `library/factchecking` scores against retrieved chunks; no figure extraction, no versioned table |
| 3 | promptfoo `financial:*` | Miss | `financialHallucination`, `financialCalculationError`: red-team prompt generators with an LLM rubric grader |
| 4 | deepeval | Miss | Hallucination and faithfulness are LLM judges against given context; no numeric or table metric |
| 5 | Llama Guard | Miss | Safety categories ("specialized advice"); no fact checking |
| 6 | Vals TaxEval v2 | Miss | Closed benchmark, not a runtime checker |
| 7 | FinGuard-RAG | Near-miss | Blocks numbers in output that aren't in the retrieved context; checks documents, not official figures by year (0–1★) |
| 8 | GitHub search | Near-miss | openaccountants (453★) matches tax concepts to values by tax year with regex, but across its own guides, not LLM output; SecondLook grounds generation in `rules/<tax_year>.json` rather than checking after |

The category pattern: guardrail tools check "supported by the context", not "matches the official figure for year X".

**Bar 4: pass (4 of 4; bar was 3).** Code read through `gh`, nothing run, 2026-10-19:

| Agent | How it calls a model | Evidence |
|---|---|---|
| virattt/dexter (TypeScript) | LangChain.js `ChatOpenAI` with configurable `baseURL` for several providers, `ChatOllama` | `src/model/llm.ts`, `src/providers.ts` |
| we-promise/sure (Rails) | `ruby-openai` client, configurable `uri_base` and model | `app/models/provider/openai.rb` |
| calderbuild/WeFinance (Python) | OpenAI SDK with `base_url`, plus a LangChain `ChatOpenAI` | `modules/chat_manager.py`, `services/langchain_agent.py` |
| badhope/xiaoman (Python) | LiteLLM `acompletion`, configurable model and `api_base` | `backend/app/llm.py` |

Design implication: only WeFinance has a Python chat-model object to hand over. The shared piece across all four is an OpenAI-compatible endpoint (base URL, model, key), so the opt-in takes that, or any `text -> text` callable, and does not require LangChain.

**Early stop: triggered.** The prototype ran on sets 1–6 (dev data) on 2026-10-19 with qwen3:8b through Ollama on an Apple M5 laptop. Code and per-set logs: branch [`llm-add-only`](https://github.com/vishalhabib99/fin-assist/tree/llm-add-only) (`src/fin_assist/llm_match.py`, `evals/llm_dev/`). Two designs were tried:

- **Label:** the model labels every number; rules only find the numbers.
- **Add-only:** the rules judge first; the model labels only numbers the rules didn't judge.

| Sets 1–6 (dev) | Rules only (shipped) | Model labels every number | Add-only | Early-stop bar |
|---|---|---|---|---|
| Bad figures caught | 224/243 (92%) | 227/243 (93%) | **234/243 (96%)** | ≥ 85% |
| Correct figures wrongly flagged | 4/506 (0.8%) | 55/506 (10.9%) | **10/506 (2.0%)** | ≤ 1% |
| Clean answers → PASS | 166/171 (97%) | 128/171 (75%) | **137/171 (80%)** | (set 7: ≥ 95%) |
| Median seconds per answer, by set | ~0 | 3.1–8.0 | **3.0–7.3** | (set 7: ≤ 3) |

Rules-only was tuned on sets 1–5, so its numbers there flatter it. Set 6, never tuned on, is the fairer comparison: rules caught 31/46 with 4 false flags; add-only caught 41/46 with 7 false flags and passed 25 of 40 clean answers.

What the numbers say:

- **The model finds what the rules miss.** On set 6 it lifted recall from 67% to 89%: paraphrased topics ("the payroll tax ceiling"), figures before their label, swapped table rows.
- **It also labels correct figures as the wrong fact,** often enough to fail: 2% of correct figures flagged and 1 clean answer in 5 sent to a person, against a bar of 1% and 1 in 20. Letting the rules keep the final say cut false flags from 10.9% to 2.0%, not far enough.
- **It's too slow on a laptop.** An 8B model generates about 10 tokens a second here; even with a cached prompt prefix and a few tokens of output per figure, answers took 3–7 seconds at the median, up to 37.

## Decision

**DON'T BUILD (yet).** The early stop triggered on false flags (2.0% vs ≤ 1%), so set 7 was not written and no Pro usage was spent. The rules-only check stays the shipped default, and nothing from the prototype is merged.

What would reopen it, each to be re-run against the same bars on dev sets first and then a fresh set 7:

1. A model that labels more accurately at the same size: the misses were mostly near-neighbour facts (the Medicare rate for the Social Security rate, one year for another).
2. Or a faster setup, such as a smaller model or a hosted endpoint the agent already pays for (bar 4 showed all four agents have one). Speed alone wouldn't fix the false flags.
3. The add-only design is the one to start from.
