# Build or not: a demo agent gated by fin-doctor

**Idea.** An education-only retirement and tax Q&A agent (no personalized advice) that runs every draft through fin-doctor (`check_numbers`, then `check_answer`) before replying: stale figures corrected or sent to REVIEW, advice-like wording sent to REVIEW. Shipped as a copyable integration example and a hosted demo.

**Why it might matter.** fin-doctor has no outside users yet. A working agent shows the product end to end and gives finance AI teams a pattern to copy.

## Bars, set before looking (2026-10-17)

1. **Integration examples drive adoption for tools like this.** Of 8 comparable open-source guardrail and eval tools, at least 5 ship runnable example agents or integration examples, AND at least 3 show users engaging with those examples (issues, discussions or PRs about them). Fewer → don't build.
2. **The demo would be copyable by the people fin-doctor is for.** Of 6 open-source finance AI agents found in the fin-doctor demand check, at least 3 have a single place where a draft answer passes before it reaches the user, so an example could show a ~10-line hook. Fewer → don't build.
3. **Not already done.** If an open-source finance Q&A agent with a figure-verification gate already exists and is maintained → don't build; link to it instead.

Decision rule: build only if bars 1 and 2 pass and bar 3 does not trigger.

## Evidence

**Bar 2: pass (4 of 6 hookable; bar was 3).** Code read, nothing run (2026-10-17):

| Repo | Stack | Where a check goes | Streaming | Verdict |
|---|---|---|---|---|
| virattt/dexter (27.7K★) | TypeScript, LangChain | `src/agent/agent.ts` `handleDirectResponse`, before the `done` event | Answer is fully accumulated first | Hookable, ~5 lines |
| we-promise/sure (10.6K★) | Rails, Turbo | `assistant_message.rb` `append_text!` (both assistant paths) | Chunks broadcast as they arrive: buffer in `Builtin#respond_to`, or check after and correct | Hookable, needs buffering |
| calderbuild/WeFinance | Python, Streamlit | `chat_manager.py` `generate_response` (4 branches, one function) | Placeholder redrawn per chunk; can overwrite after the check | Hookable; a second app path needs its own hook |
| badhope/xiaoman | FastAPI, LangGraph | `/api/ask` handler, before the `final` event | Tokens stream, but the UI replaces them with `final.answer` | Hookable (check-after corrects the screen) |
| googlarz/finance-assistant | Claude Code skill | None: Claude Code writes the answer | n/a | Not hookable |
| calef/us-federal-tax-assistant-skill | Claude Code skill | None | n/a | Not hookable |

Design implication: the demo must show the streaming case (buffer, or check after and correct), since 3 of the 4 hookable agents stream.

**Bar 3: not triggered.** No maintained open-source finance Q&A agent with a figure-verification gate against a sourced table was found. Closest: FinGuard-RAG (0★, checks numbers against retrieved source text, not an agent), money-track (1★, checks against the user's own data), NeMo Guardrails and Guardrails AI (generic fact-checking, no finance figure-table demo). GitHub search was rate-limited partway, so vendor org searches are incomplete.

**Bar 1:** pending.

## Decision

(filled in after the checks)
