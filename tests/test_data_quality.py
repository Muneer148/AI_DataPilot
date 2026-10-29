"""Tests for data quality and analysis-ready interfaces."""

import json

import numpy as np
import pandas as pd
import pytest

from src.data.cleaning import CleaningConfig, clean_dataframe
from src.data.interfaces import prepare_dataset
from src.data.profiling import profile_dataframe
from src.data.validation import validate_dataframe
from src.data.workflow import prepare_file, preview_dataframe, preview_file
from src.data.loader import DataLoader
from src.data.schema import infer_schema


def test_validation_reports_missing_values_and_duplicates():
    df = pd.DataFrame({"id": [1, 1, 2, 2], "name": ["A", "A", None, "C"]})
    report = validate_dataframe(df)
    assert report.valid
    assert any(issue.code == "MISSING_VALUES" for issue in report.warnings)
    assert any(issue.code == "DUPLICATE_ROWS" for issue in report.warnings)


def test_validation_handles_duplicate_labels_with_mixed_dtypes_and_infinity():
    df = pd.DataFrame(
        [[1, "ok"], [np.inf, "still ok"]],
        columns=["value", "value"],
    )

    report = validate_dataframe(df)

    assert not report.valid
    assert any(issue.code == "DUPLICATE_COLUMN_NAMES" for issue in report.errors)
    infinite_issues = [issue for issue in report.warnings if issue.code == "INFINITE_VALUES"]
    assert len(infinite_issues) == 1
    assert infinite_issues[0].column == "value"


def test_validation_rejects_duplicate_column_names():
    report = validate_dataframe(pd.DataFrame([[1, 2]], columns=["value", "value"]))
    assert not report.valid
    assert any(issue.code == "DUPLICATE_COLUMN_NAMES" for issue in report.errors)


def test_validation_enforces_required_columns_and_missing_ratio():
    df = pd.DataFrame({"id": [1, None, None], "name": ["A", "B", "C"]})
    report = validate_dataframe(df, required_columns=["id", "missing"], max_missing_ratio=0.5)
    assert not report.valid
    codes = {issue.code for issue in report.errors}
    assert "MISSING_REQUIRED_COLUMN" in codes
    assert "MISSING_RATIO_EXCEEDED" in codes


def test_validation_handles_nested_unhashable_values():
    report = validate_dataframe(pd.DataFrame({"payload": [{"a": 1}, ["x"], {"b": 2}]}))
    assert report.valid
    assert isinstance(report.to_dict(), dict)


def test_profile_contains_numeric_and_categorical_statistics():
    profile = profile_dataframe(pd.DataFrame({"amount": [10, 20, 30], "region": ["East", "East", "West"]}))
    amount = next(item for item in profile.column_profiles if item.name == "amount")
    region = next(item for item in profile.column_profiles if item.name == "region")
    assert profile.rows == 3
    assert amount.mean == 20.0
    assert amount.median == 20.0
    assert amount.min_value == 10
    assert amount.max_value == 30
    assert region.top_values[0] == ("East", 2)


def test_profile_handles_nested_values_timestamps_and_infinity():
    df = pd.DataFrame({
        "payload": [{"a": 1}, {"a": 1}, ["x", "y"]],
        "when": [pd.Timestamp("2026-01-01"), pd.NaT, pd.Timestamp("2026-01-03")],
        "measure": [1.0, np.inf, 2.0],
    })
    profile = profile_dataframe(df)
    payload = next(item for item in profile.column_profiles if item.name == "payload")
    when = next(item for item in profile.column_profiles if item.name == "when")
    measure = next(item for item in profile.column_profiles if item.name == "measure")
    assert payload.unique_count == 2
    assert when.example_values[0] == "2026-01-01T00:00:00"
    assert measure.max_value == 2.0
    json.dumps(profile.to_dict(), allow_nan=False)


def test_cleaning_is_conservative_and_auditable():
    df = pd.DataFrame({" name ": [" Alice ", "", "Alice"], "amount": [10, None, 10], "empty": [None, None, None]})
    cleaned, report = clean_dataframe(df, CleaningConfig(drop_duplicate_rows=True))
    assert cleaned.columns.tolist() == ["name", "amount"]
    assert cleaned["name"].tolist() == ["Alice"]
    assert report.blank_strings_replaced == 1
    assert report.empty_columns_removed == 1
    assert report.duplicate_rows_removed == 1
    assert report.output_rows == 1


def test_cleaning_retains_duplicate_records_by_default():
    cleaned, report = clean_dataframe(pd.DataFrame({"event_id": [10, 11], "amount": [25, 25]}))
    assert len(cleaned) == 2
    assert report.duplicate_rows_removed == 0


