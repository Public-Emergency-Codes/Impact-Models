"""Shared probability utilities for the prospective PEC planning models."""

from __future__ import annotations

from typing import Iterable

import numpy as np
from scipy.special import expit, logit, ndtr, ndtri
from scipy.stats import beta as beta_distribution
from scipy.stats import t as student_t_distribution


def summarize(values: np.ndarray) -> dict[str, float]:
    q = np.quantile(values, [0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975])
    return {
        "mean": float(np.mean(values)),
        "p2.5": float(q[0]),
        "p5": float(q[1]),
        "p25": float(q[2]),
        "median": float(q[3]),
        "p75": float(q[4]),
        "p95": float(q[5]),
        "p97.5": float(q[6]),
        "probability_positive": float(np.mean(values > 0.0)),
        "probability_zero": float(np.mean(values == 0.0)),
    }


def pert_parameters(values: Iterable[float], shape: float) -> tuple[float, float]:
    low, mode, high = (float(v) for v in values)
    if low == high:
        return 1.0, 1.0
    alpha = 1.0 + shape * (mode - low) / (high - low)
    beta = 1.0 + shape * (high - mode) / (high - low)
    return alpha, beta


def pert_moments(
    values: Iterable[float], shape: float
) -> tuple[float, float]:
    """Return mean and standard deviation of the scaled beta-PERT law."""

    low, mode, high = (float(v) for v in values)
    if low == high:
        return low, 0.0
    alpha, beta = pert_parameters((low, mode, high), shape)
    span = high - low
    mean = low + span * alpha / (alpha + beta)
    variance = (
        span**2
        * alpha
        * beta
        / ((alpha + beta) ** 2 * (alpha + beta + 1.0))
    )
    return mean, float(np.sqrt(variance))


def _approximately_match_pert_moments(
    values: np.ndarray,
    low: float,
    mode: float,
    high: float,
    shape: float,
) -> np.ndarray:
    """Monotonically standardize and clip an alternative to PERT moments."""

    target_mean, target_sd = pert_moments((low, mode, high), shape)
    if target_sd == 0.0:
        return np.full_like(values, target_mean)
    matched = np.asarray(values, dtype=float)
    for _ in range(12):
        current_sd = float(np.std(matched))
        if current_sd <= 1e-15:
            break
        matched = target_mean + (matched - float(np.mean(matched))) * (
            target_sd / current_sd
        )
        matched = np.clip(matched, low, high)
    return matched


def _triangular_from_uniform(
    uniforms: np.ndarray,
    low: float,
    mode: float,
    high: float,
) -> np.ndarray:
    if low == high:
        return np.full_like(uniforms, low, dtype=float)
    split = (mode - low) / (high - low)
    lower = low + np.sqrt(uniforms * (high - low) * (mode - low))
    upper = high - np.sqrt((1.0 - uniforms) * (high - low) * (high - mode))
    return np.where(uniforms < split, lower, upper)


def draw_bounded(
    rng: np.random.Generator,
    values: Iterable[float],
    size: int,
    shape: float = 8.0,
    form: str = "pert",
    uniforms: np.ndarray | None = None,
) -> np.ndarray:
    """Draw a bounded low/mode/high distribution under several forms.

    ``logit_normal`` is used only for values wholly inside [0, 1].  For other
    scales it becomes a bounded normal sensitivity.  The bounds remain hard.
    """

    low, mode, high = (float(v) for v in values)
    if low == high:
        return np.full(size, low, dtype=float)
    moment_match = form.endswith("_moment_matched")
    base_form = form.removesuffix("_moment_matched")
    u = rng.random(size) if uniforms is None else np.asarray(uniforms)
    u = np.clip(u, 1e-12, 1.0 - 1e-12)
    if base_form == "pert":
        alpha, beta = pert_parameters((low, mode, high), shape)
        result = low + (high - low) * beta_distribution.ppf(u, alpha, beta)
    elif base_form == "triangular":
        result = _triangular_from_uniform(u, low, mode, high)
    elif base_form == "uniform":
        result = low + (high - low) * u
    elif base_form == "logit_normal":
        z = ndtri(u)
        if 0.0 <= low < high <= 1.0:
            eps = 1e-6
            lo = logit(np.clip(low, eps, 1.0 - eps))
            hi = logit(np.clip(high, eps, 1.0 - eps))
            center = logit(np.clip(mode, eps, 1.0 - eps))
            scale = max((hi - lo) / (2.0 * 1.6448536269514722), 1e-9)
            result = np.clip(expit(center + scale * z), low, high)
        else:
            scale = max((high - low) / (2.0 * 1.6448536269514722), 1e-9)
            result = np.clip(mode + scale * z, low, high)
    else:
        raise ValueError(f"unknown distribution form: {form}")
    if moment_match and base_form != "pert":
        return _approximately_match_pert_moments(
            result, low, mode, high, shape
        )
    return result


