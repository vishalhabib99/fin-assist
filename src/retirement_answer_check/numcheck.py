"""Number check: compare every figure in an AI answer to the verified facts registry.

For each dollar amount, percentage, age or day count, find the registry facts the
sentence is talking about (by their cues), work out which tax year the sentence
means, and compare. The finding that matters most is a stale figure: a number that
was right for an earlier year, quoted as this year's.

Statuses:
  match         the figure is right for that year
  stale         the figure belongs to an earlier year
  wrong_year    the figure belongs to a later year
  wrong         the topic is recognized, the figure matches no year
  unknown_year  the topic is recognized, the registry has no figure for that year yet
  unverified    a figure the registry knows exists but doesn't cover (e.g. RMD age 75)
Any status other than match makes the decision REVIEW.
"""
from __future__ import annotations

import datetime as _dt
import re

from .registry import load, lookup

FACTS = load()
_CUES = {fid: [re.compile("|".join(g), re.I) for g in f.get("cues", [])] for fid, f in FACTS.items()}

_SENT = re.compile(r"(?<=[.!?;])\s+|\n+")
_YEAR = re.compile(r"\b(20[2-3]\d)\b")
_REL = re.compile(r"\b(this|next|last) (tax )?year\b", re.I)
_USD = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(k\b|K\b|thousand|million)?|\b(\d{1,3}(?:,\d{3})+)\s*dollars", re.I)
_PCT = re.compile(r"\b(\d{1,2}(?:\.\d+)?)\s?(%|percent\b)", re.I)
_AGE = re.compile(r"\b(?:age|aged|turns?|turning|reach(?:es|ing)?)\s+(\d{2})\b|\b(\d{2})(?:½|\s*1/2)?\s*(?:years? old|or older|and older)", re.I)
_DAYS = re.compile(r"\b(\d{1,3})[\s-]days?\b", re.I)
_GATE = {"usd": (0.6, 1.6), "age": None, "percent": None, "days": None}
# The customer's own amounts ("your salary is $210,000", "on pace for $16,800") are not official figures.
_CUSTOMER = re.compile(r"\b(?:your (?:salary|income|wages|pay|balance|savings|benefit|portfolio)\b|you(?:'re| are|'ve| have)? ?(?:planning to|plan to|earn|earned|make|made|saved|contributed|put in|on pace)|on pace for|currently)\b[^.;:$]{0,40}$", re.I)
_AFTER = re.compile(r"^[^.;$%\d]{0,30}?\b(?:in|for|of)\s+(?:tax year\s*)?(20[2-3]\d)\b|^\s*,?\s*(20[2-3]\d)\b")


def _kind(unit: str) -> str:
    return "usd" if unit.startswith("usd") else {"age_years": "age"}.get(unit, unit)


def _numbers(sentence: str):
    for m in _USD.finditer(sentence):
        if m.group(4):
            yield "usd", float(m.group(4).replace(",", "")), m
            continue
        n = float(m.group(1).replace(",", "") + (m.group(2) or ""))
        mult = (m.group(3) or "").lower()
        n *= 1000 if mult in ("k", "thousand") else 1_000_000 if mult == "million" else 1
        yield "usd", n, m
    for m in _PCT.finditer(sentence):
        yield "percent", float(m.group(1)), m
    for m in _AGE.finditer(sentence):
        yield "age", float(m.group(1) or m.group(2)), m
    for m in _DAYS.finditer(sentence):
        yield "days", float(m.group(1)), m


def _year_for(sentence: str, m: re.Match, context_year: int, default_year: int) -> int:
    after = _AFTER.match(sentence[m.end():])
    if after:
        return int(after.group(1) or after.group(2))
    years = [(y.start(), int(y.group(1))) for y in _YEAR.finditer(sentence)]
    before = [y for pos, y in years if pos < m.start()]
    if before:
        return before[-1]
    if years:
        return years[0][1]
    rel = _REL.search(sentence)
    if rel:
        return default_year + {"this": 0, "next": 1, "last": -1}[rel.group(1).lower()]
    return context_year


def _candidates(sentence: str, kind: str, n: float) -> list[str]:
    out = []
    for fid, fact in FACTS.items():
        if _kind(fact["unit"]) != kind or not _CUES[fid] or not all(c.search(sentence) for c in _CUES[fid]):
            continue
        vals = list(fact["values"].values())
        gate = _GATE[kind]
        if gate and not any(gate[0] * v <= n <= gate[1] * v for v in vals):
            continue
        if kind == "age" and not any(abs(n - v) <= 5 for v in vals):
            continue
        out.append(fid)
    return out


def _same(a: float, b: float) -> bool:
    return abs(a - b) < 0.005


def _judge(n: float, year: int, cands: list[str]) -> dict:
    for fid in cands:
        v = lookup(FACTS, fid, year)
        if v is not None and _same(v, n):
            return {"status": "match", "fact": fid}
    for fid in cands:
        for y, v in FACTS[fid]["values"].items():
            if y != "any" and _same(v, n) and int(y) != year:
                current = lookup(FACTS, fid, year)
                if current is None:  # not published yet for this year: can't call it stale
                    return {"status": "unknown_year", "fact": fid, "figure_year": int(y)}
                return {"status": "stale" if int(y) < year else "wrong_year", "fact": fid,
                        "figure_year": int(y), "expected": current}
    for fid in cands:
        if n in FACTS[fid].get("unverified_values", []):
            return {"status": "unverified", "fact": fid}
    known = [fid for fid in cands if lookup(FACTS, fid, year) is not None]
    if not known:
        return {"status": "unknown_year", "fact": cands[0]}
    return {"status": "wrong", "fact": known[0] if len(known) == 1 else None,
            "expected": {fid: lookup(FACTS, fid, year) for fid in known}}


def _source(fid: str | None, year: int):
    if not fid:
        return None
    srcs = FACTS[fid]["sources"]
    src = srcs.get(str(year)) or srcs.get("any") or next(iter(srcs.values()))
    return src["url"]


def check_numbers(answer: str, year: int | None = None) -> dict:
    """Return {"decision": "PASS" | "REVIEW", "year": default year, "claims": [...]}.

    year: the tax year the answer is about when a sentence doesn't say (default: this year).
    Numbers whose topic the registry doesn't recognize are not judged; PASS means no
    recognized figure is wrong, not that the answer is correct.
    """
    default_year = year or _dt.date.today().year
    context_year, claims, previous = default_year, [], ""
    for sentence in filter(None, (s.strip() for s in _SENT.split(answer or ""))):
        years = _YEAR.findall(sentence)
        for kind, n, m in _numbers(sentence):
            if _CUSTOMER.search(sentence[:m.start()]):
                continue
            y = _year_for(sentence, m, context_year, default_year)
            # The topic is often named one sentence earlier ("The HSA family limit... For 2026 it's $8,550.")
            cands = _candidates(sentence, kind, n) or _candidates(previous + " " + sentence, kind, n)
            if not cands:
                continue
            verdict = _judge(n, y, cands)
            fid = verdict.get("fact")
            claims.append({"span": m.group(0).strip(), "value": n, "year": y, **verdict,
                           "label": FACTS[fid]["label"] if fid else None, "source": _source(fid, y),
                           "sentence": sentence})
        if years:
            context_year = int(years[-1])
        previous = sentence
    bad = [c for c in claims if c["status"] != "match"]
    return {"decision": "REVIEW" if bad else "PASS", "year": default_year, "claims": claims}
