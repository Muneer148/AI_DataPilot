import pandas as pd
import pytest

from src.analytics import AnalyticsError, aggregate_dataset
from src.visualization import build_chart_spec, build_figure


def result_fixture():
    return aggregate_dataset(pd.DataFrame({"region": ["East", "West", "East"], "sales": [10, 20, 30]}), group_by=["region"], aggregations={"sales": "sum"}, sort_by="sales__sum", ascending=False)


def test_chart_spec_uses_exact_returned_analytics_rows():
    result = result_fixture()
    spec = build_chart_spec(result, chart_type="bar", x="region", y="sales__sum")
    assert spec["source_operation"] == "aggregate"
    assert spec["data"] == [{"x": row["region"], "y": row["sales__sum"]} for row in result.to_dict()["records"]]


def test_plotly_figure_uses_same_x_and_y_values_as_spec():
    result = result_fixture()
    spec = build_chart_spec(result, x="region", y="sales__sum")
    figure = build_figure(result, x="region", y="sales__sum")
    assert list(figure.data[0].x) == [point["x"] for point in spec["data"]]
    assert list(figure.data[0].y) == [point["y"] for point in spec["data"]]
    assert figure.layout.title.text


def test_empty_and_high_cardinality_charts_are_bounded():
    empty = build_chart_spec({"operation": "aggregate", "records": [], "warnings": []}, x="group", y="amount")
    assert empty["data"] == []
    assert empty["record_count"] == 0
    many = {"operation": "aggregate", "records": [{"x": i, "y": i * 2} for i in range(20)]}
    limited = build_chart_spec(many, x="x", y="y", max_points=5)
    assert len(limited["data"]) == 5
    assert any("limited" in warning for warning in limited["warnings"])


def test_chart_rejects_missing_fields_and_unsupported_type():
    result = result_fixture()
    with pytest.raises(AnalyticsError, match="missing from result"):
        build_chart_spec(result, x="missing", y="sales__sum")
    with pytest.raises(AnalyticsError, match="chart_type"):
        build_chart_spec(result, chart_type="radar", x="region", y="sales__sum")


def test_pie_chart_rejects_non_numeric_negative_and_infinite_values():
    for value in ("many", -1, float("inf")):
        with pytest.raises(AnalyticsError, match="Pie charts require"):
            build_chart_spec(
                {"operation": "aggregate", "records": [{"label": "East", "value": value}]},
                chart_type="pie",
                x="label",
                y="value",
            )


def test_empty_aggregate_chart_checks_known_result_fields():
    empty = aggregate_dataset(
        pd.DataFrame({
            "region": pd.Series(dtype=object),
            "sales": pd.Series(dtype=float),
        }),
        group_by=["region"],
        aggregations={"sales": "sum"},
    )
    spec = build_chart_spec(empty, x="region", y="sales__sum")
    assert spec["data"] == []
    with pytest.raises(AnalyticsError, match="missing from result"):
        build_chart_spec(empty, x="unknown", y="sales__sum")


def test_chart_result_warning_metadata_and_limit_are_validated():
    with pytest.raises(AnalyticsError, match="warnings must be a list"):
        build_chart_spec(
            {"operation": "aggregate", "records": [{"x": "A", "y": 1}], "warnings": "oops"},
            x="x",
            y="y",
        )
    with pytest.raises(AnalyticsError, match="max_points"):
        build_chart_spec(
            {"operation": "aggregate", "records": [{"x": "A", "y": 1}]},
            x="x",
            y="y",
            max_points=0,
        )
