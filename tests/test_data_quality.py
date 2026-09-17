"""Tests for Week 2-3 data quality and analysis-ready interfaces."""

import pandas as pd
import pytest

from src.data.cleaning import CleaningConfig, clean_dataframe
from src.data.interfaces import prepare_dataset
from src.data.profiling import profile_dataframe
from src.data.validation import validate_dataframe


def test_validation_reports_missing_values_and_duplicates():
    df = pd.DataFrame({"id": [1, 1, 2], "name": ["A", None, "C"]})

    report = validate_dataframe(df)

    assert report.valid
    assert any(issue.code == "MISSING_VALUES" for issue in report.warnings)
    assert any(issue.code == "DUPLICATE_ROWS" for issue in report.warnings)


def test_validation_rejects_duplicate_column_names():
    df = pd.DataFrame([[1, 2]], columns=["value", "value"])

    report = validate_dataframe(df)

    assert not report.valid
    assert any(issue.code == "DUPLICATE_COLUMN_NAMES" for issue in report.errors)


def test_validation_enforces_required_columns_and_missing_ratio():
    df = pd.DataFrame({"id": [1, None, None], "name": ["A", "B", "C"]})

    report = validate_dataframe(df, required_columns=["id", "missing"], max_missing_ratio=0.5)

    assert not report.valid
    codes = {issue.code for issue in report.errors}
    assert "MISSING_REQUIRED_COLUMN" in codes
    assert "MISSING_RATIO_EXCEEDED" in codes


def test_profile_contains_numeric_and_categorical_statistics():
    df = pd.DataFrame({"amount": [10, 20, 30], "region": ["East", "East", "West"]})

    profile = profile_dataframe(df)
    amount = next(item for item in profile.column_profiles if item.name == "amount")
    region = next(item for item in profile.column_profiles if item.name == "region")

    assert profile.rows == 3
    assert amount.mean == 20.0
    assert amount.median == 20.0
    assert amount.min_value == 10
    assert amount.max_value == 30
    assert region.top_values[0] == ("East", 2)


def test_cleaning_is_conservative_and_auditable():
    df = pd.DataFrame(
        {
            " name ": [" Alice ", "", "Alice"],
            "amount": [10, None, 10],
            "empty": [None, None, None],
        }
    )

    cleaned, report = clean_dataframe(df)

    assert cleaned.columns.tolist() == ["name", "amount"]
    assert cleaned["name"].tolist() == ["Alice"]
    assert report.blank_strings_replaced == 1
    assert report.empty_columns_removed == 1
    assert report.duplicate_rows_removed == 1
    assert report.output_rows == 1


def test_cleaning_can_be_configured_without_dropping_duplicates():
    df = pd.DataFrame({"name": ["A", "A"], "value": [1, 1]})

    cleaned, report = clean_dataframe(
        df,
        CleaningConfig(drop_duplicate_rows=False, drop_empty_rows=False, drop_empty_columns=False),
    )

    assert len(cleaned) == 2
    assert report.duplicate_rows_removed == 0


def test_prepare_dataset_exposes_stable_downstream_contract():
    df = pd.DataFrame({"sales": [100, 200, 300], "region": ["N", "S", "N"]})

    dataset = prepare_dataset(df, required_columns=["sales", "region"])

    assert dataset.validation.valid
    assert dataset.rows == 3
    assert dataset.columns == ["sales", "region"]
    assert dataset.metadata.numerical_columns == ["sales"]
    assert dataset.get_column("sales").tolist() == [100, 200, 300]
    assert dataset.select_columns(["region"]).columns.tolist() == ["region"]

    with pytest.raises(KeyError):
        dataset.get_column("unknown")
