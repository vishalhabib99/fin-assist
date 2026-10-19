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
_AGE = re.compile(r"\b(?:age|aged|turns?|turning|reach(?:es|ing)?|(?:begin|start|starts|must|until|by|RMDs?|distributions?)\s+at)\s+(\d{2})(½|\s?1/2)?(?!\d)|\b(\d{2})(½|\s?1/2)?\s*(?:years? old|or older|and older)", re.I)
_DAYS = re.compile(r"\b(\d{1,3})[\s-]days?\b", re.I)
_GATE = {"usd": (0.4, 2.5), "age": None, "percent": None, "days": None}
# A dollar amount is judged only when the wording states it as an official figure, or when it
# equals some year's figure exactly. "That's $6,000 for the year" is arithmetic, not a claim.
_STATED = re.compile(r"\b(?:limits?|max(?:imum)?|caps?|ceiling|catch[- ]?up|exclusion|deduction|deductible|out[- ]of[- ]pocket|threshold|wage base|taxable max(?:imum)?|up to|at least|no more than|bracket|earnings (?:test|limit)|exempt amount|benefit|standard)\b", re.I)
# "You can contribute $X" / "able to defer $X" states the limit, unless it's room left ("$3,000 more")
_CAN_PUT = re.compile(r"\b(?:can|could|able to|allowed to|may)\s+(?:contribute|defer|put in|put away|save)\s*$", re.I)
_ROOM_LEFT = re.compile(r"^\s*(?:more|extra|additional|left|remaining)\b", re.I)
_STATED_AFTER = re.compile(r"^\s*(?:annual |yearly |contribution |deferral )?(?:limit|cap|maximum|catch[- ]?up|carry ?over|roll ?over)\b|^\s*(?:can|may)\s+(?:be\s+)?(?:carr(?:y|ied)|roll(?:ed)?)\s?over|^[^.;$]{0,25}\b(?:on top of|in addition to|above|beyond) the\b[^.;$]{0,25}\blimit", re.I)
_LIST_JOIN = re.compile(r"\b(?:and|or|while|vs\.?|versus|to|through)\b|/|–|-", re.I)
_NOT_LIST = re.compile(r"\b(?:so|but|your|you|which|leaves?)\b", re.I)
# The business's or customer's own numbers, and arithmetic on official figures: "your estimated
# benefit is $2,880", "our plan has a $7,250 out-of-pocket max", "combined ... up to $35,750".
# Judged only if they equal a known figure exactly.
_OWN = re.compile(r"\b(?:your (?:estimated|projected|current|personal|own|total|employer|cap|household|combined)|our\b|my\b|estimated|projected|would be|could (?:contribute|put|save|give) up to|combined|in total|altogether|employer match|matches|remaining|room|so far|year-to-date|max(?:ing)? out|reduced|you'd receive|would you like|do you want|you can (?:choose|elect))", re.I)
_OURS = re.compile(r"\b(?:our|my|with your|based on your|on your|would be(?: reduced)?|reduced)\b|\byour\s*$", re.I)
_OURS_HEADING = re.compile(r"\b(?:our|my)\b", re.I)
# "That's $10,000" right after a sentence about a limit refers back to it.
_REFER = re.compile(r"\b(?:that's|that is|it's|it is|which is)\s*$", re.I)
# The customer's own amounts ("your salary is $210,000", "on pace for $16,800") are not official figures.
_CUSTOMER = re.compile(r"\b(?:your (?:salary|income|wages|pay|balance|savings|benefit|portfolio|personal|own|total|planned)\b|you(?:'re| are|'ve| have)? ?(?:planning to|plan to|earn|earned|make|made|saved|contributed|put in|on pace)|on pace for|currently)\b[^.;:$]{0,40}$", re.I)
_AFTER = re.compile(r"^[^.;$%\d]{0,30}?\b(?:in|for|of)\s+(?:tax year\s*)?(20[2-3]\d)\b|^\s*,?\s*(20[2-3]\d)\b")
# "Carryover into 2027", "until 2028": a destination year, not the year the figure applies to
_YEAR_ANY = re.compile(r"(?<!until )(?<!through )\b(20[2-3]\d)\b")
# "Carryover into 2027: up to $680" is the 2026 plan year's carryover
_CARRY_INTO = re.compile(r"carr(?:y|ies|ied)?\s?over\s+into\s+(20[2-3]\d)", re.I)
# Markdown headings and bold lines name the topic for the lines under them
_HEADING = re.compile(r"^\s*(?:#{1,6}\s+.+|\*\*[^*]+\*\*:?|[^.!?]{3,80}:)\s*$")


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
    carry = _CARRY_INTO.search(sentence)
    if carry and carry.start() < m.start():
        return int(carry.group(1)) - 1
    after = _AFTER.match(sentence[m.end():])
    if after:
        return int(after.group(1) or after.group(2))
    # "goes from $8,750 to $9,000" after "from $4,400 in 2026 to $4,500 in 2027": earliest / latest year
    span_years = sorted({int(y) for y in _YEAR_ANY.findall(sentence)})
    if len(span_years) >= 2:
        if _FROM.search(sentence[:m.start()]):
            return span_years[0]
        if _TO.search(sentence[:m.start()]):
            return span_years[-1]
    years = [(y.start(), int(y.group(1))) for y in _YEAR_ANY.finditer(sentence)]
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


