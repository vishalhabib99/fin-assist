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
_AGE = re.compile(r"\b(?:age|aged|turns?|turning|reach(?:es|ing)?)\s+(\d{2})(½|\s?1/2)?(?!\d)|\b(\d{2})(½|\s?1/2)?\s*(?:years? old|or older|and older)", re.I)
_DAYS = re.compile(r"\b(\d{1,3})[\s-]days?\b", re.I)
_GATE = {"usd": (0.4, 2.5), "age": None, "percent": None, "days": None}
# A dollar amount is judged only when the wording states it as an official figure, or when it
# equals some year's figure exactly. "That's $6,000 for the year" is arithmetic, not a claim.
_STATED = re.compile(r"\b(?:limits?|max(?:imum)?|caps?|ceiling|catch[- ]?up|exclusion|deduction|deductible|out[- ]of[- ]pocket|threshold|wage base|taxable max(?:imum)?|up to|at least|no more than|bracket|earnings (?:test|limit)|exempt amount|benefit|standard)\b", re.I)
_STATED_AFTER = re.compile(r"^\s*(?:annual |yearly |contribution |deferral )?(?:limit|cap|maximum|catch[- ]?up)\b|^[^.;$]{0,25}\b(?:on top of|in addition to|above|beyond) the\b[^.;$]{0,25}\blimit", re.I)
_LIST_JOIN = re.compile(r"\b(?:and|or|while|vs\.?|versus)\b|/", re.I)
_NOT_LIST = re.compile(r"\b(?:so|but|your|you|which|leaves?)\b", re.I)
# "That's $10,000" right after a sentence about a limit refers back to it.
_REFER = re.compile(r"\b(?:that's|that is|it's|it is|which is)\s*$", re.I)
# The customer's own amounts ("your salary is $210,000", "on pace for $16,800") are not official figures.
_CUSTOMER = re.compile(r"\b(?:your (?:salary|income|wages|pay|balance|savings|benefit|portfolio|personal|own|total|planned)\b|you(?:'re| are|'ve| have)? ?(?:planning to|plan to|earn|earned|make|made|saved|contributed|put in|on pace)|on pace for|currently)\b[^.;:$]{0,40}$", re.I)
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
        yield "age", float(m.group(1) or m.group(3)) + (0.5 if (m.group(2) or m.group(4)) else 0), m
    for m in _DAYS.finditer(sentence):
        yield "days", float(m.group(1)), m


_FROM = re.compile(r"\bfrom\s*$", re.I)
_TO = re.compile(r"\bto\s*$", re.I)


def _year_for(sentence: str, m: re.Match, context_year: int, default_year: int) -> int:
    after = _AFTER.match(sentence[m.end():])
    if after:
        return int(after.group(1) or after.group(2))
    # "goes from $8,750 to $9,000" after "from $4,400 in 2026 to $4,500 in 2027": earliest / latest year
    span_years = sorted({int(y) for y in _YEAR.findall(sentence)})
    if len(span_years) >= 2:
        if _FROM.search(sentence[:m.start()]):
            return span_years[0]
        if _TO.search(sentence[:m.start()]):
            return span_years[-1]
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
    context_year, claims, recent = default_year, [], []
    for sentence in filter(None, (s.strip() for s in _SENT.split(answer or ""))):
        years = _YEAR.findall(sentence)
        found = sorted(_numbers(sentence), key=lambda t: t[2].start())
        prev_usd, prev_stated = None, False
        for kind, n, m in found:
            if _CUSTOMER.search(sentence[:m.start()]):
                if kind == "usd":
                    prev_usd, prev_stated = m, False
                continue
            stated = True
            if kind == "usd":
                window = sentence[(prev_usd.end() if prev_usd else 0):m.start()]
                stated = bool(_STATED.search(window) or _STATED_AFTER.match(sentence[m.end():])
                              # a list under one topic word: "$16,100 for single filers and $31,500 for joint"
                              or (prev_stated and len(window) <= 40 and _LIST_JOIN.search(window)
                                  and not _NOT_LIST.search(window))
                              or (_REFER.search(window) and any(_STATED.search(r) for r in recent)))
                prev_usd, prev_stated = m, stated
            y = _year_for(sentence, m, context_year, default_year)
            # The topic is often named one sentence earlier ("The HSA family limit... For 2026 it's $8,550.")
            cands = _candidates(sentence, kind, n) or _candidates(" ".join(recent + [sentence]), kind, n)
            if not cands:
                continue
            exact = any(_same(v, n) for fid in cands for v in FACTS[fid]["values"].values())
            if not (stated or exact):
                continue
            verdict = _judge(n, y, cands)
            fid = verdict.get("fact")
            claims.append({"span": m.group(0).strip(), "value": n, "year": y, **verdict,
                           "label": FACTS[fid]["label"] if fid else None, "source": _source(fid, y),
                           "sentence": sentence})
        if years:
            context_year = int(years[-1])
        recent = (recent + [sentence])[-2:]
    bad = [c for c in claims if c["status"] != "match"]
    return {"decision": "REVIEW" if bad else "PASS", "year": default_year, "claims": claims}
