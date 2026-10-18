"""Verified financial facts registry.

One JSON file per domain in registry/. Every fact has an id, a unit, values keyed
by year ("any" when the figure doesn't change by year) and a source for each value.
lookup() never guesses: a year the registry doesn't hold returns None, so a caller
can send the answer to REVIEW instead of falling back to another year's figure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_REPO_DIR = Path(__file__).resolve().parents[2] / "registry"
REGISTRY_DIR = _REPO_DIR if _REPO_DIR.exists() else Path(__file__).resolve().parent / "registry_data"

UNITS = {"usd", "usd_per_year", "usd_per_month", "usd_taxable_income", "percent", "age_years", "days"}
ID = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
YEAR = re.compile(r"^(20\d\d|any)$")


def load(directory: Path = REGISTRY_DIR) -> dict[str, dict]:
    """Return {fact_id: fact}, each fact carrying its domain and resolved source per value."""
    facts = {}
    for path in sorted(directory.glob("*.json")):
        doc = json.loads(path.read_text())
        for fact in doc["facts"]:
            src = fact["source"]
            per_year = src if isinstance(src, dict) else {y: src for y in fact["values"]}
            facts[fact["id"]] = {**fact, "domain": doc["domain"],
                                 "sources": {y: doc["sources"][k] for y, k in per_year.items()}}
    return facts


def lookup(facts: dict[str, dict], fact_id: str, year: int) -> float | None:
    values = facts[fact_id]["values"]
    if "any" in values:
        return values["any"]
    return values.get(str(year))


def validate(directory: Path = REGISTRY_DIR) -> list[str]:
    """Return a list of problems; empty means the registry is well formed."""
    problems, seen = [], set()
    for path in sorted(directory.glob("*.json")):
        doc = json.loads(path.read_text())
        name = path.name
        if doc.get("domain") != path.stem:
            problems.append(f"{name}: domain {doc.get('domain')!r} should be {path.stem!r}")
        for key, src in doc.get("sources", {}).items():
            if not str(src.get("url", "")).startswith("https://") or not src.get("read_on"):
                problems.append(f"{name}: source {key} needs an https url and read_on")
        for fact in doc.get("facts", []):
            fid = fact.get("id", "?")
            if not ID.match(fid):
                problems.append(f"{name}: bad id {fid!r}")
            if fid in seen:
                problems.append(f"{name}: duplicate id {fid}")
            seen.add(fid)
            if fact.get("unit") not in UNITS:
                problems.append(f"{name}: {fid} unit {fact.get('unit')!r} not in {sorted(UNITS)}")
            values = fact.get("values") or {}
            if not values:
                problems.append(f"{name}: {fid} has no values")
            if "any" in values and len(values) > 1:
                problems.append(f"{name}: {fid} mixes 'any' with year values")
            for year, value in values.items():
                if not YEAR.match(year):
                    problems.append(f"{name}: {fid} bad year key {year!r}")
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    problems.append(f"{name}: {fid} {year} value must be a number")
            src = fact.get("source")
            keys = src.values() if isinstance(src, dict) else [src]
            if isinstance(src, dict) and set(src) != set(values):
                problems.append(f"{name}: {fid} needs a source for each year")
            for key in keys:
                if key not in doc.get("sources", {}):
                    problems.append(f"{name}: {fid} cites unknown source {key!r}")
    return problems


if __name__ == "__main__":
    issues = validate()
    print("\n".join(issues) or f"registry OK: {len(load())} facts")
    raise SystemExit(1 if issues else 0)
