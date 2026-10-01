"""Tests for convergence regression and paired-bootstrap correlation."""

import json
import numpy as np
import pytest

from option_hedging.statistics import bootstrap_correlation, log_log_convergence


def test_exact_power_law():
    sample_sizes = np.array([10.0, 100.0, 1000.0, 10000.0])
    result = log_log_convergence(sample_sizes, 3 * sample_sizes**-0.5)
    assert result["slope"] == pytest.approx(-0.5, abs=1e-13)
    assert result["r_squared"] == pytest.approx(1.0, abs=1e-13)
    assert result["standard_error"] < 1e-14
    assert result["n_points"] == 4


def test_paired_sampling_and_exclusion_are_explicit():
    result = bootstrap_correlation([1, 2], [3, 7], bootstrap_resamples=1000, seed=17)
    assert result["ci_low"] == pytest.approx(1.0)
    assert result["ci_high"] == pytest.approx(1.0)
    indices = np.random.default_rng(17).integers(0, 2, size=(1000, 2))
    independently_counted = int(np.sum(indices[:, 0] != indices[:, 1]))
    assert result["valid_resamples"] == independently_counted
    assert result["excluded_resamples"] > 0
    json.dumps(result, allow_nan=False)


def test_batch_size_does_not_change_random_draws():
    arguments = ([1, 2, 4, 9], [5, 3, 2, 7])
    result = bootstrap_correlation(*arguments, bootstrap_resamples=1031, seed=3, batch_size=100)
    other = bootstrap_correlation(*arguments, bootstrap_resamples=1031, seed=3, batch_size=1031)
    assert result == other


@pytest.mark.parametrize(
    "x,y",
    [([1, 2, 3], [1, 2]), ([1, 2, 3], [1, np.nan, 2]), ([1, 1, 1], [1, 2, 3])],
)
def test_invalid_observations_are_not_silently_dropped(x, y):
    with pytest.raises(ValueError):
        log_log_convergence(x, y)
