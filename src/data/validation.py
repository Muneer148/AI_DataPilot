from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ValidationIssue:
    """A deterministic validation finding for a dataset."""

    severity: str
    code: str
    message: str
    column: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationReport:
    """Validation findings produced before or after data preparation."""

    issues: tuple[ValidationIssue, ...]

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def _issue(severity: str, code: str, message: str, column: str | None = None) -> ValidationIssue:
    return ValidationIssue(severity=severity, code=code, message=message, column=column)


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: Iterable[str] | None = None,
    *,
    allow_empty: bool = False,
    max_missing_ratio: float = 1.0,
) -> ValidationReport:
    """Validate structural and basic data-quality constraints without mutating ``df``."""
    issues: list[ValidationIssue] = []

    if not isinstance(df, pd.DataFrame):
        return ValidationReport(
            (_issue("error", "NOT_DATAFRAME", "Expected a pandas DataFrame."),)
        )

    if not 0 <= max_missing_ratio <= 1:
        raise ValueError("max_missing_ratio must be between 0 and 1.")

    if df.empty:
        severity = "warning" if allow_empty else "error"
        issues.append(_issue(severity, "EMPTY_DATASET", "Dataset contains no rows."))

    if len(df.columns) == 0:
        issues.append(_issue("error", "NO_COLUMNS", "Dataset contains no columns."))

    if not df.columns.is_unique:
        duplicates = df.columns[df.columns.duplicated()].astype(str).tolist()
        issues.append(
            _issue(
                "error",
                "DUPLICATE_COLUMN_NAMES",
                f"Column names are not unique: {duplicates}.",
            )
        )

    blank_columns = [
        str(column)
        for column in df.columns
        if not isinstance(column, str) or not column.strip()
    ]
    if blank_columns:
        issues.append(
            _issue(
                "error",
                "BLANK_COLUMN_NAME",
                f"Blank or invalid column names found: {blank_columns}.",
            )
        )

    required = list(required_columns or [])
    missing_required = [column for column in required if column not in df.columns]
    for column in missing_required:
        issues.append(
            _issue("error", "MISSING_REQUIRED_COLUMN", f"Required column '{column}' is missing.", column)
        )

    if len(df) > 0:
        missing_ratios = df.isna().mean()
        for column, ratio in missing_ratios.items():
            if ratio > max_missing_ratio:
                issues.append(
                    _issue(
                        "error",
                        "MISSING_RATIO_EXCEEDED",
                        f"Missing ratio is {ratio:.2%}, above the allowed {max_missing_ratio:.2%}.",
                        str(column),
                    )
                )
            elif ratio > 0:
                issues.append(
                    _issue(
                        "warning",
                        "MISSING_VALUES",
                        f"Column contains {ratio:.2%} missing values.",
                        str(column),
                    )
                )

    all_null_columns = df.columns[df.isna().all()].astype(str).tolist()
    for column in all_null_columns:
        issues.append(
            _issue("warning", "ALL_NULL_COLUMN", "Column contains no non-null values.", column)
        )

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        issues.append(
            _issue(
                "warning",
                "DUPLICATE_ROWS",
                f"Dataset contains {duplicate_rows} duplicate row(s).",
            )
        )

    numeric_columns = df.select_dtypes(include="number").columns
    for column in numeric_columns:
        values = df[column].to_numpy(dtype=float, na_value=np.nan)
        if np.isinf(values).any():
            issues.append(
                _issue(
                    "warning",
                    "INFINITE_VALUES",
                    "Numeric column contains infinite values.",
                    str(column),
                )
            )

    return ValidationReport(tuple(issues))