def test_cleaning_can_be_configured_without_dropping_duplicates():
    df = pd.DataFrame({"name": ["A", "A"], "value": [1, 1]})
    cleaned, report = clean_dataframe(df, CleaningConfig(drop_duplicate_rows=False, drop_empty_rows=False, drop_empty_columns=False))
    assert len(cleaned) == 2
    assert report.duplicate_rows_removed == 0


def test_cleaning_makes_generated_column_names_unique():
    cleaned, _ = clean_dataframe(pd.DataFrame([[1, 2, 3]], columns=["x", "x", "x_2"]))
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
    assert dataset.source_validation is not None
    assert dataset.provenance is not None
    assert dataset.provenance.input_rows == 3
    with pytest.raises(KeyError):
        dataset.get_column("unknown")


def test_model_context_is_bounded_and_excludes_examples_by_default():
    df = pd.DataFrame({"email": ["private@example.com", "another@example.com"], "age": [21, 22]})
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


def test_preview_reports_before_and_after_without_mutating_input():
    df = pd.DataFrame({" name ": [" Alice ", "  ", "Bob"], "empty": [None, None, None]})
    original = df.copy(deep=True)
    preview = preview_dataframe(df, required_columns=["name"])
    assert preview.ready
    assert preview.source_rows == 3
    assert preview.cleaned_dataframe["name"].tolist() == ["Alice", "Bob"]
    assert any(issue.code == "ALL_NULL_COLUMN" for issue in preview.source_validation.warnings)
    assert preview.cleaning.empty_rows_removed == 1
    assert preview.cleaning.empty_columns_removed == 1
    pd.testing.assert_frame_equal(df, original)
    serialized = json.dumps(preview.to_dict(), allow_nan=False)
    assert "Alice" not in serialized
    assert "cleaned_dataframe" not in preview.to_dict()


def test_preview_reports_blocking_required_column_without_discarding_preview():
    df = pd.DataFrame({"name": ["Ada", "Linus"]})
    preview = preview_dataframe(df, required_columns=["customer_id"])
    assert not preview.ready
    assert any(issue.code == "MISSING_REQUIRED_COLUMN" for issue in preview.output_validation.errors)
    assert len(preview.cleaned_dataframe) == 2


def test_preview_file_and_prepare_file_share_source_provenance(tmp_path):
    path = tmp_path / "sales.csv"
    path.write_text("sales,region\n100,East\n200,West\n", encoding="utf-8")
    preview = preview_file(path, required_columns=["sales", "region"])
    prepared = prepare_file(path, required_columns=["sales", "region"])
    assert preview.ready
    assert preview.source_name == "sales.csv"
    assert prepared.provenance is not None
    assert prepared.provenance.source_name == "sales.csv"
    assert prepared.provenance.source_format == "csv"
    assert prepared.provenance.source_size_bytes == path.stat().st_size
    assert prepared.dataframe.equals(preview.cleaned_dataframe)



def test_cleaning_handles_duplicate_column_labels_when_uniqueness_is_disabled():
    df = pd.DataFrame(
        [[" Alice ", " Bob "], ["", "Carol"]],
        columns=["name", "name"],
    )
    original = df.copy(deep=True)
    config = CleaningConfig(make_column_names_unique=False)

    cleaned, report = clean_dataframe(df, config)

    assert cleaned.columns.tolist() == ["name", "name"]
    assert cleaned.iloc[0].tolist() == ["Alice", "Bob"]
    assert pd.isna(cleaned.iloc[1, 0])
    assert cleaned.iloc[1, 1] == "Carol"
    assert report.blank_strings_replaced == 1
    pd.testing.assert_frame_equal(df, original)


def test_dataset_to_dict_excludes_sensitive_profile_examples_by_default():
    df = pd.DataFrame({"email": ["private@example.com", "another@example.com"], "age": [21, 22]})
    dataset = prepare_dataset(df)

    serialized = dataset.to_dict()
    assert "private@example.com" not in json.dumps(serialized)
    assert "example_values" not in serialized["profile"]["column_profiles"][0]
    assert "top_values" not in serialized["profile"]["column_profiles"][0]

    with_examples = dataset.to_dict(include_value_examples=True)
    assert "private@example.com" in json.dumps(with_examples)


def test_required_columns_rejects_a_string_instead_of_iterating_characters():
    df = pd.DataFrame({"sales": [10], "region": ["East"]})

    with pytest.raises(TypeError, match="not a string"):
        validate_dataframe(df, required_columns="sales")
    with pytest.raises(TypeError, match="not a string"):
        prepare_dataset(df, required_columns="sales")


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), float("inf")])
def test_validation_rejects_out_of_range_or_non_finite_missing_thresholds(threshold):
    with pytest.raises(ValueError, match="between 0 and 1"):
        validate_dataframe(pd.DataFrame({"value": [1]}), max_missing_ratio=threshold)


