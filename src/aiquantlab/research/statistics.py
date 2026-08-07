"""Deterministic statistical summaries for event-study outcomes."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from aiquantlab.research.event_study import EventStudyResult
from aiquantlab.research.models import (
    BootstrapMethod,
    DistributionSummary,
    ExpectedDirection,
    ExperimentConfig,
    HorizonStatistics,
    StatisticalReport,
    StatisticalSpecification,
)


def summarize_distribution(values: pd.Series | NDArray[np.float64]) -> DistributionSummary:
    numeric = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
    clean = numeric[np.isfinite(numeric)]
    if len(clean) == 0:
        return DistributionSummary(count=0)
    standard_deviation = float(np.std(clean, ddof=1)) if len(clean) > 1 else None
    return DistributionSummary(
        count=len(clean),
        mean=float(np.mean(clean)),
        median=float(np.median(clean)),
        standard_deviation=standard_deviation,
        minimum=float(np.min(clean)),
        maximum=float(np.max(clean)),
        quantile_05=float(np.quantile(clean, 0.05)),
        quantile_25=float(np.quantile(clean, 0.25)),
        quantile_75=float(np.quantile(clean, 0.75)),
        quantile_95=float(np.quantile(clean, 0.95)),
        positive_probability=float(np.mean(clean > 0)),
    )


def _bootstrap_means(
    values: NDArray[np.float64],
    specification: StatisticalSpecification,
    rng: np.random.Generator,
) -> NDArray[np.float64]:
    sample_count = len(values)
    if specification.bootstrap_method == BootstrapMethod.IID:
        indices = rng.integers(
            0,
            sample_count,
            size=(specification.bootstrap_samples, sample_count),
        )
        return np.asarray(values[indices].mean(axis=1), dtype=np.float64)

    block_size = min(specification.block_size, sample_count)
    block_count = int(np.ceil(sample_count / block_size))
    starts = rng.integers(
        0,
        sample_count,
        size=(specification.bootstrap_samples, block_count),
    )
    offsets = np.arange(block_size)
    indices = (starts[:, :, None] + offsets[None, None, :]) % sample_count
    samples = values[indices.reshape(specification.bootstrap_samples, -1)[:, :sample_count]]
    return np.asarray(samples.mean(axis=1), dtype=np.float64)


def _bootstrap_inference(
    event_values: NDArray[np.float64],
    baseline_mean: float,
    *,
    expected_direction: ExpectedDirection,
    specification: StatisticalSpecification,
    rng: np.random.Generator,
) -> tuple[tuple[float, float], float]:
    bootstrap_means = _bootstrap_means(event_values, specification, rng)
    alpha = 1.0 - specification.confidence_level
    interval = (
        float(np.quantile(bootstrap_means - baseline_mean, alpha / 2.0)),
        float(np.quantile(bootstrap_means - baseline_mean, 1.0 - alpha / 2.0)),
    )

    observed_effect = float(np.mean(event_values) - baseline_mean)
    null_values = event_values - np.mean(event_values) + baseline_mean
    null_means = _bootstrap_means(null_values, specification, rng)
    null_effects = null_means - baseline_mean
    if expected_direction == ExpectedDirection.POSITIVE:
        exceedances = np.count_nonzero(null_effects >= observed_effect)
    elif expected_direction == ExpectedDirection.NEGATIVE:
        exceedances = np.count_nonzero(null_effects <= observed_effect)
    else:
        exceedances = np.count_nonzero(np.abs(null_effects) >= abs(observed_effect))
    p_value = float((exceedances + 1) / (specification.bootstrap_samples + 1))
    return interval, p_value


def benjamini_hochberg(p_values: list[float | None]) -> list[float | None]:
    """Control false discovery rate across the tested forward horizons."""

    valid = [(index, value) for index, value in enumerate(p_values) if value is not None]
    if not valid:
        return [None] * len(p_values)
    ordered = sorted(valid, key=lambda item: item[1])
    adjusted_by_index: dict[int, float] = {}
    running_minimum = 1.0
    test_count = len(ordered)
    for reverse_rank, (index, value) in enumerate(reversed(ordered), start=1):
        rank = test_count - reverse_rank + 1
        candidate = min(1.0, value * test_count / rank)
        running_minimum = min(running_minimum, candidate)
        adjusted_by_index[index] = running_minimum
    return [adjusted_by_index.get(index) for index in range(len(p_values))]


def build_statistical_report(
    result: EventStudyResult,
    config: ExperimentConfig,
) -> StatisticalReport:
    """Summarize event outcomes without automatically accepting the hypothesis."""

    rng = np.random.default_rng(config.statistics.random_seed)
    horizon_results: list[HorizonStatistics] = []
    p_values: list[float | None] = []

    for horizon in config.event_study.horizons_bars:
        event_rows = result.observations.loc[result.observations["horizon_bars"] == horizon]
        baseline_rows = result.baseline.loc[result.baseline["horizon_bars"] == horizon]
        event_summary = summarize_distribution(event_rows["forward_return"])
        baseline_summary = summarize_distribution(baseline_rows["forward_return"])
        warnings: list[str] = []
        interval: tuple[float, float] | None = None
        p_value: float | None = None
        excess_mean: float | None = None
        standardized_effect: float | None = None

        if event_summary.count < config.statistics.minimum_sample_size:
            warnings.append(
                f"event sample {event_summary.count} is below minimum "
                f"{config.statistics.minimum_sample_size}"
            )
        if event_summary.mean is not None and baseline_summary.mean is not None:
            excess_mean = event_summary.mean - baseline_summary.mean
            if (
                baseline_summary.standard_deviation is not None
                and baseline_summary.standard_deviation > 0
            ):
                standardized_effect = excess_mean / baseline_summary.standard_deviation
            else:
                warnings.append("baseline standard deviation is zero or unavailable")

        event_values = pd.to_numeric(
            event_rows["forward_return"], errors="coerce"
        ).to_numpy(dtype=float)
        event_values = event_values[np.isfinite(event_values)]
        if len(event_values) >= 2 and baseline_summary.mean is not None:
            interval, p_value = _bootstrap_inference(
                event_values,
                baseline_summary.mean,
                expected_direction=config.hypothesis.expected_direction,
                specification=config.statistics,
                rng=rng,
            )
        else:
            warnings.append("bootstrap inference requires at least two finite event outcomes")
        p_values.append(p_value)

        horizon_results.append(
            HorizonStatistics(
                horizon_bars=horizon,
                event_forward_return=event_summary,
                baseline_forward_return=baseline_summary,
                maximum_upside_return=summarize_distribution(
                    event_rows["maximum_upside_return"]
                ),
                maximum_downside_return=summarize_distribution(
                    event_rows["maximum_downside_return"]
                ),
                time_to_first_positive_bar=summarize_distribution(
                    event_rows["time_to_first_positive_bar"]
                ),
                time_to_first_negative_bar=summarize_distribution(
                    event_rows["time_to_first_negative_bar"]
                ),
                excess_mean_confidence_interval=interval,
                excess_mean_return=excess_mean,
                standardized_effect=standardized_effect,
                bootstrap_p_value=p_value,
                warnings=tuple(warnings),
            )
        )

    q_values = benjamini_hochberg(p_values)
    adjusted_horizons = tuple(
        horizon.model_copy(update={"adjusted_q_value": q_value})
        for horizon, q_value in zip(horizon_results, q_values, strict=True)
    )
    report_warnings = [
        "the unconditional baseline includes event observations",
        "baseline uncertainty is not resampled in the bootstrap confidence interval",
        "statistical significance does not establish economic significance or tradability",
    ]
    if config.event_study.overlap_policy.value == "allow" and any(
        horizon > 1 for horizon in config.event_study.horizons_bars
    ):
        report_warnings.append(
            "event windows may overlap; moving-block bootstrap only partially addresses dependence"
        )
    return StatisticalReport(
        experiment_id=config.experiment_id,
        revision=config.revision,
        config_sha256=config.fingerprint(),
        expected_direction=config.hypothesis.expected_direction,
        confidence_level=config.statistics.confidence_level,
        bootstrap_method=config.statistics.bootstrap_method,
        bootstrap_samples=config.statistics.bootstrap_samples,
        random_seed=config.statistics.random_seed,
        horizons=adjusted_horizons,
        warnings=tuple(report_warnings),
    )
