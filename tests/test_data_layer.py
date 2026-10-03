"""Unit tests for the data ingestion and schema layer."""

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
    with pytest.raises(ValueError, match="Unsupported file type"):
        DataLoader().load(path)


def test_loader_reads_csv(tmp_path):
    path = tmp_path / "dataset.csv"
    path.write_text("id,name\n1,Ada\n2,Linus\n", encoding="utf-8")

    result = DataLoader().load(path)

    assert result.to_dict(orient="records") == [
        {"id": 1, "name": "Ada"},
        {"id": 2, "name": "Linus"},
    ]


def test_loader_rejects_empty_file(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="file is empty"):
        DataLoader().load(path)


def test_loader_enforces_configurable_size_limit(tmp_path):
    path = tmp_path / "dataset.csv"
    path.write_text("id\n1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="too large"):
        DataLoader(max_file_size_bytes=1).load(path)


def test_loader_rejects_directory_path(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        DataLoader().load(tmp_path)
