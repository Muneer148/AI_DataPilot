"""Unit tests for the initial data layer."""

import pandas as pd
import pytest

from src.data.loader import DataLoader
from src.data.schema import infer_schema


def test_infer_schema_counts_and_types():
    df = pd.DataFrame(
        {
            "age": [20, 21, 22],
            "name": ["A", "B", "C"],
            "active": [True, False, True],
        }
    )
    metadata = infer_schema(df)

    assert metadata.rows == 3
    assert metadata.columns == 3
    assert metadata.numerical_columns == ["age"]
    assert metadata.categorical_columns == ["name"]
    assert metadata.boolean_columns == ["active"]
    assert metadata.missing_cells == 0
    assert metadata.duplicate_rows == 0


def test_loader_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        DataLoader().load("does-not-exist.csv")


def test_loader_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "dataset.txt"
    path.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        DataLoader().load(path)
