from __future__ import annotations

import re
import warnings
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DatasetMetadata:
    """Structural metadata plus conservative semantic hints for downstream models."""

    rows: int
    columns: int
    column_names: list[str]
    numerical_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    boolean_columns: list[str]
    missing_cells: int
    duplicate_rows: int
    datetime_like_columns: list[str] = field(default_factory=list)
    identifier_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _looks_datetime_like(series: pd.Series) -> bool:
    """Flag string columns that parse consistently as dates without changing them."""
    if not (
        pd.api.types.is_object_dtype(series)
        or pd.api.types.is_string_dtype(series)
    ):
        return False

    values = series.dropna()
    if values.empty:
        return False
    strings = values.astype(str).str.strip()
    strings = strings[strings != ""]
    if strings.empty:
        return False

    # Avoid interpreting plain numeric codes such as "202401" as dates.
    has_date_marker = strings.str.contains(r"[-/:T]|\\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\\b", case=False, regex=True).any()
    if not has_date_marker:
        return False

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(strings, errors="coerce")
    return float(parsed.notna().mean()) >= 0.8


def _looks_identifier_like(column_name: str) -> bool:
    normalized = re.sub(r"[\\s-]+", "_", column_name.strip().lower())
    return (
        normalized == "id"
        or normalized.endswith(("_id", "_uuid", "_key"))
    )


def infer_schema(df: pd.DataFrame) -> DatasetMetadata:
    """Infer physical column types and conservative semantic hints.

    Date-like strings are reported separately; this function does not coerce or
    mutate source values. Identifier hints are based on column names, not proof
    that values are unique or safe to expose.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    names = df.columns.astype(str).tolist()
    numerical: list[str] = []
    categorical: list[str] = []
    datetime: list[str] = []
    boolean: list[str] = []
    datetime_like: list[str] = []
    identifiers: list[str] = []

    for position, name in enumerate(names):
        series = df.iloc[:, position]
        if pd.api.types.is_bool_dtype(series):
            boolean.append(name)
        elif pd.api.types.is_numeric_dtype(series):
            numerical.append(name)
        elif pd.api.types.is_datetime64_any_dtype(series):
            datetime.append(name)
        else:
            categorical.append(name)
            if _looks_datetime_like(series):
                datetime_like.append(name)
        if _looks_identifier_like(name):
            identifiers.append(name)

    try:
        duplicate_rows = int(df.duplicated().sum())
    except TypeError:
        duplicate_rows = 0

    return DatasetMetadata(
        rows=len(df),
        columns=len(df.columns),
        column_names=names,
        numerical_columns=numerical,
        categorical_columns=categorical,
        datetime_columns=datetime,
        boolean_columns=boolean,
        missing_cells=int(df.isna().sum().sum()),
        duplicate_rows=duplicate_rows,
        datetime_like_columns=datetime_like,
        identifier_columns=identifiers,
    )
