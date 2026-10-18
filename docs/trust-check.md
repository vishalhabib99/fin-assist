# mcp-trust-check result

Run locally on 2026-09-26 (v0.2.0, 3 tools, commit bb9bc8c) against a clean `git archive` of the repo (what CI checks out), with the server started over stdio. Same checks as the [mcp-trust-check](https://github.com/vishalhabib99/mcp-trust-check) GitHub Action, which also runs in this repo's CI.

## mcp-trust-check — SHIP (HIGH confidence) · combined score: 100% (A)

### Release decision: ✅ SHIP

No rule fired.

**Confidence: HIGH** · needs human review: no
- mcp-fuzz called 3 of 3 tools (100%).

> Worth a manual look, one call each: large responses from get_facts (6,748 chars).

### mcp-doctor (static) — 100% (A)
```
mcp-doctor report
Quality:  100%  Grade: A  (3 tool(s) found)
Security: 100%  Grade: A

  [OK] check_answer (src/fin_doctor/server.py:16)
  [OK] get_facts (src/fin_doctor/server.py:38)
  [OK] contribution_room (src/fin_doctor/server.py:52)


```

### mcp-fuzz (runtime crash resilience) — 100.0% (A)
```
mcp-fuzz: fin-doctor

Crash resilience: 100% (A) — 0 crash(es), 0 timeout(s) across 15 bad-input calls
Tested 3 tool(s), skipped 0 (not read-only)
Latency: 100% (A) — 0 tool(s) flagged slow out of 3 checked (server median 1ms; single real call per tool, not a load test — see README)
Response size: 67% (D) — 1 tool(s) flagged bloated out of 3 checked (server median 1537 chars; single real call per tool, not representative of every possible input — see README)
Estimated token cost: ~2,120 tokens total across 3 tool(s) (~707 avg/call) — one call per tool, ~4 chars/token rule of thumb, not a real tokenizer — see README

  [ok] check_answer
  [WARN] get_facts — bloated
      bloated — 4.4x this server's median (1537 chars)
  [ok] contribution_room

```

### mcp-reality-check (runtime output fidelity) — 100.0% (A)
```
mcp-reality-check: fin-doctor

Response sanity: 100% (A) — 0 flagged of 3 checkable response(s)
Tested 3 tool(s), skipped 0 (not read-only)

  [ok]  check_answer
  [ok]  get_facts
  [ok]  contribution_room

```
