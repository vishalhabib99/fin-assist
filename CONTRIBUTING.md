# Contributing

The most useful contribution is a figure: a new one, or next year's value for one that's already here.

## Add or update a figure

1. Find the figure on a **primary source**: an IRS newsroom release, revenue procedure, notice or publication, or an SSA fact sheet. Not a news article, blog or summary site.
2. Edit the domain file in [`registry/`](registry/README.md). Add the year to `values` and its source key to `source`. If the source is new, add it under `sources` with its `url`, `title` and the `read_on` date.
3. A new fact also needs `cues`: groups of regex alternatives that must all appear in a sentence for the figure to be about this fact (see existing facts).
4. Run `python -m retirement_answer_check.registry` and `pytest -q`.
5. In the pull request, quote the sentence or table row from the source that gives the value.

Rules: never fill a year from a projection or from last year's value. A year that isn't published stays missing, so the checker reports `unknown_year` instead of guessing.

## Report a miss

If fin-doctor passed a wrong figure or flagged a right one, open an issue with the answer text, the year, and what it should have said. Misses become regression tests, and fixes are measured on a fresh blind set before any new result is claimed.
