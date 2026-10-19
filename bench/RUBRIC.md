# Grading rubric

Each answer gets exactly one grade. A person grades against the key in [`questions.jsonl`](questions.jsonl). No model grades, because the checker's judges are Claude and Claude is one of the assistants being tested.

| Grade | Rule |
|---|---|
| **WRONG** | At least one statement contradicts a key claim, or the answer matches a `known_wrong` entry. One wrong claim is enough, even if the rest is right. |
| **INCOMPLETE** | Nothing contradicts the key, but at least one `required` claim is missing. |
| **CORRECT** | Every `required` claim is present and nothing contradicts the key. |
| **DECLINED** | No substantive answer (for example "consult a tax professional" with no figure or rule). |

**Tags on WRONG** (one or more): `stale_year` (last year's number given as this year's), `outdated_law` (a rule SECURE 2.0 changed, such as RMDs at 72 or a 50% penalty), `wrong_account_type` (an IRA rule applied to a 401(k) or the reverse), `false_premise_accepted` (agrees with a wrong number in the question), `other`.

**Claims outside the key** (such as spousal IRAs, the future age-75 RMD start, or the Roth catch-up rule for high earners) are **not graded**. The grader writes them in `notes`. Accurate extras never lower a grade. An extra that is clearly wrong is recorded in notes but doesn't change the grade either, because the key can't prove it wrong.

**"This year" questions** (q02, q03, q08, q16) mean 2026, since collection finishes before 2027-01-01. Giving a prior year's figure as the answer is WRONG (`stale_year`), even if it's labeled with its year. It's INCOMPLETE if the assistant clearly says it doesn't know the current year's figure and gives no wrong one.

**Rounding and phrasing:** "$7,500 plus $1,100" counts as "$8,600". "Once a year" counts as "one per 12 months". "Once per IRA account" is WRONG.

## Second signal: would the checker have caught it?

Every collected answer is also run through `fin_assist.check()` (rules layer only, which is deterministic and free). This gives the checker's first **non-synthetic** test data:

- **Checker recall on real mistakes:** of the WRONG answers, how many got REVIEW
- **Checker false-REVIEW on real answers:** of the CORRECT answers, how many got REVIEW

Both are reported as-is, including misses. The judge layers aren't part of the headline, because they cost usage per call.
