from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ColumnProfile:
    """Compact, JSON-friendly profile for one dataset column."""

    name: str
    dtype: str
    non_null_count: int
    missing_count: int
    missing_ratio: float
    unique_count: int
    unique_ratio: float
    example_values: tuple[Any, ...]
    min_value: Any | None = None
    max_value: Any | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    top_values: tuple[tuple[Any, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DatasetProfile:
    """Dataset-level and column-level profiling output."""

    rows: int
    columns: int
    duplicate_rows: int
    column_profiles: tuple[ColumnProfile, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "duplicate_rows": self.duplicate_rows,
            "column_profiles": [profile.to_dict() for profile in self.column_profiles],
        }


def _is_missing(value: Any) -> bool:
    """Return whether a scalar is missing without failing on lists/dicts/arrays."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    try:
        result = pd.isna(value)
        return bool(result) if isinstance(result, (bool, np.bool_)) else False
    except (TypeError, ValueError):
        return False


def _safe_value(value: Any) -> Any:
    """Convert common pandas/numpy values to JSON-compatible Python values."""
    if _is_missing(value):
        return None
    if isinstance(value, (pd.Timestamp, pd.Timedelta, datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_safe_value(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _value_key(value: Any) -> tuple[str, str]:
    """Create a stable-enough key for values that may be unhashable."""
    return type(value).__name__, repr(value)


def _distinct_values(series: pd.Series, limit: int | None = None) -> list[Any]:
    values: list[Any] = []
    seen: set[tuple[str, str]] = set()
    for value in series.tolist():
        if _is_missing(value):
            continue
        key = _value_key(value)
        if key in seen:
            continue
        seen.add(key)
        values.append(value)
        if limit is not None and len(values) >= limit:
            break
    return values


def _examples(series: pd.Series, limit: int) -> tuple[Any, ...]:
    if limit == 0:
        return ()
    return tuple(_safe_value(value) for value in _distinct_values(series, limit))


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    try:
        numeric = numeric[np.isfinite(numeric)]
    except TypeError:
        return {"min_value": None, "max_value": None, "mean": None, "median": None, "std": None}
    if numeric.empty:
        return {"min_value": None, "max_value": None, "mean": None, "median": None, "std": None}
    return {
        "min_value": _safe_value(numeric.min()),
        "max_value": _safe_value(numeric.max()),
        "mean": _safe_value(float(numeric.mean())),
        "median": _safe_value(float(numeric.median())),
        "std": _safe_value(float(numeric.std(ddof=1))) if len(numeric) > 1 else 0.0,
    }


def _top_values(series: pd.Series, limit: int) -> tuple[tuple[Any, int], ...]:
    if limit == 0:
        return ()
    counts: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], Any] = {}
    for value in series.tolist():
        if _is_missing(value):
            continue
        key = _value_key(value)
        counts[key] += 1
        examples.setdefault(key, value)
    return tuple(
        (_safe_value(examples[key]), int(count))
        for key, count in counts.most_common(limit)
    )


def profile_dataframe(
    df: pd.DataFrame,
    *,
    example_limit: int = 5,
    top_value_limit: int = 5,
) -> DatasetProfile:
    """Create a deterministic, bounded profile without changing the input DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    if example_limit < 0 or top_value_limit < 0:
        raise ValueError("Profile limits must be non-negative.")

    profiles: list[ColumnProfile] = []
    row_count = len(df)

    for position, column in enumerate(df.columns):
        # iloc also handles duplicate column labels when profiling raw input.
        series = df.iloc[:, position]
        non_null = int(series.notna().sum())
        missing = row_count - non_null
        unique = len(_distinct_values(series))
        denominator = non_null if non_null else 1

        stats: dict[str, Any] = {}
        top_values: tuple[tuple[Any, int], ...] = ()
        if pd.api.types.is_numeric_dtype(series):
            stats = _numeric_stats(series)
        elif (
            pd.api.types.is_object_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
            or pd.api.types.is_string_dtype(series)
            or pd.api.types.is_bool_dtype(series)
        ):
            top_values = _top_values(series, top_value_limit)

        profiles.append(
            ColumnProfile(
                name=str(column),
                dtype=str(series.dtype),
                non_null_count=non_null,
                missing_count=missing,
                missing_ratio=(missing / row_count) if row_count else 0.0,
                unique_count=unique,
                unique_ratio=unique / denominator,
                example_values=_examples(series, example_limit),
                top_values=top_values,
                **stats,
            )
        )

    try:
        duplicate_rows = int(df.duplicated().sum())
    except TypeError:
        # Nested object values can be unhashable; avoid failing the whole profile.
        duplicate_rows = 0

    return DatasetProfile(
        rows=row_count,
        columns=len(df.columns),
        duplicate_rows=duplicate_rows,
        column_profiles=tuple(profiles),
    )
