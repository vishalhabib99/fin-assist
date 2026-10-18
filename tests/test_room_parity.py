"""The web page (docs/room/room.js) and the MCP tool (room.py) must give identical answers."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from fin_doctor.checker import FACTS, FACTS_PATH
from fin_doctor.room import contribution_room

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


def _cases(n=400, seed=11):
    rng = random.Random(seed)
    ranges = [r for v in FACTS["income_phase_outs"]["roth_ira_contribution"].values() if isinstance(v, dict) for r in [v["2026"]]]
    cases = []
    for _ in range(n):
        start, end = rng.choice(ranges)
        cases.append({
            "age_at_year_end": rng.choice([25, 49, 50, 59, 60, 61, 63, 64, 72, 73, 80]),
            "compensation": rng.choice([0, 3_000, 7_499, 7_500, 8_600, 60_000, 250_000]),
            "plan_type": rng.choice(["none", "401k", "simple"]),
            "plan_deferrals_so_far": rng.choice([0, 5_000, 24_500, 40_000]),
            "traditional_ira_so_far": rng.choice([0, 1_000, 7_500, 9_000]),
            "roth_ira_so_far": rng.choice([0, 500, 3_000]),
            "magi": rng.choice([None, start - 1, start, start + 1, rng.randint(start, end), end - 400, end - 150, end - 1, end, end + 50_000]),
            "filing_status": rng.choice(["single", "head_of_household", "married_joint", "married_separate", "qualifying_surviving_spouse"]),
            "lived_with_spouse": rng.choice([True, False]),
        })
    return cases


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_js_matches_python():
    cases = _cases()
    script = (
        "const R=require(process.argv[1]);const f=require(process.argv[2]);"
        "const cs=JSON.parse(require('fs').readFileSync(0,'utf8'));"
        "console.log(JSON.stringify(cs.map(c=>R.contributionRoom(f,c))));"
    )
    out = subprocess.run([NODE, "-e", script, str(ROOT / "docs/room/room.js"), str(FACTS_PATH)],
                         input=json.dumps(cases), capture_output=True, text=True, check=True).stdout
    for case, js in zip(cases, json.loads(out)):
        assert js == contribution_room(**case), case


def test_page_copy_of_facts_is_current():
    assert json.loads((ROOT / "docs/room/facts.json").read_text()) == FACTS, \
        "docs/room/facts.json is stale: cp data/facts.json docs/room/facts.json"