def _topics(text: str, kind: str) -> list[str]:
    """Every fact of this kind whose cues are all in the text, whatever the figure."""
    return [fid for fid, f in FACTS.items()
            if _kind(f["unit"]) == kind and _CUES[fid] and all(c.search(text) for c in _CUES[fid])]


def _carried(sentence: str, context: str, kind: str, n: float) -> list[str]:
    """Candidates whose topic was named earlier (previous sentences, a heading, the first line).

    For percentages, ages and day counts, the fact's specific cues (all but its first group)
    must still be in the sentence itself: "loans up to 50%" two lines after a sentence about
    withholding is not a withholding rate.
    """
    out = _candidates(context + " " + sentence, kind, n)
    if kind == "usd":
        return out
    if kind == "age":
        return out
    return [fid for fid in out if len(_CUES[fid]) > 1 and all(c.search(sentence) for c in _CUES[fid][1:])]


def _is_total(n: float, year: int, facts: list[str]) -> bool:
    """$32,500 = the $24,500 limit + the $8,000 catch-up: arithmetic on two of the figures the
    answer is talking about, not a claim of its own."""
    vals = [(fid, lookup(FACTS, fid, year)) for fid in facts]
    vals = [(f, v) for f, v in vals if v]
    return any(fa != fb and _same(a + b, n) for i, (fa, a) in enumerate(vals) for fb, b in vals[i + 1:])


def _exact_any(sentence: str, context: str, kind: str, n: float) -> bool:
    cands = _candidates(sentence, kind, n) or _carried(sentence, context, kind, n)
    return any(_same(v, n) for fid in cands for v in FACTS[fid]["values"].values())


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


_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_RULE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _tables_to_sentences(text: str) -> tuple[str, set[str]]:
    """Turn each markdown table cell into "<row label> <column header> <table header>: <cell>."

    A table of figures states each one, so its cells are marked as stated claims.
    """
    out, header, stated = [], None, set()
    for line in text.splitlines():
        row = _ROW.match(line)
        if not row:
            header = None
            out.append(line)
            continue
        if _RULE.match(line):
            continue
        cells = [c.strip() for c in row.group(1).split("|")]
        if header is None:
            header = cells
            continue
        for i, cell in enumerate(cells[1:], start=1):
            col = header[i] if i < len(header) else ""
            sentence = f"{cells[0]} {col} {header[0]}: {cell}."
            stated.add(sentence)
            out.append(sentence)
    return "\n".join(out), stated


def _model_labels(llm, answer: str, sentences: list[str], year: int):
    """Ask the model which fact each number is about. {(sentence index, start): (fact, year)}."""
    from .llm_match import build_prompt, parse
    spans = [(si, m.start(), m.group(0).strip(), sentence, _options(kind, n))
             for si, sentence in enumerate(sentences) for kind, n, m in _numbers(sentence)]
    spans = [s for s in spans if s[4]]
    if not spans:
        return {}
    figures = [(i, span, sentence, options) for i, (_, _, span, sentence, options) in enumerate(spans)]
    labels = parse(llm(build_prompt(answer, figures, FACTS, year)), figures, FACTS)
    return {(si, start): labels.get(i, (None, None)) for i, (si, start, *_) in enumerate(spans)}


def _options(kind: str, n: float) -> list[str]:
    """The facts a number could be: same kind, and for dollars the same size range the rules use."""
    gate = _GATE[kind]
    return [fid for fid, f in FACTS.items() if _kind(f["unit"]) == kind and (
        not gate or any(gate[0] * v <= n <= gate[1] * v for v in f["values"].values()))
        and (kind != "age" or any(abs(n - v) <= 5 for v in f["values"].values()))]


