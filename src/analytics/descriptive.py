from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from .contracts import AnalyticsError, AnalyticsResult, MAX_COLUMNS, finite_numeric_series, get_dataset_context, is_non_finite_float_result, json_safe, sum_numeric_values, validate_columns


def describe_dataset(
    dataset: Any,
    *,
    columns: Sequence[str] | None = None,
    quantiles: Sequence[float] = (0.25, 0.5, 0.75),
    max_columns: int = MAX_COLUMNS,
) -> AnalyticsResult:
    """Calculate column statistics from the supplied DataFrame without mutating it.

    Missing ratios use total row count. Numeric summaries exclude infinities and
    never coerce strings. Standard deviation is sample standard deviation (ddof=1).
    """
    dataframe, provenance, warnings = get_dataset_context(dataset)
    if isinstance(max_columns, bool) or not isinstance(max_columns, int) or not 1 <= max_columns <= MAX_COLUMNS:
        raise AnalyticsError(f"max_columns must be between 1 and {MAX_COLUMNS}", code="INVALID_LIMIT")
    if columns is None:
        selected = list(dataframe.columns[:max_columns])
        if len(dataframe.columns) > max_columns:
            warnings.append(f"Only the first {max_columns} of {len(dataframe.columns)} columns were summarized.")
    else:
        selected = validate_columns(dataframe, columns)
        if len(selected) > max_columns:
            warnings.append(f"Only the first {max_columns} requested columns were summarized.")
            selected = selected[:max_columns]
    if isinstance(quantiles, (str, bytes, Mapping, set, frozenset)):
        raise AnalyticsError(
            "quantiles must be an ordered sequence of numbers",
            code="INVALID_QUANTILES",
        )
    try:
        qs = [float(q) for q in quantiles]
    except (TypeError, ValueError) as exc:
        raise AnalyticsError("quantiles must be a sequence of numbers", code="INVALID_QUANTILES") from exc
    if not qs or any(not np.isfinite(q) or q < 0 or q > 1 for q in qs) or len(set(qs)) != len(qs):
        raise AnalyticsError("quantiles must be unique finite numbers between 0 and 1", code="INVALID_QUANTILES", details={"quantiles": qs})

    row_count = len(dataframe)
    records = []
    for column in selected:
        series = dataframe[column]
        missing = int(series.isna().sum())
        record: dict[str, Any] = {
            "column": column, "dtype": str(series.dtype), "non_null_count": int(series.notna().sum()),
            "missing_count": missing, "missing_ratio": missing / row_count if row_count else 0.0,
            "numeric_count": None, "non_finite_count": 0, "sum": None, "mean": None,
            "median": None, "min": None, "max": None, "std": None, "quantiles": {},
        }
        if pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(series.dtype) and not pd.api.types.is_complex_dtype(series.dtype):
            finite, non_finite = finite_numeric_series(series, column)
            values = finite.dropna()
            record["numeric_count"] = int(len(values))
            record["non_finite_count"] = non_finite
            record["quantiles"] = {str(q): None for q in qs}
            if not values.empty:
                # Keep raw calculation outputs long enough to distinguish missing data
                # from overflow. json_safe intentionally maps non-finite floats to null.
                raw_stats = {
                    "sum": sum_numeric_values(values),
                    "mean": values.mean(),
                    "median": values.median(),
                    "min": values.min(),
                    "max": values.max(),
                    "std": values.std(ddof=1) if len(values) > 1 else None,
                }
                raw_quantiles = {str(q): values.quantile(q) for q in qs}
                if any(is_non_finite_float_result(value) for value in [
                    *raw_stats.values(), *raw_quantiles.values()
                ]):
                    warnings.append(
                        f"Column '{column}' produced a non-finite floating-point statistic; "
                        "the affected result is null (possible numeric overflow)."
                    )
                record.update({
                    **{name: json_safe(value) for name, value in raw_stats.items()},
                    "quantiles": {name: json_safe(value) for name, value in raw_quantiles.items()},
                })
            if non_finite:
                warnings.append(f"Column '{column}' has {non_finite} infinite value(s), excluded from numeric summaries.")
        records.append(record)

    return AnalyticsResult(
        operation="describe", columns=selected, row_count=row_count, records=records,
        metrics={"total_columns": len(dataframe.columns), "returned_columns": len(selected), "quantiles": qs},
        parameters={"quantiles": qs, "max_columns": max_columns},
        warnings=list(dict.fromkeys(warnings)),
        assumptions=[
            "missing_ratio = missing_count / total row count; empty datasets use 0.",
            "Numeric summaries exclude infinities and report their count separately.",
            "Text columns are not coerced to numbers.",
            "Sample standard deviation uses ddof=1 and is null for fewer than two finite observations.",
        ],
        provenance=provenance,
    )
