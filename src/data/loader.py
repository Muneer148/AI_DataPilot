from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class DataLoader:
    """Load supported tabular datasets into pandas DataFrames."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}

    def load(self, path: str | Path) -> pd.DataFrame:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")

        loaders: dict[str, Any] = {
            ".csv": pd.read_csv,
            ".xlsx": pd.read_excel,
            ".xls": pd.read_excel,
            ".json": pd.read_json,
        }
        return loaders[suffix](file_path)
