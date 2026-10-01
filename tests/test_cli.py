import json
from pathlib import Path

import pytest

from option_hedging.__main__ import main
from option_hedging.experiments import prepare_output

ROOT = Path(__file__).resolve().parents[1]


def test_quick_reproduce_command(tmp_path, capsys):
    output = tmp_path / "quick"
    main(["reproduce", "--quick", "--output", str(output)])
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "quick"
    assert (output / "statistics.json").exists()
    assert (output / "data" / "seed_manifest.csv").exists()
    assert (output / "manifest.json").exists()


def test_output_rejects_protected_directories():
    for path in [ROOT, ROOT / "src", ROOT / "paper", ROOT / "config", ROOT / "src" / "danger"]:
        with pytest.raises(ValueError):
            prepare_output(path, replace=True)


def test_output_rejects_existing_results_without_force(tmp_path):
    (tmp_path / "sentinel.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_output(tmp_path)
    assert (tmp_path / "sentinel.txt").read_text(encoding="utf-8") == "keep"
