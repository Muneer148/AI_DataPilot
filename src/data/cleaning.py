from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CleaningConfig:
    """Explicit, conservative cleaning options."""

    strip_column_names: bool = True
    make_column_names_unique: bool = True
    strip_string_values: bool = True
    blank_strings_to_missing: bool = True
    drop_empty_rows: bool = True
    drop_empty_columns: bool = True
    drop_duplicate_rows: bool = True


@dataclass(frozen=True)
class CleaningReport:
    """Audit information describing deterministic cleaning changes."""

    input_rows: int
    output_rows: int
    input_columns: int
    output_columns: int
    rows_removed: int
    columns_removed: int
    duplicate_rows_removed: int
    empty_rows_removed: int
    empty_columns_removed: int
    blank_strings_replaced: int
    renamed_columns: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unique_names(names: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    result: list[str] = []
    for name in names:
        counts[name] = counts.get(name, 0) + 1
        result.append(name if counts[name] == 1 else f"{name}_{counts[name]}")
    return result


def clean_dataframe(
    df: pd.DataFrame,
    config: CleaningConfig | None = None,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Return a cleaned copy and an auditable report; the input is never mutated."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    config = config or CleaningConfig()
    cleaned = df.copy(deep=True)
    input_rows, input_columns = cleaned.shape

    original_names = [str(column) for column in cleaned.columns]
    new_names = original_names.copy()
    if config.strip_column_names:
        new_names = [name.strip() for name in new_names]
    if config.make_column_names_unique:
        new_names = _unique_names(new_names)

    renamed_columns = {
        old: new
        for old, new in zip(original_names, new_names)
        if old != new
    }
    cleaned.columns = new_names

    blank_strings_replaced = 0
    if config.strip_string_values or config.blank_strings_to_missing:
        object_columns = cleaned.select_dtypes(include=["object", "string"]).columns
        for column in object_columns:
            series = cleaned[column]
            if config.strip_string_values:
                series = series.map(lambda value: value.strip() if isinstance(value, str) else value)
            if config.blank_strings_to_missing:
                blank_mask = series.map(lambda value: isinstance(value, str) and value == "")
                blank_strings_replaced += int(blank_mask.sum())
                series = series.mask(blank_mask, pd.NA)
            cleaned[column] = series

    empty_rows_removed = 0
    if config.drop_empty_rows:
        before = len(cleaned)
        cleaned = cleaned.dropna(how="all")
        empty_rows_removed = before - len(cleaned)

    empty_columns_removed = 0
    if config.drop_empty_columns:
        before = len(cleaned.columns)
        cleaned = cleaned.dropna(axis=1, how="all")
        empty_columns_removed = before - len(cleaned.columns)

    duplicate_rows_removed = 0
    if config.drop_duplicate_rows:
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates(ignore_index=True)
        duplicate_rows_removed = before - len(cleaned)

    cleaned = cleaned.reset_index(drop=True)

    report = CleaningReport(
        input_rows=input_rows,
        output_rows=len(cleaned),
        input_columns=input_columns,
        output_columns=len(cleaned.columns),
        rows_removed=input_rows - len(cleaned),
        columns_removed=input_columns - len(cleaned.columns),
        duplicate_rows_removed=duplicate_rows_removed,
        empty_rows_removed=empty_rows_removed,
        empty_columns_removed=empty_columns_removed,
        blank_strings_replaced=blank_strings_replaced,
        renamed_columns=renamed_columns,
    )
    return cleaned, report
