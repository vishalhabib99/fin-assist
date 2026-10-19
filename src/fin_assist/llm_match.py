"""Opt-in model layer for the number check: which registry fact is each number about?

The model only labels. For each number in a draft it picks one fact id from the registry
list, or "none", and the year the sentence means. It never sees or writes a value: every
right value still comes from the registry, and the comparison stays in numcheck.

    from fin_assist.llm_match import ollama, openai_compatible
    check_numbers(draft, llm=ollama("qwen3:8b"))
    check_numbers(draft, llm=openai_compatible("http://localhost:8000/v1", "my-model", api_key="..."))

`llm` is any callable that takes a prompt string and returns the model's text.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable

Ask = Callable[[str], str]

# Fixed prefix first (instructions + the numbered fact list), so a local model server can
# reuse its cache across calls; only the answer and its figures change.
_PREFIX = """You label the numbers in an AI assistant's answer about US money rules (retirement accounts, HSA/FSA, Social Security, payroll and federal tax).

For each figure, decide whether the answer presents it as an OFFICIAL figure (an IRS or SSA limit, rate, threshold, age or day count) and, if so, which fact below it is. Each figure lists the only fact numbers it can be.

Choose 0 (none) when the number is:
- the customer's own amount (salary, balance, contributions so far, planned or elected amounts, their age)
- a company's or plan's own number (our plan's deductible, an employer match)
- arithmetic (a sum of two figures, room left, a monthly amount, tax owed, a dollar result of a rate)
- a fee, a return, a date, or none of its listed facts

Pick the fact the sentence is ABOUT even when the number looks wrong or out of date: judging the value is not your job.
Year: the tax or plan year the figure applies to; "-" when the answer doesn't say.

Facts:
{catalog}
"""

_SUFFIX = """
"This year" = {year}, "next year" = {next_year}, "last year" = {last_year}.

Answer:
<<<
{answer}
>>>

Figures:
{figures}

Reply with one line per figure and nothing else: the figure number, the fact number (or 0), and the year (or -).
For example, if figure 0 is fact 12 for 2026 and figure 1 is none:
0 12 2026
1 0 -"""

_CATALOG: dict[int, str] = {}


def _catalog(facts: dict) -> tuple[str, dict[str, int]]:
    key = id(facts)
    if key not in _CATALOG:
        _CATALOG[key] = "\n".join(f"{k}. {f['label']}" for k, f in enumerate(facts.values(), 1))
    return _CATALOG[key], {fid: k for k, fid in enumerate(facts, 1)}


def build_prompt(answer: str, figures: list[tuple[int, str, str, list[str]]], facts: dict, year: int) -> str:
    """figures: (index, span, sentence, the fact ids this figure could be)."""
    catalog, number = _catalog(facts)
    listed = "\n".join(f'[{i}] "{span}" in: {sentence}\n    can be: {", ".join(str(number[f]) for f in options)}, or 0'
                        for i, span, sentence, options in figures)
    return _PREFIX.format(catalog=catalog) + _SUFFIX.format(
        year=year, next_year=year + 1, last_year=year - 1, answer=answer, figures=listed)


_LINE = re.compile(r"^\W*(\d+)\W+(\d+)\W+(20[2-3]\d|-|null|none)?", re.M)


def parse(text: str, figures: list[tuple[int, str, str, list[str]]], facts: dict) -> dict[int, tuple[str | None, int | None]]:
    """Model reply -> {figure index: (fact id or None, year or None)}. A fact outside the figure's list counts as none."""
    ids = list(facts)
    options = {i: set(opts) for i, _, _, opts in figures}
    out = {}
    for m in _LINE.finditer(text or ""):
        i, k = int(m.group(1)), int(m.group(2))
        if i not in options or i in out:
            continue
        fid = ids[k - 1] if 1 <= k <= len(ids) and ids[k - 1] in options[i] else None
        y = int(m.group(3)) if m.group(3) and m.group(3).isdigit() else None
        out[i] = (fid, y)
    return out


def _post(url: str, body: dict, headers: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def ollama(model: str = "qwen3:8b", host: str | None = None, timeout: float = 60) -> Ask:
    """A local model through Ollama. Nothing leaves the machine."""
    host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    if not host.startswith("http"):
        host = "http://" + host

    def ask(prompt: str) -> str:
        body = {"model": model, "prompt": prompt, "stream": False, "think": False,
                "options": {"temperature": 0, "num_ctx": 8192}}
        return _post(host + "/api/generate", body, {}, timeout).get("response") or ""
    return ask


def openai_compatible(base_url: str, model: str, api_key: str | None = None, timeout: float = 60) -> Ask:
    """Any OpenAI-compatible chat endpoint: the one an agent already uses (vLLM, LiteLLM, Ollama's /v1, a hosted API)."""
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def ask(prompt: str) -> str:
        body = {"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        return _post(url, body, headers, timeout)["choices"][0]["message"]["content"] or ""
    return ask
