"""Discrete Black--Scholes delta hedging used by the reproducible study."""

from dataclasses import dataclass

import numpy as np

from .models import _positive_integer, _scalar_inputs, black_scholes_call, call_delta, call_gamma


@dataclass(frozen=True)
class HedgeResult:
    """Pathwise terminal hedge errors, integrated Gamma proxy, and paid costs.

    Costs are summed in nominal dollars at their transaction dates. Errors are
    measured in terminal dollars, so they include the financing effect of costs.
    """

    errors: np.ndarray
    gamma_exposure: np.ndarray
    total_costs: np.ndarray

    def summary(self):
        """Return mean error, sample SD, RMSE, mean exposure and nominal cost."""
        return {
            "mean_error": float(np.mean(self.errors)),
            "std": float(np.std(self.errors, ddof=1)),
            "rmse": float(np.sqrt(np.mean(self.errors**2))),
            "mean_gamma_exposure": float(np.mean(self.gamma_exposure)),
            "mean_cost": float(np.mean(self.total_costs)),
        }


def simulate_hedge(
    spot=100,
    strike=100,
    maturity=1,
    rate=0.03,
    volatility=0.2,
    steps=52,
    paths=5000,
    cost_rate=0,
    seed=20260925,
    initial_cost=False,
):
    """Simulate a long replicating portfolio against a short European call.

    The option premium funds Delta shares plus cash at time zero. Cash accrues
    at ``rate``, and stock follows exact risk-neutral GBM transitions. At each
    internal grid date the shares are reset to analytical Delta; the charge
    is ``cost_rate * abs(change_in_delta) * spot`` and is paid from cash.

    By default, the initial stock purchase is not charged, and there is no
    terminal rebalance or stock liquidation. ``initial_cost=True`` adds the
    initial purchase charge. Terminal error is stock value plus cash minus
    the option payoff. The strategy and initial premium are not adjusted for
    costs; this is a comparison of fixed-grid Delta hedging policies, not a
    transaction-cost-optimal policy.

    Gamma exposure uses the left-point sum
    ``0.5 * sum(abs(Gamma) * S**2 * volatility**2 * dt)``. It is a descriptive
    convexity-exposure proxy, not an estimator of causal effects or exact
    hedge-error variance. ``steps`` is the number of time intervals, with
    ``steps - 1`` internal rebalancing opportunities.
    """
    s, k, t, r, sigma = _scalar_inputs(spot, strike, maturity, rate, volatility)
    n = _positive_integer(steps, "steps")
    count = _positive_integer(paths, "paths", minimum=2)
    if not np.isscalar(cost_rate):
        raise ValueError("cost_rate must be a finite nonnegative scalar")
    try:
        cost_rate = float(cost_rate)
    except (TypeError, ValueError) as exc:
        raise ValueError("cost_rate must be a finite nonnegative scalar") from exc
    if not np.isfinite(cost_rate) or cost_rate < 0:
        raise ValueError("cost_rate must be a finite nonnegative scalar")
    if not isinstance(initial_cost, (bool, np.bool_)):
        raise ValueError("initial_cost must be a boolean")
    stock = np.full(count, s, dtype=float)
    delta = np.full(count, call_delta(s, k, t, r, sigma), dtype=float)
    cash = np.full(count, black_scholes_call(s, k, t, r, sigma), dtype=float) - delta * stock
    total_costs = np.zeros(count)
    exposure = np.zeros(count)
    if initial_cost:
        total_costs += cost_rate * np.abs(delta) * stock
        cash -= total_costs

    dt = t / n
    growth = np.exp(r * dt)
    rng = np.random.default_rng(seed)
    for index in range(n):
        remaining = t * (n - index) / n
        gamma = call_gamma(stock, k, remaining, r, sigma)
        exposure += 0.5 * np.abs(gamma) * stock**2 * sigma**2 * dt
        cash *= growth
        stock *= np.exp((r - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * rng.standard_normal(count))
        if index < n - 1:
            next_remaining = t * (n - index - 1) / n
            next_delta = call_delta(stock, k, next_remaining, r, sigma)
            trade = next_delta - delta
            charge = cost_rate * np.abs(trade) * stock
            cash -= trade * stock + charge
            total_costs += charge
            delta = next_delta

    errors = delta * stock + cash - np.maximum(stock - k, 0.0)
    return HedgeResult(errors=errors, gamma_exposure=exposure, total_costs=total_costs)
