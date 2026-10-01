"""Consistency checks for the committed full-study outputs."""

import csv
import json
from pathlib import Path

import pytest

from option_hedging.models import black_scholes_call, crr_call
from option_hedging.statistics import log_log_convergence
from option_hedging.experiments import _crr_csv_equivalent

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reproducible" / "data"


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_committed_statistics_match_generated_tables():
    stats = json.loads((ROOT / "reproducible" / "statistics.json").read_text())
    mc = rows("monte_carlo_convergence.csv")
    recomputed = log_log_convergence([float(r["N"]) for r in mc], [float(r["MAE"]) for r in mc])
    for key in ["slope", "standard_error", "ci_low", "ci_high", "r_squared"]:
        assert stats["monte_carlo"][key] == pytest.approx(recomputed[key], rel=1e-13, abs=1e-13)
    assert stats["black_scholes"] == pytest.approx(black_scholes_call(100, 100, 1, 0.03, 0.2))


def test_crr_table_is_deterministic_model_output():
    # Validate the model output against the committed CRR prices, while checking
    # derived error columns for internal consistency against the committed
    # benchmark.  Recomputing ``abs(price - benchmark)`` across platforms can
    # amplify independent last-bit differences from both pricing routines.
    committed_stats = json.loads((ROOT / "reproducible" / "statistics.json").read_text())
    benchmark = float(committed_stats["black_scholes"])
    recomputed_benchmark = black_scholes_call(100, 100, 1, 0.03, 0.2)
    assert recomputed_benchmark == pytest.approx(benchmark, rel=1e-12, abs=5e-12)

    for row in rows("crr_convergence.csv"):
        committed_price = float(row["CRR_price"])
        committed_signed_error = float(row["Signed_error"])
        committed_absolute_error = float(row["Absolute_error"])
        price = crr_call(100, 100, 1, 0.03, 0.2, int(row["N"]))

        assert price == pytest.approx(committed_price, rel=1e-11, abs=5e-12)
        assert committed_signed_error == pytest.approx(
            committed_price - benchmark, rel=1e-13, abs=5e-15
        )
        assert committed_absolute_error == pytest.approx(
            abs(committed_signed_error), rel=1e-13, abs=5e-15
        )


def test_frictionless_is_exact_zero_cost_slice():
    free = {int(r["Steps"]): r for r in rows("frictionless_hedging.csv")}
    zero = {int(r["Steps"]): r for r in rows("transaction_cost_sensitivity.csv") if int(r["Cost_bps"]) == 0}
    assert free.keys() == zero.keys()
    for steps in free:
        assert free[steps] == zero[steps]


def test_paper_reads_generated_assets():
    main = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    assert r"\input{../reproducible/paper_values.tex}" in main
    assert r"\input{../reproducible/tables/pricing_table.tex}" in main
    assert "upon reasonable request" not in main
    assert "github.com/zhengli0426/option-pricing-delta-hedging" in main


def test_manifest_covers_deterministic_outputs():
    manifest = json.loads((ROOT / "reproducible" / "manifest.json").read_text())
    paths = {item["path"] for item in manifest["files"]}
    assert "statistics.json" in paths
    assert "data/seed_manifest.csv" in paths
    assert "paper_values.tex" in paths
    assert "tables/transaction_cost_table.tex" in paths


def test_crr_cross_platform_verifier_handles_derived_roundoff(tmp_path):
    reference = tmp_path / "reference.csv"
    generated = tmp_path / "generated.csv"
    reference_benchmark = 9.413403383853016
    generated_benchmark = 9.413403383853015
    reference_price = 9.409437807239552
    generated_price = 9.409437807237882

    def write(path, price, benchmark):
        signed = price - benchmark
        absolute = abs(signed)
        relative = 100 * absolute / benchmark
        path.write_text(
            "N,CRR_price,Signed_error,Absolute_error,Relative_error_pct\n"
            f"500,{price},{signed},{absolute},{relative}\n",
            encoding="utf-8",
        )

    write(reference, reference_price, reference_benchmark)
    write(generated, generated_price, generated_benchmark)
    assert _crr_csv_equivalent(
        reference, generated,
        reference_benchmark=reference_benchmark,
        generated_benchmark=generated_benchmark,
    )

    generated.write_text(
        generated.read_text(encoding="utf-8").replace(
            str(100 * abs(generated_price - generated_benchmark) / generated_benchmark),
            "0.5",
        ),
        encoding="utf-8",
    )
    assert not _crr_csv_equivalent(
        reference, generated,
        reference_benchmark=reference_benchmark,
        generated_benchmark=generated_benchmark,
    )