@pytest.mark.parametrize("threshold", ["0.5", True, None])
def test_validation_rejects_non_numeric_missing_thresholds(threshold):
    with pytest.raises(TypeError, match="finite number"):
        validate_dataframe(pd.DataFrame({"value": [1]}), max_missing_ratio=threshold)


@pytest.mark.parametrize("source_size", [-1, 1.5, True, "10"])
def test_prepare_dataset_validates_source_size_type_and_range(source_size):
    df = pd.DataFrame({"value": [1]})
    if source_size == -1:
        error = ValueError
        message = "cannot be negative"
    else:
        error = TypeError
        message = "non-negative integer"
    with pytest.raises(error, match=message):
        prepare_dataset(df, source_size_bytes=source_size)


@pytest.mark.parametrize("limit_name", ["example_limit", "top_value_limit"])
@pytest.mark.parametrize("limit", [-1, 1.5, True])
def test_profile_limits_must_be_non_negative_integers(limit_name, limit):
    kwargs = {limit_name: limit}
    error = ValueError if limit == -1 else TypeError
    with pytest.raises(error, match="non-negative integer"):
        profile_dataframe(pd.DataFrame({"value": [1]}), **kwargs)


def test_profile_limit_zero_is_valid():
    profile = profile_dataframe(
        pd.DataFrame({"label": ["secret", "public"]}),
        example_limit=0,
        top_value_limit=0,
    )
    assert profile.column_profiles[0].example_values == ()
    assert profile.column_profiles[0].top_values == ()



def test_duplicate_check_skips_are_reported_as_unknown_not_zero(monkeypatch):
    df = pd.DataFrame({"payload": [{"private": "x"}, {"private": "y"}]})

    def unsupported_duplicate_check(self, *args, **kwargs):
        raise TypeError("synthetic unhashable values")

    monkeypatch.setattr(pd.DataFrame, "duplicated", unsupported_duplicate_check)

    profile = profile_dataframe(df)
    metadata = infer_schema(df)
    validation = validate_dataframe(df)

    assert profile.duplicate_rows is None
    assert profile.duplicate_check_skipped is True
    assert profile.to_dict()["duplicate_check_skipped"] is True
    assert metadata.duplicate_rows is None
    assert metadata.duplicate_check_skipped is True
    assert any(issue.code == "DUPLICATE_CHECK_SKIPPED" for issue in validation.warnings)


def test_cleaning_rename_details_preserve_duplicate_original_labels():
    df = pd.DataFrame([[1, 2]], columns=[" amount ", " amount "])

    cleaned, report = clean_dataframe(df)

    assert cleaned.columns.tolist() == ["amount", "amount_2"]
    # The backwards-compatible mapping cannot represent both duplicate keys.
    assert report.renamed_columns[" amount "] == "amount_2"
    assert report.renamed_column_details == (
        {"position": 0, "original_name": " amount ", "cleaned_name": "amount"},
        {"position": 1, "original_name": " amount ", "cleaned_name": "amount_2"},
    )
    assert report.to_dict()["renamed_column_details"][0]["position"] == 0


def test_loader_parses_csv_and_json_bytes_without_writing_to_disk():
    loader = DataLoader(max_file_size_bytes=1024)

    csv_frame = loader.load_bytes("customer.csv", b"sales,region\n100,East\n200,West\n")
    assert csv_frame.to_dict(orient="records") == [
        {"sales": 100, "region": "East"},
        {"sales": 200, "region": "West"},
    ]

    json_frame = loader.load_bytes("customers.json", b'[{"sales": 100, "region": "East"}]')
    assert json_frame.to_dict(orient="records") == [{"sales": 100, "region": "East"}]


def test_loader_bytes_enforces_type_extension_empty_and_size_limits():
    with pytest.raises(TypeError, match="positive integer"):
        DataLoader(max_file_size_bytes=True)
    with pytest.raises(TypeError, match="positive integer"):
        DataLoader(max_file_size_bytes=1.5)

    loader = DataLoader(max_file_size_bytes=4)
    with pytest.raises(ValueError, match="Unsupported file type"):
        loader.load_bytes("payload.exe", b"data")
    with pytest.raises(ValueError, match="empty"):
        loader.load_bytes("empty.csv", b"")
    with pytest.raises(ValueError, match="too large"):
        loader.load_bytes("large.csv", b"sales\n1\n")
    with pytest.raises(TypeError, match="bytes-like"):
        loader.load_bytes("sales.csv", "sales\n1\n")


def test_loader_bytes_sanitizes_filename_in_parse_errors():
    loader = DataLoader()
    with pytest.raises(ValueError, match="Could not parse dataset 'bad.csv'"):
        loader.load_bytes("../../bad.csv", b"\xff,\xfe")
