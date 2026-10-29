import asyncio
from io import BytesIO

from fastapi import UploadFile

from app.main import (
    MAX_COLUMNS, MAX_ROWS, AppInputError, PreviewRequest, analyze_upload,
    parse_csv_text, preview, preview_upload, run_analysis,
)


SAMPLE = """month,product,selling_price,quantity
2026-01,Rice,48,10
2026-02,Rice,52,12
2026-03,Rice,55,13
"""


def test_parse_csv_text_reads_in_memory_dataset():
    frame = parse_csv_text(SAMPLE)
    assert frame.shape == (3, 4)
    assert list(frame.columns) == ["month", "product", "selling_price", "quantity"]


def test_analysis_returns_result_and_evidence():
    result = run_analysis(SAMPLE, "What is the average selling_price?")
    assert result["status"] == "ok"
    assert result["evidence"]["operation"] == "aggregate"
    assert abs(result["evidence"]["records"][0]["selling_price__mean"] - (155 / 3)) < 1e-10
    assert result["dataset"]["rows"] == 3


def test_unknown_column_returns_clarification_not_number():
    result = run_analysis(SAMPLE, "What is total profit?")
    assert result["status"] == "needs_clarification"
    assert result["evidence"] is None


def test_empty_or_duplicate_header_input_is_rejected():
    for bad in ("", "sales,sales\n1,2\n"):
        try:
            parse_csv_text(bad)
            assert False, "Expected AppInputError"
        except AppInputError:
            pass


def test_row_and_column_limits_are_enforced():
    too_many_rows = "x\n" + "\n".join(str(i) for i in range(MAX_ROWS + 1))
    try:
        parse_csv_text(too_many_rows)
        assert False, "Expected AppInputError"
    except AppInputError as exc:
        assert "rows" in str(exc)

    too_many_cols = ",".join(f"c{i}" for i in range(MAX_COLUMNS + 1)) + "\n" + ",".join("1" for _ in range(MAX_COLUMNS + 1))
    try:
        parse_csv_text(too_many_cols)
        assert False, "Expected AppInputError"
    except AppInputError as exc:
        assert "columns" in str(exc)



def test_server_preview_returns_cleaning_report_without_profile_examples():
    payload = PreviewRequest(csv_text=" sales , region \n10, East \n20,West\n")

    result = preview(payload)

    assert result["ready"] is True
    assert result["preview"]["source"]["rows"] == 2
    assert result["preview"]["preview_output"]["columns"] == ["sales", "region"]
    assert "example_values" not in result["preview"]["source_profile"]["column_profiles"][0]
    assert result["source_sample"]["records"][0][" sales "] == 10
    assert result["cleaned_sample"]["records"][0]["region"] == "East"


def test_analysis_can_use_explicitly_approved_prepared_dataset():
    text = " sales , region \n10, East \n20, West\n"

    result = run_analysis(text, "What is the average sales?", prepare=True)

    assert result["status"] == "ok"
    assert result["evidence"]["records"][0]["sales__mean"] == 15
    assert result["preparation"]["provenance"]["source_format"] == "csv"
    assert result["preparation"]["provenance"]["input_rows"] == 2
    assert result["evidence"]["provenance"]["source_name"] == "pasted.csv"


def test_upload_preview_reads_csv_bytes_without_temporary_file():
    upload = UploadFile(filename="sales.csv", file=BytesIO(b"sales,region\n100,East\n200,West\n"))

    result = asyncio.run(preview_upload(upload))

    assert result["ready"] is True
    assert result["preview"]["source"]["name"] == "sales.csv"
    assert result["preview"]["source"]["format"] == "csv"
    assert result["preview"]["source"]["size_bytes"] > 0


def test_upload_analyze_uses_same_preparation_contract():
    upload = UploadFile(filename="sales.csv", file=BytesIO(b" sales ,region\n10,East\n20,West\n"))

    result = asyncio.run(
        analyze_upload(
            file=upload,
            question="What is the average sales?",
            planner="rules",
            prepare=True,
        )
    )

    assert result["status"] == "ok"
    assert result["evidence"]["records"][0]["sales__mean"] == 15
    assert result["preparation"]["provenance"]["source_name"] == "sales.csv"


def test_upload_preview_rejects_unsupported_extension_cleanly():
    upload = UploadFile(filename="payload.exe", file=BytesIO(b"not a dataset"))

    result = asyncio.run(preview_upload(upload))

    assert result["status"] == "invalid_dataset"
    assert result["ready"] is False
    assert "supported extension" in result["clarification"].lower()