def check_numbers(answer: str, year: int | None = None, llm=None, llm_mode: str = "add") -> dict:
    """Return {"decision": "PASS" | "REVIEW", "year": default year, "claims": [...]}.

    year: the tax year the answer is about when a sentence doesn't say (default: this year).
    llm: optional prompt -> text callable (see llm_match). The model says which registry fact
    a number is about; values and the comparison stay here. llm_mode "add": the model labels
    only numbers the rules didn't judge, and the rules keep the final say on the rest.
    "label": the model labels every number. If the model fails,
    the answer is checked with the rules only and "llm" in the result says so.
    Numbers whose topic the registry doesn't recognize are not judged; PASS means no
    recognized figure is wrong, not that the answer is correct.
    """
    default_year = year or _dt.date.today().year
    context_year, claims, recent = default_year, [], []
    text, table_cells = _tables_to_sentences(answer or "")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0] if lines else ""          # "Here's a summary of the 2026 limits for your 401(k):"
    headings: list[str] = []
    sentences = [s.strip() for s in _SENT.split(text) if s.strip()]
    labels, llm_status = None, None
    if llm is not None:
        try:
            labels, llm_status = _model_labels(llm, answer or "", sentences, default_year), "used"
        except Exception as e:  # any model failure: rules only for this answer
            llm_status = f"failed, rules only: {type(e).__name__}: {e}"[:200]
    for si, sentence in enumerate(sentences):
        years = _YEAR_ANY.findall(_CARRY_INTO.sub("", sentence))
        found = sorted(_numbers(sentence), key=lambda t: t[2].start())
        prev_usd, prev_stated = None, False
        context = " ".join([title] + headings[-2:] + recent)
        if headings and _OURS_HEADING.search(headings[-1]) and not _HEADING.match(sentence):
            recent = (recent + [sentence])[-2:]
            continue   # "Our plan's numbers": the company's own figures
        for kind, n, m in found:
            # The customer's own amounts are skipped, unless the amount is exactly an official
            # figure ("you earn above $23,400" is the earnings test, not their pay).
            if _CUSTOMER.search(sentence[:m.start()]) and not _exact_any(sentence, context, kind, n):
                if kind == "usd":
                    prev_usd, prev_stated = m, False
                continue
            stated = True
            if kind != "usd" and _OWN.search(sentence[:m.start()]):
                continue
            if kind == "usd" and sentence not in table_cells:
                window = sentence[(prev_usd.end() if prev_usd else 0):m.start()]
                stated = bool(_STATED.search(window) or _STATED_AFTER.match(sentence[m.end():])
                              # a list under one topic word: "$16,100 for single filers and $31,500 for joint"
                              or (prev_stated and len(window) <= 40 and _LIST_JOIN.search(window)
                                  and not _NOT_LIST.search(window))
                              or (_REFER.search(window) and any(_STATED.search(r) for r in recent))
                              or (_CAN_PUT.search(window) and not _ROOM_LEFT.match(sentence[m.end():])))
                if _OWN.search(window) or _OURS.search(sentence[:m.start()]):
                    stated = False
                prev_usd, prev_stated = m, stated
            y = _year_for(sentence, m, context_year, default_year)
            def model_claim() -> bool:
                """Judge this number by the model's label. False when the model says none."""
                fid, model_year = labels.get((si, m.start()), (None, None))
                gate = _GATE[kind]
                if fid is None or _kind(FACTS[fid]["unit"]) != kind or (
                        gate and not any(gate[0] * v <= n <= gate[1] * v for v in FACTS[fid]["values"].values())):
                    return False
                my = model_year or y
                exact = any(_same(v, n) for v in FACTS[fid]["values"].values())
                if kind == "usd" and not exact and _is_total(n, my, _topics(context + " " + sentence, kind) + [fid]):
                    return False
                claims.append({"span": m.group(0).strip(), "value": n, "year": my, **_judge(n, my, [fid]),
                               "label": FACTS[fid]["label"], "source": _source(fid, my), "sentence": sentence})
                return True

            if labels is not None and llm_mode == "label":
                model_claim()
                continue
            add = labels is not None and llm_mode == "add"
            # The topic is often named one sentence earlier ("The HSA family limit... For 2026 it's $8,550.")
            cands = _candidates(sentence, kind, n) or _carried(sentence, context, kind, n)
            if not cands:
                if add:
                    model_claim()
                continue
            exact = any(_same(v, n) for fid in cands for v in FACTS[fid]["values"].values())
            if not (stated or exact):
                if add:
                    model_claim()
                continue
            if kind == "usd" and not exact and _is_total(n, y, _topics(context + " " + sentence, kind)):
                continue
            verdict = _judge(n, y, cands)
            if verdict["status"] != "match":
                more = [f for f in _carried(sentence, context, kind, n) if f not in cands]
                if more and _judge(n, y, more)["status"] == "match":
                    verdict = _judge(n, y, more)
            fid = verdict.get("fact")
            claims.append({"span": m.group(0).strip(), "value": n, "year": y, **verdict,
                           "label": FACTS[fid]["label"] if fid else None, "source": _source(fid, y),
                           "sentence": sentence})
        if years:
            ys = [int(y) for y in years]
            context_year = context_year if context_year in ys and len(set(ys)) > 1 else ys[-1]
        recent = (recent + [sentence])[-2:]
        if _HEADING.match(sentence):
            headings.append(sentence)
    bad = [c for c in claims if c["status"] != "match"]
    out = {"decision": "REVIEW" if bad else "PASS", "year": default_year, "claims": claims}
    if llm_status:
        out["llm"] = llm_status
    return out
