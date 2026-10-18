# Gate your agent with fin-doctor

One call before your agent's answer reaches a customer:

```python
from fin_doctor.gate import gate

verdict = gate(question, draft, year=2026)
reply = verdict.text          # send this, not the draft
log(verdict.outcome, verdict.fixes, verdict.reasons)
```

| `verdict.outcome` | What happened | `verdict.text` |
|---|---|---|
| `send` | No problems found | The draft, unchanged |
| `fixed` | Only stale or early figures, each with one known right value | The draft with those figures replaced; each fix is in `verdict.fixes` with the old value, the year it belonged to and the source |
| `review` | A wrong figure, an unpublished year, advice or promissory wording, or text aimed at the checker | A holding message; send the draft to a person with `verdict.reasons` |

## Run the examples

```bash
pip install -e .                                  # from a clone of this repo
python examples/plain_agent.py                    # canned drafts: no model, no API key, no cost
python examples/plain_agent.py --ollama llama3.2 "What's the HSA limit this year?"   # free local model
python examples/streaming_agent.py hold           # streaming: buffer, check, then show
python examples/streaming_agent.py correct        # streaming: show live, then replace if needed
pip install langchain-core && python examples/langchain_agent.py
```

What `plain_agent.py` prints on the canned drafts:

```text
Q: How much can I put in my 401(k) this year?
   [FIXED]
   fixed:   $23,500 -> $24,500 (2025 figure; https://www.irs.gov/newsroom/...)
   sent:    For 2026 you can defer up to $24,500 into your 401(k), plus an $8,000 catch-up if you're 50 or older.

Q: When do RMDs start?
   [REVIEW]
   held:    age 72: wrong
   sent:    Thanks for your question. A specialist will review this answer and follow up shortly.
```

## Where the gate goes in your agent

Put it at the one place where the finished answer passes before the user sees it:

- **Returned all at once** (most agent loops): call `gate()` before you return or render it.
- **Streamed token by token**: either hold the tokens and show the gated text (`hold` in `streaming_agent.py`, the safe default for money answers), or show them live and replace the message when the check finishes (`correct`, which needs a UI that can replace a message in place).
- **LangChain**: make it the last step of the chain (`langchain_agent.py`).

The demo agent's system prompt asks for education only. The gate doesn't trust that: advice-like and promissory wording still goes to `review`. fin-doctor is a checker, not an advisor, and none of this is financial or tax advice.
