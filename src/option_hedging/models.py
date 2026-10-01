"""European-call pricing and Greeks under the no-dividend Black--Scholes model."""

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr


def _inputs(spot, strike, maturity, rate, volatility):
    """Validate and broadcast model inputs without mutating caller arrays."""
    try:
        values = np.broadcast_arrays(
            *[np.asarray(v, dtype=float) for v in (spot, strike, maturity, rate, volatility)]
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("model inputs must be numeric and broadcast-compatible") from exc
    names = ("spot", "strike", "maturity", "rate", "volatility")
    for name, value in zip(names, values):
        if not np.all(np.isfinite(value)):
            raise ValueError(f"{name} must be finite")
    if np.any(values[0] < 0):
        raise ValueError("spot must be nonnegative")
    if np.any(values[1] <= 0):
        raise ValueError("strike must be positive")
    if np.any(values[2] < 0):
        raise ValueError("maturity must be nonnegative")
    if np.any(values[4] < 0):
        raise ValueError("volatility must be nonnegative")
    return values


def _scalar_inputs(spot, strike, maturity, rate, volatility):
    values = _inputs(spot, strike, maturity, rate, volatility)
    if any(value.ndim != 0 for value in values):
        raise ValueError("this function requires scalar model inputs")
    return tuple(float(value) for value in values)


def _positive_integer(value, name, minimum=1):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    if value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _result(value):
    return float(value) if value.ndim == 0 else value


def black_scholes_call(spot, strike, maturity, rate, volatility):
    """Return the call value; scalars return float, arrays broadcast naturally.

    Rates are continuously compounded and there are no dividends. Maturity and
    volatility may be zero; spot may be zero. Strike must be strictly positive.
    """
    s, k, t, r, sigma = _inputs(spot, strike, maturity, rate, volatility)
    discounted_strike = k * np.exp(-r * t)
    value = np.asarray(np.maximum(s - discounted_strike, 0.0))
    regular = (s > 0) & (t > 0) & (sigma > 0)
    if np.any(regular):
        st = sigma[regular] * np.sqrt(t[regular])
        d1 = (np.log(s[regular] / k[regular]) + r[regular] * t[regular]) / st + st / 2
        value = value.copy()
        value[regular] = s[regular] * ndtr(d1) - discounted_strike[regular] * ndtr(d1 - st)
    return _result(value)


def call_delta(spot, strike, maturity, rate, volatility):
    """Return call Delta, with 0.5 chosen at a deterministic payoff kink.

    Delta is not mathematically defined at that kink. The 0.5 convention applies
    both at expiration and when volatility is zero; it is an implementation
    convention, not a claim of differentiability.
    """
    s, k, t, r, sigma = _inputs(spot, strike, maturity, rate, volatility)
    discounted_strike = k * np.exp(-r * t)
    delta = np.where(s > discounted_strike, 1.0, np.where(s < discounted_strike, 0.0, 0.5))
    regular = (s > 0) & (t > 0) & (sigma > 0)
    if np.any(regular):
        st = sigma[regular] * np.sqrt(t[regular])
        d1 = (np.log(s[regular] / k[regular]) + r[regular] * t[regular]) / st + st / 2
        delta[regular] = ndtr(d1)
    return _result(delta)


def call_vega(spot, strike, maturity, rate, volatility):
    """Return Black--Scholes call Vega per unit change in volatility.

    Vega is zero at deterministic endpoints used by this implementation.
    """
    s, k, t, r, sigma = _inputs(spot, strike, maturity, rate, volatility)
    vega = np.zeros_like(s)
    regular = (s > 0) & (t > 0) & (sigma > 0)
    if np.any(regular):
        st = sigma[regular] * np.sqrt(t[regular])
        d1 = (np.log(s[regular] / k[regular]) + r[regular] * t[regular]) / st + st / 2
        vega[regular] = s[regular] * np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi) * np.sqrt(t[regular])
    return _result(vega)


