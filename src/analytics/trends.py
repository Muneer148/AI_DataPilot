from __future__ import annotations

from typing import Any

import pandas as pd

from .contracts import AnalyticsError, AnalyticsResult, finite_numeric_series, get_dataset_context, json_safe, validate_columns, validate_limit

INTERVALS = {"hour": "h", "day": "D", "week": "W", "month": "MS", "quarter": "QS", "year": "YS"}
TREND_AGGREGATIONS = {"count", "sum", "mean", "median", "min", "max"}


def trend_dataset(
    dataset: Any, *, time_column: str, value_column: str, interval: str = "day",
    aggregation: str = "sum", timezone: str = "UTC", limit: int = 1000,
) -> AnalyticsResult:
    """Aggregate a numeric measure into time buckets; naive timestamps are interpreted as UTC."""
    dataframe, provenance, warnings = get_dataset_context(dataset)
    selected = validate_columns(dataframe, [time_column, value_column])
    if time_column == value_column:
        raise AnalyticsError("time_column and value_column must differ", code="INVALID_TIME_COLUMNS")
    if interval not in INTERVALS:
        raise AnalyticsError(f"interval must be one of {sorted(INTERVALS)}", code="INVALID_TIME_INTERVAL")
    if aggregation not in TREND_AGGREGATIONS:
        raise AnalyticsError(f"aggregation must be one of {sorted(TREND_AGGREGATIONS)}", code="INVALID_AGGREGATION")
    limit = validate_limit(limit)
    if not isinstance(timezone, str) or not timezone.strip():
        raise AnalyticsError("timezone must be a valid timezone name", code="INVALID_TIMEZONE")
    raw_time = dataframe[time_column]
    if pd.api.types.is_numeric_dtype(raw_time.dtype) or pd.api.types.is_bool_dtype(raw_time.dtype):
        raise AnalyticsError(
            "time_column must contain datetime-like values or parseable date strings, not numeric values",
            code="NON_DATETIME_COLUMN",
            details={"column": time_column, "dtype": str(raw_time.dtype)},
        )
    values, non_finite = finite_numeric_series(dataframe[value_column], value_column)
    try:
        timestamps = pd.to_datetime(dataframe[time_column], errors="coerce", utc=True)
        if timezone.upper() != "UTC":
            timestamps = timestamps.dt.tz_convert(timezone)
    except (TypeError, ValueError, KeyError) as exc:
        raise AnalyticsError(f"Could not interpret timezone '{timezone}'", code="INVALID_TIMEZONE", details={"timezone": timezone}) from exc
    invalid_times = int(timestamps.isna().sum())
    invalid_values = int((values.isna() & dataframe[value_column].notna()).sum())
    valid = timestamps.notna() & values.notna()
    work = pd.DataFrame({"_timestamp": timestamps.loc[valid], "_value": values.loc[valid]})
    grouped = work.groupby(pd.Grouper(key="_timestamp", freq=INTERVALS[interval]))["_value"]
    if aggregation == "count":
        result = grouped.count()
    elif aggregation == "sum":
        result = grouped.agg(lambda items: items.sum(min_count=1))
    else:
        result = grouped.agg(aggregation)
    records = [{"period": json_safe(period), "value": json_safe(value)} for period, value in result.items()]
    bucket_count = len(records)
    if bucket_count > limit:
        warnings.append(f"Trend produced {bucket_count} buckets; only the most recent {limit} are returned.")
        records = records[-limit:]
    if invalid_times:
        warnings.append(f"{invalid_times} row(s) had invalid or missing timestamps and were skipped.")
    if invalid_values:
        warnings.append(f"{invalid_values} row(s) had missing or non-finite measures and were skipped.")
    if non_finite:
        warnings.append(f"Column '{value_column}' has {non_finite} infinite value(s), excluded from the trend.")
    if work.empty:
        warnings.append("No rows had both a valid timestamp and a finite numeric measure.")
    return AnalyticsResult(
        operation="trend", columns=selected, row_count=len(work), records=records,
        metrics={"valid_observation_count": len(work), "time_bucket_count": bucket_count, "returned_bucket_count": len(records)},
        parameters={"time_column": time_column, "value_column": value_column, "interval": interval, "aggregation": aggregation, "timezone": timezone, "limit": limit},
        warnings=list(dict.fromkeys(warnings)),
        assumptions=[
            "Naive timestamps are interpreted as UTC; aware timestamps are converted to the selected timezone.",
            "The selected timezone is applied before calendar bucketing.",
            "Invalid timestamps and missing/non-finite measures are skipped and reported.",
            "Only buckets present in the input are returned; empty periods are not synthesized.",
        ],
        provenance=provenance,
    )
