import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "research_walkthrough.py"


def run_example(*arguments, cwd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run([sys.executable, str(EXAMPLE), *arguments], cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout


def test_walkthrough_json_from_another_directory(tmp_path):
    report = json.loads(run_example("--json", cwd=tmp_path))
    assert report["pricing"]["black_scholes"] == pytest.approx(9.413403383853016)
    assert len(report["hedging_demo"]) == 8
    assert not list(tmp_path.iterdir())


def test_walkthrough_is_read_only(tmp_path):
    text = run_example(cwd=tmp_path)
    assert "No files were written" in text
    assert "paper dataset" in text
