from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from .cleaning import CleaningConfig, CleaningReport, clean_dataframe
from .profiling import DatasetProfile, profile_dataframe
from .schema import DatasetMetadata, infer_schema
from .validation import ValidationReport, validate_dataframe


@dataclass
class AnalysisReadyDataset:
    """Stable data contract for downstream AI and analytics modules."""

    dataframe: pd.DataFrame
    metadata: DatasetMetadata
    profile: DatasetProfile
    validation: ValidationReport
    cleaning: CleaningReport

    @property
    def rows(self) -> int:
        return len(self.dataframe)

    @property
    def columns(self) -> list[str]:
        return self.dataframe.columns.astype(str).tolist()

    def get_column(self, name: str) -> pd.Series:
        """Return one analysis-ready column, raising a clear error when absent."""
        if name not in self.dataframe.columns:
            raise KeyError(f"Column not found: {name}")
        return self.dataframe[name].copy()

    def select_columns(self, columns: Iterable[str]) -> pd.DataFrame:
        """Return a copy containing only requested columns."""
        selected = list(columns)
        missing = [column for column in selected if column not in self.dataframe.columns]
        if missing:
            raise KeyError(f"Columns not found: {missing}")
        return self.dataframe.loc[:, selected].copy()

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "metadata": self.metadata.to_dict(),
            "profile": self.profile.to_dict(),
            "validation": self.validation.to_dict(),
            "cleaning": self.cleaning.to_dict(),
        }


def prepare_dataset(
    df: pd.DataFrame,
    *,
    config: CleaningConfig | None = None,
    required_columns: Iterable[str] | None = None,
    max_missing_ratio: float = 1.0,
) -> AnalysisReadyDataset:
    """Clean, validate, profile and package a DataFrame for downstream analysis."""
    cleaned, cleaning_report = clean_dataframe(df, config)
    validation = validate_dataframe(
        cleaned,
        required_columns=required_columns,
        max_missing_ratio=max_missing_ratio,
    )
    if not validation.valid:
        messages = "; ".join(issue.message for issue in validation.errors)
        raise ValueError(f"Dataset failed validation: {messages}")

    return AnalysisReadyDataset(
        dataframe=cleaned,
        metadata=infer_schema(cleaned),
        profile=profile_dataframe(cleaned),
        validation=validation,
        cleaning=cleaning_report,
    )
