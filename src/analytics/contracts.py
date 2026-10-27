from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Mapping

import numpy as np
import pandas as pd

MAX_RESULT_ROWS = 1000
MAX_COLUMNS = 100


class AnalyticsError(ValueError):
    """A serializable analytics request or data-contract error."""

    def __init__(self, message: str, *, code: str = "INVALID_REQUEST", details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": str(self), "details": json_safe(self.details)}}


def json_safe(value: Any) -> Any:
    """Convert pandas, NumPy, date and non-finite values to strict JSON primitives."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date, time)):
        return value.isoformat()
    if isinstance(value, pd.Timedelta):
        return str(value)
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, set):
        return [json_safe(item) for item in sorted(value, key=repr)]
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)):
        return value
    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and bool(missing):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


@dataclass
class AnalyticsResult:
    """Stable result envelope for downstream agent and API integration."""

    operation: str
    columns: list[str] = field(default_factory=list)
    row_count: int = 0
    records: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    provenance: Any = None

    def to_dict(self) -> dict[str, Any]:
        return json_safe({
            "operation": self.operation, "columns": self.columns, "row_count": self.row_count,
            "records": self.records, "metrics": self.metrics, "parameters": self.parameters,
            "warnings": self.warnings, "assumptions": self.assumptions, "provenance": self.provenance,
        })

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), allow_nan=False)


def get_dataset_context(dataset: Any) -> tuple[pd.DataFrame, Any, list[str]]:
    """Accept a DataFrame or a prepared object exposing .dataframe, without importing src.data."""
    if isinstance(dataset, pd.DataFrame):
        dataframe, provenance, inherited_warnings = dataset, None, []
    else:
        dataframe = getattr(dataset, "dataframe", None)
        provenance_object = getattr(dataset, "provenance", None)
        provenance = provenance_object.to_dict() if callable(getattr(provenance_object, "to_dict", None)) else provenance_object
        inherited_warnings = []
        for report_name in ("source_validation", "validation"):
            report = getattr(dataset, report_name, None)
            for issue in getattr(report, "warnings", ()) or ():
                message = getattr(issue, "message", str(issue))
                if message and str(message) not in inherited_warnings:
                    inherited_warnings.append(str(message))
    if not isinstance(dataframe, pd.DataFrame):
        raise AnalyticsError("dataset must be a DataFrame or expose a DataFrame as .dataframe", code="INVALID_DATASET")
    if not dataframe.columns.is_unique:
        duplicates = dataframe.columns[dataframe.columns.duplicated()].astype(str).tolist()
        raise AnalyticsError("Duplicate column labels are not supported", code="DUPLICATE_COLUMNS", details={"columns": duplicates})
    invalid = [repr(c) for c in dataframe.columns if not isinstance(c, str) or not c.strip()]
    if invalid:
        raise AnalyticsError("Column labels must be non-empty strings", code="INVALID_COLUMN_LABELS", details={"columns": invalid})
    return dataframe, json_safe(provenance), inherited_warnings


def validate_columns(dataframe: pd.DataFrame, columns: Any, *, parameter: str = "columns", allow_empty: bool = False) -> list[str]:
    if isinstance(columns, (str, bytes, Mapping, set, frozenset)):
        raise AnalyticsError(
            f"{parameter} must be an ordered sequence of column names",
            code="INVALID_COLUMNS",
            details={"parameter": parameter},
        )
    try:
        selected = list(columns)
    except TypeError as exc:
        raise AnalyticsError(f"{parameter} must be a sequence of column names", code="INVALID_COLUMNS", details={"parameter": parameter}) from exc
    if not allow_empty and not selected:
        raise AnalyticsError(f"{parameter} must contain at least one column", code="EMPTY_COLUMNS", details={"parameter": parameter})
    if any(not isinstance(c, str) for c in selected):
        raise AnalyticsError(f"{parameter} entries must be strings", code="INVALID_COLUMNS", details={"parameter": parameter})
    if len(set(selected)) != len(selected):
        raise AnalyticsError(f"{parameter} cannot contain duplicate names", code="DUPLICATE_COLUMNS", details={"parameter": parameter})
    missing = [c for c in selected if c not in dataframe.columns]
    if missing:
        raise AnalyticsError(f"Unknown column name(s) in {parameter}: {missing}", code="UNKNOWN_COLUMN", details={"parameter": parameter, "columns": missing})
    return selected


def finite_numeric_series(series: pd.Series, column: str) -> tuple[pd.Series, int]:
    """Keep finite real numeric values only; string data is never converted."""
    if not pd.api.types.is_numeric_dtype(series.dtype) or pd.api.types.is_bool_dtype(series.dtype) or pd.api.types.is_complex_dtype(series.dtype):
        raise AnalyticsError(f"Column '{column}' must have a real numeric dtype", code="NON_NUMERIC_COLUMN", details={"column": column, "dtype": str(series.dtype)})
    values = series.to_numpy(dtype="float64", na_value=np.nan)
    finite = np.isfinite(values)
    non_finite = int((~finite & ~pd.isna(values)).sum())
    return series.where(finite), non_finite


def validate_limit(limit: Any, *, parameter: str = "limit") -> int:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULT_ROWS:
        raise AnalyticsError(f"{parameter} must be an integer between 1 and {MAX_RESULT_ROWS}", code="INVALID_LIMIT", details={"parameter": parameter, "maximum": MAX_RESULT_ROWS})
    return limit
