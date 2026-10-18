# RetireBench

How often do free AI chat assistants get basic US retirement-account facts wrong, and would [fin-doctor](../README.md) have caught the mistakes?

**Status:** questions and key **frozen 2026-09-26** (git tag `retirebench-v1`), before any answers were collected. Collection must finish before 2027-01-01, because "this year" questions assume 2026.

**Dry run (2026-09-26):** each key, written as a one-line answer and run through the checker's rules layer, got SEND on 28/30. The 2 REVIEWs (q08, q30) are checker false positives: the rules layer reads any dollar figure in an IRA answer as a claimed limit, so derived amounts (a $4,000 compensation cap, a $500 excess) get flagged. **Left unfixed on purpose** until collection is done: fixing it now would tune the checker on this benchmark. It will be fixed afterwards, with checker results reported both before and after the fix.

## What's here

| File | What |
|---|---|
| [`questions.jsonl`](questions.jsonl) | 30 questions: contribution limits (10), RMDs (6), early withdrawals (9), rollovers (4), excess contributions (1). Every key claim points at an IRS-sourced entry in [`../data/facts.json`](../data/facts.json). |
| [`validate.py`](validate.py) | Fails if any key claim doesn't match `facts.json`. Currently: 30 questions, 37 key claims, 0 errors. |
| [`RUBRIC.md`](RUBRIC.md) | CORRECT / INCOMPLETE / WRONG / DECLINED, plus error tags. |
| [`collect.html`](collect.html) | Offline page for collecting answers: shows the questions only, never the key. Saves in the browser and exports JSON. Rebuild with `build_collect.py`. |
| [`make_questions.py`](make_questions.py) | Source of the question set, so the key can be reviewed as code. |

**Designed to catch** the mistakes that actually hurt people: last year's limits given as this year's, rules from before SECURE 2.0, IRA rules applied to 401(k)s (and the reverse), and agreeing with a wrong number in the question.

**Not measured:** personalized advice. General-purpose chatbots aren't FINRA-regulated, so scoring them on the advice boundary would be unfair. This benchmark checks facts only.

## Protocol (pre-registered before collection)

1. Freeze: commit the questions and key, and tag it. After that, any change goes in a changelog with a reason.
2. Assistants: the **free web tiers** of ChatGPT, Gemini and Claude, which is what customers actually use. Record the product, the model label shown, the date, and whether it searched the web.
3. One question per **new chat**, logged in with memory and custom instructions off. The question is pasted exactly as written. The first answer is recorded word for word, with no follow-ups and no regenerating.
4. Grade by hand with [`RUBRIC.md`](RUBRIC.md), then run the checker's rules layer on every answer.
5. Publish every answer, grade and checker result, including anywhere Claude does badly.

**Framing for publication:** a dated snapshot of 3 free assistants on 30 questions. Not a ranking of models. With 30 questions, a gap of a few answers between assistants is noise.

## Changelog

- 2026-09-26: v1 frozen. 30 questions, 37 key claims.
