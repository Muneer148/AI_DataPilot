from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class DatasetMetadata:
    rows: int
    columns: int
    column_names: list[str]
    numerical_columns: list[str]
    categorical_columns: list[str]
    datetime_columns: list[str]
    boolean_columns: list[str]
    missing_cells: int
    duplicate_rows: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_schema(df: pd.DataFrame) -> DatasetMetadata:
    numerical = df.select_dtypes(include="number").columns.tolist()
    datetime = df.select_dtypes(include="datetime").columns.tolist()
    boolean = df.select_dtypes(include="bool").columns.tolist()
    categorical = [
        col for col in df.columns
        if col not in numerical and col not in datetime and col not in boolean
    ]

    return DatasetMetadata(
        rows=len(df),
        columns=len(df.columns),
        column_names=df.columns.astype(str).tolist(),
        numerical_columns=numerical,
        categorical_columns=categorical,
        datetime_columns=datetime,
        boolean_columns=boolean,
        missing_cells=int(df.isna().sum().sum()),
        duplicate_rows=int(df.duplicated().sum()),
    )
