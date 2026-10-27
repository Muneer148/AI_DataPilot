from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from .contracts import (
    MAX_COLUMNS,
    AnalyticsError,
    AnalyticsResult,
    finite_numeric_series,
    get_dataset_context,
    json_safe,
    validate_columns,
    validate_limit,
)

SUPPORTED_CORRELATIONS = {"pearson", "spearman", "kendall"}


def correlate_dataset(
    dataset: Any,
    *,
    columns: Sequence[str] | None = None,
    method: str = "pearson",
    min_periods: int = 2,
    max_pairs: int = 1000,
    max_columns: int = MAX_COLUMNS,
) -> AnalyticsResult:
    """Calculate pairwise-complete correlations; correlation does not imply causation."""
    dataframe, provenance, warnings = get_dataset_context(dataset)
    if not isinstance(method, str) or method not in SUPPORTED_CORRELATIONS:
        raise AnalyticsError(
            f"method must be one of {sorted(SUPPORTED_CORRELATIONS)}",
            code="INVALID_CORRELATION_METHOD",
        )
    if isinstance(min_periods, bool) or not isinstance(min_periods, int) or min_periods < 2:
        raise AnalyticsError("min_periods must be an integer of at least 2", code="INVALID_MIN_PERIODS")
    max_pairs = validate_limit(max_pairs, parameter="max_pairs")
    if (
        isinstance(max_columns, bool)
        or not isinstance(max_columns, int)
        or not 1 <= max_columns <= MAX_COLUMNS
    ):
        raise AnalyticsError(
            f"max_columns must be between 1 and {MAX_COLUMNS}",
            code="INVALID_LIMIT",
        )

    if columns is None:
        selected = [c for c in dataframe.columns if pd.api.types.is_numeric_dtype(dataframe[c].dtype) and not pd.api.types.is_bool_dtype(dataframe[c].dtype) and not pd.api.types.is_complex_dtype(dataframe[c].dtype)]
    else:
        selected = validate_columns(dataframe, columns)
        for column in selected:
            s = dataframe[column]
            if not pd.api.types.is_numeric_dtype(s.dtype) or pd.api.types.is_bool_dtype(s.dtype) or pd.api.types.is_complex_dtype(s.dtype):
                raise AnalyticsError(f"Correlation requires real numeric columns; '{column}' is not numeric", code="NON_NUMERIC_COLUMN", details={"column": column})
    if len(selected) > max_columns:
        warnings.append(
            f"Only the first {max_columns} of {len(selected)} selected columns were correlated."
        )
        selected = selected[:max_columns]

    clean = {}
    for column in selected:
        clean[column], n = finite_numeric_series(dataframe[column], column)
        if n:
            warnings.append(f"Column '{column}' has {n} infinite value(s), excluded from correlation.")
    records = []
    constant_pairs = insufficient_pairs = 0
    total_pair_count = len(selected) * (len(selected) - 1) // 2
    for i, left in enumerate(selected):
        for right in selected[i + 1:]:
            if len(records) >= max_pairs:
                break
            pair = pd.concat([clean[left].rename(left), clean[right].rename(right)], axis=1).dropna()
            count = int(len(pair))
            corr = None
            if count < min_periods:
                insufficient_pairs += 1
            elif pair[left].nunique() < 2 or pair[right].nunique() < 2:
                constant_pairs += 1
            else:
                value = pair[left].corr(pair[right], method=method, min_periods=min_periods)
                corr = json_safe(value) if pd.notna(value) and np.isfinite(float(value)) else None
            records.append({"column_a": left, "column_b": right, "correlation": corr, "sample_size": count})
        if len(records) >= max_pairs:
            break
    if total_pair_count > max_pairs:
        warnings.append(f"{total_pair_count} column pairs are possible; only the first {max_pairs} pairs were calculated.")
    if insufficient_pairs:
        warnings.append(f"{insufficient_pairs} pair(s) had fewer than {min_periods} complete observations.")
    if constant_pairs:
        warnings.append(f"{constant_pairs} pair(s) included a constant column; correlation is undefined.")
    if len(selected) < 2:
        warnings.append("At least two numeric columns are needed to calculate a relationship.")
    return AnalyticsResult(
        operation="correlation", columns=selected, row_count=len(dataframe), records=records,
        metrics={"method": method, "pair_count": total_pair_count, "returned_pair_count": len(records), "defined_pair_count": sum(r["correlation"] is not None for r in records)},
        parameters={
            "method": method,
            "min_periods": min_periods,
            "max_pairs": max_pairs,
            "max_columns": max_columns,
            "missing_policy": "pairwise_complete",
        },
        warnings=list(dict.fromkeys(warnings)),
        assumptions=[
            "Each pair uses rows where both selected values are present and finite.",
            "Correlation measures association; it does not establish causation.",
            "Constant columns and pairs below min_periods return null correlations.",
        ],
        provenance=provenance,
    )
