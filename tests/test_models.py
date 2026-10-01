"""Financial identities and boundary checks for pricing and Greeks."""

import numpy as np
import pytest

from option_hedging.models import (
    black_scholes_call,
    call_delta,
    call_gamma,
    call_theta,
    call_vega,
    crr_call,
    monte_carlo_call,
)


def test_black_scholes_known_benchmark():
    args = (100, 100, 1, 0.05, 0.2)
    assert black_scholes_call(*args) == pytest.approx(10.450583572185565)
    assert call_delta(*args) == pytest.approx(0.6368306511756191)
    assert call_gamma(*args) == pytest.approx(0.018762017345846895)


def test_greeks_match_finite_differences():
    spot, h = 103.0, 0.01
    strike, maturity, rate, vol = 100, 0.6, 0.03, 0.24
    lower = black_scholes_call(spot - h, strike, maturity, rate, vol)
    base = black_scholes_call(spot, strike, maturity, rate, vol)
    upper = black_scholes_call(spot + h, strike, maturity, rate, vol)
    assert (upper - lower) / (2 * h) == pytest.approx(call_delta(spot, strike, maturity, rate, vol), rel=1e-6)
    assert (upper - 2 * base + lower) / h**2 == pytest.approx(call_gamma(spot, strike, maturity, rate, vol), rel=1e-6)

    hv = 1e-5
    dv = (black_scholes_call(spot, strike, maturity, rate, vol + hv) - black_scholes_call(spot, strike, maturity, rate, vol - hv)) / (2 * hv)
    assert dv == pytest.approx(call_vega(spot, strike, maturity, rate, vol), rel=1e-7)

    ht = 1e-5
    d_remaining = (black_scholes_call(spot, strike, maturity + ht, rate, vol) - black_scholes_call(spot, strike, maturity - ht, rate, vol)) / (2 * ht)
    assert -d_remaining == pytest.approx(call_theta(spot, strike, maturity, rate, vol), rel=1e-6)


def test_vectorization_and_call_bounds():
    spots = np.array([0, 80, 100, 120])[:, None]
    maturities = np.array([0.1, 1.0, 2.0])
    prices = black_scholes_call(spots, 100, maturities, -0.01, 0.2)
    assert prices.shape == (4, 3)
    assert np.all(prices >= np.maximum(spots - 100 * np.exp(0.01 * maturities), 0) - 1e-12)
    assert np.all(prices <= spots)
    assert np.all(call_gamma(spots, 100, maturities, -0.01, 0.2) >= 0)


def test_expiry_and_zero_volatility_conventions():
    spots = np.array([90, 100, 110])
    np.testing.assert_array_equal(black_scholes_call(spots, 100, 0, 0.03, 0.2), [0, 0, 10])
    np.testing.assert_array_equal(call_delta(spots, 100, 0, 0.03, 0.2), [0, 0.5, 1])
    np.testing.assert_array_equal(call_gamma(spots, 100, 0, 0.03, 0.2), [0, 0, 0])
    np.testing.assert_array_equal(call_vega(spots, 100, 0, 0.03, 0.2), [0, 0, 0])
    np.testing.assert_array_equal(call_theta(spots, 100, 0, 0.03, 0.2), [0, 0, 0])


def test_crr_convergence_and_no_arbitrage_guard():
    args = (100, 100, 1, 0.05, 0.2)
    exact = black_scholes_call(*args)
    coarse = abs(crr_call(*args, steps=32) - exact)
    fine = abs(crr_call(*args, steps=512) - exact)
    assert fine < coarse / 8
    with pytest.raises(ValueError, match="no-arbitrage"):
        crr_call(100, 100, 1, 0.3, 0.01, steps=1)


def test_monte_carlo_seed_and_standard_error():
    args = (100, 100, 1, 0.03, 0.2)
    result = monte_carlo_call(*args, paths=50_000, seed=812)
    assert result == monte_carlo_call(*args, paths=50_000, seed=812)
    assert result != monte_carlo_call(*args, paths=50_000, seed=813)
    assert result.standard_error > 0