def gaussian_copula_uniforms(
    rng: np.random.Generator,
    draws: int,
    dimensions: int,
    rho: float,
) -> np.ndarray:
    """Equicorrelated Gaussian-copula uniforms for dependence sensitivity."""

    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must lie in [0, 1)")
    common = rng.standard_normal((draws, 1))
    independent = rng.standard_normal((draws, dimensions))
    normals = np.sqrt(rho) * common + np.sqrt(1.0 - rho) * independent
    return ndtr(normals)


def t_copula_uniforms(
    rng: np.random.Generator,
    draws: int,
    dimensions: int,
    rho: float,
    degrees_of_freedom: int = 4,
) -> np.ndarray:
    """Equicorrelated Student-t copula uniforms for tail-dependence sensitivity."""

    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must lie in [0, 1)")
    common = rng.standard_normal((draws, 1))
    independent = rng.standard_normal((draws, dimensions))
    correlated_normal = (
        np.sqrt(rho) * common + np.sqrt(1.0 - rho) * independent
    )
    scale = np.sqrt(
        rng.chisquare(degrees_of_freedom, (draws, 1)) / degrees_of_freedom
    )
    t_values = correlated_normal / scale
    return student_t_distribution.cdf(t_values, df=degrees_of_freedom)


def spike_slab(
    rng: np.random.Generator,
    nonzero_probability: np.ndarray,
    slab: np.ndarray,
    uniforms: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    u = rng.random(len(slab)) if uniforms is None else uniforms
    active = u < np.clip(nonzero_probability, 0.0, 1.0)
    return active.astype(float) * slab, active


def exclusive_outcome_counts(
    rng: np.random.Generator,
    affected_count: np.ndarray,
    benefit_probability: np.ndarray,
    harm_probability: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if np.any(benefit_probability < 0.0) or np.any(harm_probability < 0.0):
        raise AssertionError("negative outcome probability")
    if np.any(benefit_probability + harm_probability > 1.0 + 1e-12):
        raise AssertionError("benefit and harm probabilities exceed one")
    beneficial = rng.binomial(affected_count, benefit_probability)
    remaining = affected_count - beneficial
    conditional_harm = np.divide(
        harm_probability,
        1.0 - benefit_probability,
        out=np.zeros_like(harm_probability),
        where=benefit_probability < 1.0,
    )
    adverse = rng.binomial(remaining, np.clip(conditional_harm, 0.0, 1.0))
    return beneficial, adverse


def categorical_cpr_gain(
    category_weights: Iterable[float],
    survival_rates: Iterable[float],
    minutes_recovered: np.ndarray,
) -> np.ndarray:
    """Expected absolute survival gain from moving one 2-minute category earlier.

    The transition probability is minutes_recovered / 2, capped at one.  This
    preserves the published categories and absolute risks rather than fitting a
    constant per-minute log-odds coefficient.
    """

    weights = np.asarray(tuple(category_weights), dtype=float)
    survival = np.asarray(tuple(survival_rates), dtype=float)
    if len(weights) != len(survival) or not np.isclose(weights.sum(), 1.0):
        raise ValueError("CPR category weights and survival rates are invalid")
    adjacent_gain = survival[:-1] - survival[1:]
    expected_full_category_gain = float(np.sum(weights[1:] * adjacent_gain))
    transition_probability = np.clip(minutes_recovered / 2.0, 0.0, 1.0)
    return transition_probability * expected_full_category_gain