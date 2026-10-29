from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .contracts import (
    AnalyticsError,
    AnalyticsResult,
    finite_numeric_series,
    get_dataset_context,
    json_safe,
    validate_columns,
    validate_limit,
)


def detect_outliers(
    dataset: Any,
    *,
    column: str,
    method: str = "iqr",
    threshold: float = 1.5,
    max_results: int = 100,
) -> AnalyticsResult:
    """Flag candidate outliers via IQR fences or absolute population z-score.

    Returned rows include only source row position and the selected numeric value.
    A flag is a candidate for review, not proof of error or fraud.
    """
    dataframe, provenance, warnings = get_dataset_context(dataset)
    validate_columns(dataframe, [column])
    if not isinstance(method, str) or method not in {"iqr", "zscore"}:
        raise AnalyticsError(
            "method must be 'iqr' or 'zscore'",
            code="INVALID_OUTLIER_METHOD",
        )
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not np.isfinite(threshold)
        or threshold <= 0
    ):
        raise AnalyticsError(
            "threshold must be a positive finite number",
            code="INVALID_THRESHOLD",
        )
    max_results = validate_limit(max_results)
    finite, non_finite = finite_numeric_series(dataframe[column], column)
    values = finite.to_numpy(dtype="float64", na_value=np.nan)
    valid = np.isfinite(values)
    sample = values[valid]
    count = len(sample)
    lower = upper = center = scale = None
    scores = np.full(len(dataframe), np.nan, dtype=float)
    if count == 0:
        warnings.append("No finite numeric observations were available.")
        flagged = np.zeros(len(dataframe), dtype=bool)
    elif method == "iqr":
        if count < 2:
            warnings.append("At least two finite observations are recommended for IQR analysis.")
        q1, q3 = np.quantile(sample, [0.25, 0.75])
        with np.errstate(over="ignore", invalid="ignore"):
            scale = float(q3 - q1)
            raw_lower, raw_upper = q1 - threshold * scale, q3 + threshold * scale
        center = float(np.median(sample))
        if not np.isfinite(scale) or not np.isfinite(raw_lower) or not np.isfinite(raw_upper):
            warnings.append(
                "IQR spread or fences overflowed floating-point range; no outlier candidates "
                "were classified because the thresholds are not representable."
            )
            scale = None if not np.isfinite(scale) else scale
            lower = upper = None
            flagged = np.zeros(len(dataframe), dtype=bool)
        else:
            lower, upper = float(raw_lower), float(raw_upper)
            flagged = valid & ((values < lower) | (values > upper))
            with np.errstate(over="ignore", invalid="ignore"):
                scores = np.where(values < lower, lower - values, values - upper)
            scores[~flagged] = np.nan
    else:
        with np.errstate(over="ignore", invalid="ignore"):
            center = float(np.mean(sample))
            scale = float(np.std(sample, ddof=0))
        if count < 2:
            warnings.append("At least two finite observations are required for z-score analysis.")
            flagged = np.zeros(len(dataframe), dtype=bool)
        elif not np.isfinite(center) or not np.isfinite(scale):
            warnings.append(
                "Z-score center or population standard deviation overflowed floating-point range; "
                "no outlier candidates were classified."
            )
            center = center if np.isfinite(center) else None
            scale = scale if np.isfinite(scale) else None
            flagged = np.zeros(len(dataframe), dtype=bool)
        elif scale == 0:
            warnings.append("Z-scores are undefined because the finite observations have zero variance.")
            flagged = np.zeros(len(dataframe), dtype=bool)
        else:
            with np.errstate(over="ignore", invalid="ignore"):
                scores = np.abs((values - center) / scale)
            flagged = valid & np.isfinite(scores) & (scores > threshold)
            scores[~flagged] = np.nan
    positions = np.flatnonzero(flagged)
    candidates = len(positions)
    if candidates > max_results:
        warnings.append(f"{candidates} outlier candidate(s) were found; output was limited to {max_results} records.")
        positions = positions[:max_results]
    records = []
    for position in positions:
        value = float(values[position])
        if method == "iqr":
            if lower is not None and value < lower:
                side = "low"
            else:
                side = "high"
        else:
            side = "threshold_exceeded"

        record = {
            "row_position": int(position),
            "value": json_safe(value),
            "outlier_score": json_safe(float(scores[position])),
            "side": side,
        }
        if lower is not None:
            record["lower_fence"], record["upper_fence"] = json_safe(lower), json_safe(upper)
        records.append(record)
    if non_finite:
        warnings.append(f"Column '{column}' has {non_finite} infinite value(s), excluded from outlier analysis.")
    return AnalyticsResult(
        operation="outliers", columns=[column], row_count=count, records=records,
        metrics={
            "method": method,
            "threshold": float(threshold),
            "sample_size": count,
            "candidate_count": candidates,
            "returned_count": len(records),
            "center": json_safe(center),
            "scale": json_safe(scale),
            "lower_fence": json_safe(lower),
            "upper_fence": json_safe(upper),
        },
        parameters={
            "column": column,
            "method": method,
            "threshold": float(threshold),
            "max_results": max_results,
        },
        warnings=list(dict.fromkeys(warnings)),
        assumptions=[
            "Only finite real numeric values are analyzed; missing and infinite values are excluded.",
            "IQR flags values strictly outside Q1 - threshold*IQR and Q3 + threshold*IQR.",
            "Z-score flags absolute population z-scores strictly greater than threshold.",
            "Outliers are candidates for investigation, not proof of an error or fraud.",
            "Only row position and selected numeric value are returned; other row fields are omitted.",
        ],
        provenance=provenance,
    )
