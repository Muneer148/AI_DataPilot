"""Tests for data quality and analysis-ready interfaces."""

import json

import numpy as np
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


def test_profile_handles_nested_values_timestamps_and_infinity():
    df = pd.DataFrame(
        {
            "payload": [{"a": 1}, {"a": 1}, ["x", "y"]],
            "when": [pd.Timestamp("2026-01-01"), pd.NaT, pd.Timestamp("2026-01-03")],
            "measure": [1.0, np.inf, 2.0],
        }
    )

    profile = profile_dataframe(df)
    payload = next(item for item in profile.column_profiles if item.name == "payload")
    when = next(item for item in profile.column_profiles if item.name == "when")
    measure = next(item for item in profile.column_profiles if item.name == "measure")

    assert payload.unique_count == 2
    assert when.example_values[0] == "2026-01-01T00:00:00"
    assert measure.max_value == 2.0
    json.dumps(profile.to_dict(), allow_nan=False)


def test_cleaning_is_conservative_and_auditable():
    df = pd.DataFrame(
        {
            " name ": [" Alice ", "", "Alice"],
            "amount": [10, None, 10],
            "empty": [None, None, None],
        }
    )

    cleaned, report = clean_dataframe(df, CleaningConfig(drop_duplicate_rows=True))

    assert cleaned.columns.tolist() == ["name", "amount"]
    assert cleaned["name"].tolist() == ["Alice"]
    assert report.blank_strings_replaced == 1
    assert report.empty_columns_removed == 1
    assert report.duplicate_rows_removed == 1
    assert report.output_rows == 1


def test_cleaning_retains_duplicate_records_by_default():
    df = pd.DataFrame({"event_id": [10, 11], "amount": [25, 25]})

    cleaned, report = clean_dataframe(df)

    assert len(cleaned) == 2
    assert report.duplicate_rows_removed == 0


def test_cleaning_can_be_configured_without_dropping_duplicates():
    df = pd.DataFrame({"name": ["A", "A"], "value": [1, 1]})

    cleaned, report = clean_dataframe(
        df,
        CleaningConfig(
            drop_duplicate_rows=False,
            drop_empty_rows=False,
            drop_empty_columns=False,
        ),
    )

    assert len(cleaned) == 2
    assert report.duplicate_rows_removed == 0


def test_cleaning_makes_generated_column_names_unique():
    df = pd.DataFrame([[1, 2, 3]], columns=["x", "x", "x_2"])

    cleaned, _ = clean_dataframe(df)

    assert cleaned.columns.tolist() == ["x", "x_2", "x_2_2"]
    assert cleaned.columns.is_unique


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


def test_model_context_is_bounded_and_excludes_examples_by_default():
    df = pd.DataFrame(
        {
            "email": ["private@example.com", "another@example.com"],
            "age": [21, 22],
        }
    )
    dataset = prepare_dataset(df)

    context = dataset.to_model_context(max_columns=1)

    assert context["dataset"]["schema_truncated"] is True
    assert context["dataset"]["columns_included"] == 1
    assert len(context["column_profiles"]) == 1
    assert context["data_access"]["raw_rows_included"] is False
    assert "example_values" not in context["column_profiles"][0]
    assert "top_values" not in context["column_profiles"][0]
    assert "private@example.com" not in json.dumps(context)

    with_examples = dataset.to_model_context(include_value_examples=True)
    assert "private@example.com" in json.dumps(with_examples)

    with pytest.raises(ValueError, match="at least 1"):
        dataset.to_model_context(max_columns=0)
