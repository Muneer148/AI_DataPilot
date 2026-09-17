from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

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


def _safe_value(value: Any) -> Any:
    """Convert common pandas/numpy scalar values into JSON-friendly Python values."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return value.isoformat()
    return value


def _examples(series: pd.Series, limit: int) -> tuple[Any, ...]:
    values = series.dropna().drop_duplicates().head(limit).tolist()
    return tuple(_safe_value(value) for value in values)


def _numeric_stats(series: pd.Series) -> dict[str, float | None]:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {"min_value": None, "max_value": None, "mean": None, "median": None, "std": None}
    return {
        "min_value": _safe_value(numeric.min()),
        "max_value": _safe_value(numeric.max()),
        "mean": float(numeric.mean()),
        "median": float(numeric.median()),
        "std": float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0,
    }


def profile_dataframe(df: pd.DataFrame, *, example_limit: int = 5, top_value_limit: int = 5) -> DatasetProfile:
    """Create a deterministic, bounded profile without changing the input DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    if example_limit < 0 or top_value_limit < 0:
        raise ValueError("Profile limits must be non-negative.")

    profiles: list[ColumnProfile] = []
    row_count = len(df)

    for column in df.columns:
        series = df[column]
        non_null = int(series.notna().sum())
        missing = row_count - non_null
        unique = int(series.nunique(dropna=True))
        denominator = non_null if non_null else 1

        stats: dict[str, Any] = {}
        top_values: tuple[tuple[Any, int], ...] = ()
        if pd.api.types.is_numeric_dtype(series):
            stats = _numeric_stats(series)
        elif pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
            counts = series.dropna().value_counts().head(top_value_limit)
            top_values = tuple((_safe_value(value), int(count)) for value, count in counts.items())

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

    return DatasetProfile(
        rows=row_count,
        columns=len(df.columns),
        duplicate_rows=int(df.duplicated().sum()),
        column_profiles=tuple(profiles),
    )
