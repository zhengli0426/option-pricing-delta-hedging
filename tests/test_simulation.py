"""Check replication accounting, sampling reproducibility and cost conventions."""

import numpy as np
import pytest

from option_hedging.models import black_scholes_call, call_delta
from option_hedging.simulation import simulate_hedge


def test_seed_reproducibility_and_summary():
    first = simulate_hedge(steps=12, paths=500, seed=4)
    second = simulate_hedge(steps=12, paths=500, seed=4)
    np.testing.assert_array_equal(first.errors, second.errors)
    np.testing.assert_array_equal(first.gamma_exposure, second.gamma_exposure)
    assert np.all(first.gamma_exposure > 0)
    assert np.all(first.total_costs == 0)
    stats = first.summary()
    assert stats["rmse"] == pytest.approx(np.sqrt(np.mean(first.errors**2)))
    assert stats["std"] == pytest.approx(np.std(first.errors, ddof=1))
    assert set(stats) == {"mean_error", "std", "rmse", "mean_gamma_exposure", "mean_cost"}


def test_one_interval_matches_direct_stock_cash_accounting():
    s, k, t, r, sigma = 100, 100, 1, 0.03, 0.2
    count, seed = 200, 91
    terminal = s * np.exp((r - sigma**2 / 2) * t + sigma * np.sqrt(t) * np.random.default_rng(seed).standard_normal(count))
    delta = call_delta(s, k, t, r, sigma)
    expected = delta * terminal + (black_scholes_call(s, k, t, r, sigma) - delta * s) * np.exp(r * t) - np.maximum(terminal - k, 0)
    result = simulate_hedge(spot=s, strike=k, maturity=t, rate=r, volatility=sigma, steps=1, paths=count, seed=seed, cost_rate=0.1)
    np.testing.assert_allclose(result.errors, expected, atol=1e-12)
    # With no internal rebalance and no initial/terminal charge, costs are zero.
    np.testing.assert_array_equal(result.total_costs, np.zeros(count))


def test_costs_reduce_same_path_terminal_wealth():
    settings = dict(steps=26, paths=1000, seed=81, rate=0)
    free = simulate_hedge(**settings)
    charged = simulate_hedge(**settings, cost_rate=0.001)
    np.testing.assert_array_equal(free.gamma_exposure, charged.gamma_exposure)
    assert np.all(charged.errors <= free.errors + 1e-12)
    assert np.all(charged.total_costs >= 0)
    np.testing.assert_allclose(free.errors - charged.errors, charged.total_costs, atol=1e-11)


def test_initial_charge_includes_financing_until_maturity():
    settings = dict(steps=8, paths=500, seed=9, rate=0.03, cost_rate=0.001)
    without = simulate_hedge(**settings)
    with_initial = simulate_hedge(**settings, initial_cost=True)
    initial = 0.001 * call_delta(100, 100, 1, 0.03, 0.2) * 100
    np.testing.assert_allclose(without.errors - with_initial.errors, initial * np.exp(0.03), atol=1e-11)
    np.testing.assert_allclose(with_initial.total_costs - without.total_costs, initial, atol=1e-12)


def test_deterministic_asset_is_replicated():
    result = simulate_hedge(spot=120, volatility=0, steps=24, paths=20)
    np.testing.assert_allclose(result.errors, 0, atol=1e-10)
    np.testing.assert_array_equal(result.gamma_exposure, np.zeros(20))
    zero_spot = simulate_hedge(spot=0, paths=20, steps=3)
    np.testing.assert_array_equal(zero_spot.errors, np.zeros(20))


def test_finer_frictionless_hedging_reduces_sampling_rmse():
    # Aggregate comparison with fixed seeds, not a claim of pathwise monotonicity.
    coarse = simulate_hedge(steps=12, paths=4000, seed=12).summary()
    fine = simulate_hedge(steps=192, paths=4000, seed=12).summary()
    assert fine["rmse"] < 0.45 * coarse["rmse"]
    assert abs(fine["mean_error"]) < 4 * fine["std"] / np.sqrt(4000)


@pytest.mark.parametrize("setting", [{"steps": 0}, {"paths": 1}, {"cost_rate": -0.1}, {"cost_rate": np.nan}, {"initial_cost": "yes"}])
def test_invalid_simulation_settings(setting):
    with pytest.raises(ValueError):
        simulate_hedge(**setting)