def call_theta(spot, strike, maturity, rate, volatility):
    """Return Black--Scholes call Theta per year (calendar-time decay).

    The classical formula is used for positive spot, maturity and volatility.
    Deterministic endpoints return zero because the derivative is not used in
    the study at those boundaries.
    """
    s, k, t, r, sigma = _inputs(spot, strike, maturity, rate, volatility)
    theta = np.zeros_like(s)
    regular = (s > 0) & (t > 0) & (sigma > 0)
    if np.any(regular):
        sqrt_t = np.sqrt(t[regular])
        st = sigma[regular] * sqrt_t
        d1 = (np.log(s[regular] / k[regular]) + r[regular] * t[regular]) / st + st / 2
        d2 = d1 - st
        density = np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)
        theta[regular] = (
            -s[regular] * density * sigma[regular] / (2 * sqrt_t)
            - r[regular] * k[regular] * np.exp(-r[regular] * t[regular]) * ndtr(d2)
        )
    return _result(theta)


def call_gamma(spot, strike, maturity, rate, volatility):
    """Return call Gamma, with zero used at expiry/zero volatility/zero spot.

    At a deterministic payoff kink the classical second derivative does not
    exist. The returned zero is a finite endpoint convention for computation.
    """
    s, k, t, r, sigma = _inputs(spot, strike, maturity, rate, volatility)
    gamma = np.zeros_like(s)
    regular = (s > 0) & (t > 0) & (sigma > 0)
    if np.any(regular):
        st = sigma[regular] * np.sqrt(t[regular])
        d1 = (np.log(s[regular] / k[regular]) + r[regular] * t[regular]) / st + st / 2
        gamma[regular] = np.exp(-0.5 * d1**2) / (np.sqrt(2 * np.pi) * s[regular] * st)
    return _result(gamma)


def crr_call(spot, strike, maturity, rate, volatility, steps):
    """Price a European call by Cox--Ross--Rubinstein backward induction.

    Requires ``d < exp(rate * dt) < u`` for a nondegenerate tree. Increase the
    number of steps if the one-step risk-neutral probability is inadmissible.
    Zero maturity, zero volatility and zero spot use their exact limiting value.
    Runtime is O(steps**2), with O(steps) working memory.
    """
    s, k, t, r, sigma = _scalar_inputs(spot, strike, maturity, rate, volatility)
    n = _positive_integer(steps, "steps")
    if t == 0 or sigma == 0 or s == 0:
        return black_scholes_call(s, k, t, r, sigma)
    dt = t / n
    log_up = sigma * np.sqrt(dt)
    up, down = np.exp(log_up), np.exp(-log_up)
    growth = np.exp(r * dt)
    if not down < growth < up:
        raise ValueError("CRR no-arbitrage condition failed; increase steps")
    probability = (growth - down) / (up - down)
    terminal_spot = s * np.exp((2 * np.arange(n + 1) - n) * log_up)
    values = np.maximum(terminal_spot - k, 0.0)
    discount = np.exp(-r * dt)
    for size in range(n, 0, -1):
        values = discount * ((1 - probability) * values[:size] + probability * values[1 : size + 1])
    return float(values[0])


@dataclass(frozen=True)
class MonteCarloEstimate:
    """Plain Monte Carlo estimate and normal-approximation 95% interval."""

    price: float
    standard_error: float
    confidence_interval: tuple[float, float]
    paths: int
    seed: int | None


def monte_carlo_call(spot, strike, maturity, rate, volatility, paths, seed):
    """Price a call from independent exact-GBM terminal samples.

    Standard error uses the sample variance (ddof=1). The interval is
    ``price +/- 1.9599639845 * standard_error`` and is asymptotic, not exact.
    At least two paths are required. A fixed seed yields reproducible results
    for a fixed NumPy random-generator implementation.
    """
    s, k, t, r, sigma = _scalar_inputs(spot, strike, maturity, rate, volatility)
    count = _positive_integer(paths, "paths", minimum=2)
    if t == 0 or sigma == 0 or s == 0:
        price = black_scholes_call(s, k, t, r, sigma)
        return MonteCarloEstimate(price, 0.0, (price, price), count, seed)
    rng = np.random.default_rng(seed)
    terminal_spot = s * np.exp((r - 0.5 * sigma**2) * t + sigma * np.sqrt(t) * rng.standard_normal(count))
    payoffs = np.exp(-r * t) * np.maximum(terminal_spot - k, 0.0)
    price = float(np.mean(payoffs))
    standard_error = float(np.std(payoffs, ddof=1) / np.sqrt(count))
    radius = 1.959963984540054 * standard_error
    return MonteCarloEstimate(price, standard_error, (price - radius, price + radius), count, seed)
