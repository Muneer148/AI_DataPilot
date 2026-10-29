from __future__ import annotations

from io import BytesIO, StringIO
from numbers import Integral
from pathlib import Path
from typing import Any

import pandas as pd


class DataLoader:
    """Load supported tabular datasets into pandas DataFrames.

    The default size guard is intended for interactive uploads. Set the limit
    to None for trusted local workflows that need to load larger files.
    """

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}
    DEFAULT_MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024

    def __init__(self, max_file_size_bytes: int | None = DEFAULT_MAX_FILE_SIZE_BYTES):
        if max_file_size_bytes is not None:
            if isinstance(max_file_size_bytes, bool) or not isinstance(max_file_size_bytes, Integral):
                raise TypeError("max_file_size_bytes must be a positive integer or None.")
            if max_file_size_bytes <= 0:
                raise ValueError("max_file_size_bytes must be positive or None.")
        self.max_file_size_bytes = max_file_size_bytes

    def load_bytes(self, filename: str, content: bytes | bytearray | memoryview) -> pd.DataFrame:
        """Parse an uploaded file directly from bytes without writing it to disk.

        The filename is used only to determine the supported format and report a
        basename. The content is bounded before parsing; user-supplied paths are
        never opened by this method.
        """
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("A filename with a supported extension is required.")
        file_name = Path(filename).name
        suffix = Path(file_name).suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")
        if not isinstance(content, (bytes, bytearray, memoryview)):
            raise TypeError("content must be bytes-like.")
        payload = bytes(content)
        if not payload:
            raise ValueError("Dataset file is empty.")
        if self.max_file_size_bytes is not None and len(payload) > self.max_file_size_bytes:
            limit_mib = self.max_file_size_bytes / (1024 * 1024)
            raise ValueError(
                f"Dataset is too large ({len(payload)} bytes). "
                f"Maximum allowed size is {limit_mib:g} MiB."
            )

        try:
            if suffix == ".csv":
                return pd.read_csv(BytesIO(payload))
            if suffix in {".xlsx", ".xls"}:
                return pd.read_excel(BytesIO(payload))
            # Pandas accepts a text stream for JSON and UTF-8-sig removes a BOM.
            text = payload.decode("utf-8-sig")
            return pd.read_json(StringIO(text))
        except Exception as exc:
            # Parser libraries may raise several format-specific exception types
            # (including zip/engine errors); keep uploads behind one safe boundary.
            raise ValueError(
                f"Could not parse dataset '{file_name}'. Check its contents and ensure the format engine is installed."
            ) from exc

    def load(self, path: str | Path) -> pd.DataFrame:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Dataset path is not a file: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(self.SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type '{suffix}'. Supported: {supported}")

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"Dataset file is empty: {file_path}")
        if self.max_file_size_bytes is not None and file_size > self.max_file_size_bytes:
            limit_mib = self.max_file_size_bytes / (1024 * 1024)
            raise ValueError(
                f"Dataset is too large ({file_size} bytes). "
                f"Maximum allowed size is {limit_mib:g} MiB."
            )

        loaders: dict[str, Any] = {
            ".csv": pd.read_csv,
            ".xlsx": pd.read_excel,
            ".xls": pd.read_excel,
            ".json": pd.read_json,
        }
        try:
            return loaders[suffix](file_path)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as exc:
            raise ValueError(f"Could not parse dataset '{file_path.name}': {exc}") from exc
