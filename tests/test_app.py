from app.main import MAX_COLUMNS, MAX_ROWS, AppInputError, parse_csv_text, run_analysis


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
