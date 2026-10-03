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
        """Return the complete metadata contract, excluding raw row records."""
        return {
            "rows": self.rows,
            "columns": self.columns,
            "metadata": self.metadata.to_dict(),
            "profile": self.profile.to_dict(),
            "validation": self.validation.to_dict(),
            "cleaning": self.cleaning.to_dict(),
        }

    def to_model_context(
        self,
        *,
        max_columns: int = 100,
        include_value_examples: bool = False,
    ) -> dict[str, Any]:
        """Build bounded context for an LLM without sending the dataset's rows.

        Examples and frequent values are excluded by default because they may
        contain sensitive values. Row-level analysis should run against the local
        DataFrame through deterministic tools, not be guessed from this summary.
        """
        if max_columns < 1:
            raise ValueError("max_columns must be at least 1.")

        included_names = self.columns[:max_columns]
        included_set = set(included_names)
        column_profiles: list[dict[str, Any]] = []
        for profile in self.profile.column_profiles[:max_columns]:
            item = profile.to_dict()
            if not include_value_examples:
                item.pop("example_values", None)
                item.pop("top_values", None)
            column_profiles.append(item)

        schema_hints = {
            "numerical_columns": [name for name in self.metadata.numerical_columns if name in included_set],
            "categorical_columns": [name for name in self.metadata.categorical_columns if name in included_set],
            "datetime_columns": [name for name in self.metadata.datetime_columns if name in included_set],
            "datetime_like_columns": [name for name in self.metadata.datetime_like_columns if name in included_set],
            "boolean_columns": [name for name in self.metadata.boolean_columns if name in included_set],
            "identifier_columns": [name for name in self.metadata.identifier_columns if name in included_set],
        }
        return {
            "dataset": {
                "rows": self.rows,
                "total_columns": len(self.columns),
                "columns_included": len(included_names),
                "schema_truncated": len(self.columns) > max_columns,
            },
            "schema_hints": schema_hints,
            "column_profiles": column_profiles,
            "validation": self.validation.to_dict(),
            "cleaning": self.cleaning.to_dict(),
            "data_access": {
                "raw_rows_included": False,
                "guidance": "Use local analysis tools for row-level calculations; do not infer results from profile summaries alone.",
            },
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
