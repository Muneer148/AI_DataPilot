from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from .cleaning import CleaningConfig, CleaningReport, clean_dataframe
from .interfaces import AnalysisReadyDataset, prepare_dataset
from .loader import DataLoader
from .profiling import DatasetProfile, profile_dataframe
from .validation import ValidationReport, validate_dataframe


@dataclass
class DatasetPreparationPreview:
    """Non-destructive preview of quality findings and proposed cleaning."""

    source_name: str
    source_format: str
    source_size_bytes: int | None
    source_rows: int
    source_columns: int
    source_validation: ValidationReport
    source_profile: DatasetProfile
    cleaned_dataframe: pd.DataFrame
    cleaning: CleaningReport
    output_validation: ValidationReport
    cleaning_config: CleaningConfig

    @property
    def ready(self) -> bool:
        return self.output_validation.valid

    def to_dict(self, *, include_value_examples: bool = False) -> dict[str, Any]:
        """Return preview metadata without raw rows; examples are opt-in."""
        profile = self.source_profile.to_dict()
        if not include_value_examples:
            for column in profile["column_profiles"]:
                column.pop("example_values", None)
                column.pop("top_values", None)
        return {
            "source": {
                "name": self.source_name,
                "format": self.source_format,
                "size_bytes": self.source_size_bytes,
                "rows": self.source_rows,
                "columns": self.source_columns,
            },
            "source_validation": self.source_validation.to_dict(),
            "source_profile": profile,
            "proposed_cleaning": self.cleaning.to_dict(),
            "output_validation": self.output_validation.to_dict(),
            "preview_output": {
                "rows": len(self.cleaned_dataframe),
                "columns": self.cleaned_dataframe.columns.astype(str).tolist(),
                "ready": self.ready,
            },
            "cleaning_config": asdict(self.cleaning_config),
            "approval_note": "The cleaned preview is a separate DataFrame. The input was not mutated; call prepare_dataset or prepare_file with the same config to produce the final contract.",
        }


def preview_dataframe(
    df: pd.DataFrame,
    *,
    config: CleaningConfig | None = None,
    required_columns: Iterable[str] | None = None,
    max_missing_ratio: float = 1.0,
    source_name: str = "in-memory dataset",
    source_format: str = "dataframe",
    source_size_bytes: int | None = None,
) -> DatasetPreparationPreview:
    """Inspect quality and preview cleaning without mutating the input."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")
    if not 0 <= max_missing_ratio <= 1:
        raise ValueError("max_missing_ratio must be between 0 and 1.")
    if source_size_bytes is not None and source_size_bytes < 0:
        raise ValueError("source_size_bytes cannot be negative.")

    config = config or CleaningConfig()
    source_validation = validate_dataframe(df, allow_empty=True)
    source_profile = profile_dataframe(df)
    cleaned, cleaning_report = clean_dataframe(df, config)
    output_validation = validate_dataframe(
        cleaned,
        required_columns=required_columns,
        max_missing_ratio=max_missing_ratio,
    )
    return DatasetPreparationPreview(
        source_name=Path(source_name).name if source_name != "in-memory dataset" else source_name,
        source_format=source_format.lower().lstrip("."),
        source_size_bytes=source_size_bytes,
        source_rows=len(df),
        source_columns=len(df.columns),
        source_validation=source_validation,
        source_profile=source_profile,
        cleaned_dataframe=cleaned,
        cleaning=cleaning_report,
        output_validation=output_validation,
        cleaning_config=config,
    )


def preview_file(
    path: str | Path,
    *,
    loader: DataLoader | None = None,
    config: CleaningConfig | None = None,
    required_columns: Iterable[str] | None = None,
    max_missing_ratio: float = 1.0,
) -> DatasetPreparationPreview:
    """Load a supported file and return quality findings plus a cleaning preview."""
    file_path = Path(path)
    dataframe = (loader or DataLoader()).load(file_path)
    return preview_dataframe(
        dataframe,
        config=config,
        required_columns=required_columns,
        max_missing_ratio=max_missing_ratio,
        source_name=file_path.name,
        source_format=file_path.suffix,
        source_size_bytes=file_path.stat().st_size,
    )


def prepare_file(
    path: str | Path,
    *,
    loader: DataLoader | None = None,
    config: CleaningConfig | None = None,
    required_columns: Iterable[str] | None = None,
    max_missing_ratio: float = 1.0,
) -> AnalysisReadyDataset:
    """Load and prepare a supported file into the downstream data contract."""
    file_path = Path(path)
    dataframe = (loader or DataLoader()).load(file_path)
    return prepare_dataset(
        dataframe,
        config=config,
        required_columns=required_columns,
        max_missing_ratio=max_missing_ratio,
        source_name=file_path.name,
        source_format=file_path.suffix,
        source_size_bytes=file_path.stat().st_size,
    )
