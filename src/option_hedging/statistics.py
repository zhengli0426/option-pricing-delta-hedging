"""Statistical summaries used by the reproducible study pipeline."""

from __future__ import annotations

from typing import Iterable

import numpy as np
from scipy.stats import spearmanr, t


def _paired_vectors(
    x: Iterable[float], y: Iterable[float], *, minimum: int
) -> tuple[np.ndarray, np.ndarray]:
    x_array = np.asarray(list(x), dtype=float)
    y_array = np.asarray(list(y), dtype=float)
    if x_array.ndim != 1 or y_array.ndim != 1:
        raise ValueError("Observations must be one-dimensional.")
    if x_array.size != y_array.size or x_array.size < minimum:
        raise ValueError(f"At least {minimum} paired observations are required.")
    if not (np.all(np.isfinite(x_array)) and np.all(np.isfinite(y_array))):
        raise ValueError("Observations must be finite; no rows are silently removed.")
    if np.ptp(x_array) == 0 or np.ptp(y_array) == 0:
        raise ValueError("Both variables must have positive variation.")
    return x_array, y_array


def log_log_convergence(
    sample_sizes: Iterable[float], errors: Iterable[float]
) -> dict[str, float | int]:
    """Fit log(error) = intercept + slope * log(N), with a 95% t interval."""
    n_values, error_values = _paired_vectors(sample_sizes, errors, minimum=3)
    if np.any(n_values <= 0) or np.any(error_values <= 0):
        raise ValueError("Sample sizes and errors must be strictly positive.")
    x, y = np.log(n_values), np.log(error_values)
    x_centered, y_centered = x - x.mean(), y - y.mean()
    sxx = float(x_centered @ x_centered)
    slope = float((x_centered @ y_centered) / sxx)
    residuals = y_centered - slope * x_centered
    sse = float(residuals @ residuals)
    degrees_of_freedom = x.size - 2
    standard_error = float(np.sqrt(sse / degrees_of_freedom / sxx))
    margin = float(t.ppf(0.975, degrees_of_freedom)) * standard_error
    r_squared = 1.0 - sse / float(y_centered @ y_centered)
    return {
        "slope": slope,
        "standard_error": standard_error,
        "ci_low": slope - margin,
        "ci_high": slope + margin,
        "r_squared": r_squared,
        "n_points": int(x.size),
    }


def bootstrap_correlation(
    exposure: Iterable[float],
    rmse: Iterable[float],
    *,
    bootstrap_resamples: int = 200_000,
    seed: int = 20260923,
    batch_size: int = 10_000,
) -> dict[str, float | int]:
    """Pearson/Spearman association with a paired percentile-bootstrap interval."""
    x, y = _paired_vectors(exposure, rmse, minimum=2)
    for name, value in (("bootstrap_resamples", bootstrap_resamples), ("batch_size", batch_size)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value <= 0:
            raise ValueError(f"{name} must be a positive integer.")
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")

    generator = np.random.default_rng(seed)
    correlations = np.empty(bootstrap_resamples, dtype=float)
    valid_count = 0
    for start in range(0, bootstrap_resamples, batch_size):
        size = min(batch_size, bootstrap_resamples - start)
        indices = generator.integers(0, x.size, size=(size, x.size))
        sampled_x, sampled_y = x[indices], y[indices]
        valid = (np.ptp(sampled_x, axis=1) > 0) & (np.ptp(sampled_y, axis=1) > 0)
        centered_x = sampled_x[valid] - sampled_x[valid].mean(axis=1, keepdims=True)
        centered_y = sampled_y[valid] - sampled_y[valid].mean(axis=1, keepdims=True)
        numerator = np.sum(centered_x * centered_y, axis=1)
        denominator = np.sqrt(np.sum(centered_x**2, axis=1) * np.sum(centered_y**2, axis=1))
        batch_correlations = np.clip(numerator / denominator, -1.0, 1.0)
        end = valid_count + batch_correlations.size
        correlations[valid_count:end] = batch_correlations
        valid_count = end

    if valid_count == 0:
        raise ValueError("Every bootstrap resample was degenerate; no interval can be estimated.")
    ci_low, ci_high = np.quantile(correlations[:valid_count], [0.025, 0.975], method="linear")
    return {
        "pearson": float(np.corrcoef(x, y)[0, 1]),
        "spearman": float(spearmanr(x, y).statistic),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "n_scenarios": int(x.size),
        "bootstrap_resamples": int(bootstrap_resamples),
        "valid_resamples": int(valid_count),
        "excluded_resamples": int(bootstrap_resamples - valid_count),
        "seed": int(seed),
    }
