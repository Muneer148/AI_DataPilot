"""Smoke tests for the user-facing data-foundation demonstration."""

import json

import pandas as pd

from examples.data_foundation_demo import main


def test_demo_previews_without_preparing_or_emitting_example_values(capsys):
    exit_code = main([])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["stage"] == "preview"
    assert payload["ready"] is True
    assert payload["prepared"] is False
    assert payload["preview"]["proposed_cleaning"]["empty_rows_removed"] == 1
    assert "priority" not in output.out
    assert "repeat" not in output.out


def test_demo_prepares_only_after_explicit_flag_and_omits_raw_rows(tmp_path, capsys):
    path = tmp_path / "private_sales.csv"
    pd.DataFrame(
        {
            "sales": [10, 20],
            "region": ["East", "West"],
            "contact": ["customer@example.com", "another@example.com"],
        }
    ).to_csv(path, index=False)

    exit_code = main(
        [
            str(path),
            "--prepare",
            "--required-column",
            "sales",
            "--required-column",
            "region",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["stage"] == "prepared"
    assert payload["prepared"] is True
    assert payload["dataset"]["rows"] == 2
    assert payload["dataset"]["provenance"]["source_name"] == path.name
    assert payload["dataset"]["model_context"]["data_access"]["raw_rows_included"] is False
    assert "customer@example.com" not in output.out
    assert "another@example.com" not in output.out


def test_demo_blocks_prepare_when_required_column_is_missing(tmp_path, capsys):
    path = tmp_path / "incomplete.csv"
    pd.DataFrame({"sales": [10, 20]}).to_csv(path, index=False)

    exit_code = main(
        [
            str(path),
            "--prepare",
            "--required-column",
            "region",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["ready"] is False
    assert payload["prepared"] is False
    assert any(
        issue["code"] == "MISSING_REQUIRED_COLUMN"
        for issue in payload["preview"]["output_validation"]["errors"]
    )
