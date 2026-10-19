"""The paste page (docs/check/) installs fin-assist from PyPI by version and runs its Python in the browser."""
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "docs" / "check" / "index.html").read_text()


def test_page_pins_the_current_version():
    # A release must bump the page too, or the page keeps running the old checker.
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert re.search(r'const FIN_ASSIST_VERSION = "([^"]+)"', PAGE).group(1) == version


def test_page_python_runs_on_its_examples():
    ns = {}
    exec(re.search(r"const PY = `(.*?)`;", PAGE, re.S).group(1), ns)
    examples = json.loads("[" + re.search(r"const EXAMPLES = \[(.*?)\];", PAGE, re.S).group(1).rstrip().rstrip(",") + "]")
    outcomes = {json.loads(ns["run"](text, "2026"))["gate"]["outcome"] for text in examples}
    assert outcomes == {"fixed", "review"}
