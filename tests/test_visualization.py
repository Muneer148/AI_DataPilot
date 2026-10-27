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


@pytest.mark.parametrize("bad_value", ["many", [1, 2], {"amount": 3}, True])
def test_non_pie_charts_reject_non_numeric_y_values(bad_value):
    result = {
        "operation": "aggregate",
        "records": [{"label": "East", "value": bad_value}],
    }
    with pytest.raises(AnalyticsError, match="require numeric or null y values"):
        build_chart_spec(result, chart_type="bar", x="label", y="value")


@pytest.mark.parametrize("bad_label", [[1, 2], {"region": "East"}])
def test_charts_reject_nested_x_values(bad_label):
    result = {
        "operation": "aggregate",
        "records": [{"label": bad_label, "value": 10}],
    }
    with pytest.raises(AnalyticsError, match="x values must be scalar"):
        build_chart_spec(result, chart_type="bar", x="label", y="value")


@pytest.mark.parametrize("bad_value", [float("inf"), float("nan"), 10**400])
def test_non_pie_charts_reject_non_finite_or_unrepresentable_y_values(bad_value):
    result = {
        "operation": "aggregate",
        "records": [{"label": "East", "value": bad_value}],
    }
    with pytest.raises(AnalyticsError, match="y values must be finite numbers"):
        build_chart_spec(result, chart_type="bar", x="label", y="value")


def test_charts_reject_non_finite_numeric_x_values():
    result = {
        "operation": "aggregate",
        "records": [{"label": float("inf"), "value": 10}],
    }
    with pytest.raises(AnalyticsError, match="x values must be finite numbers"):
        build_chart_spec(result, chart_type="scatter", x="label", y="value")


def test_non_pie_charts_allow_null_y_values_for_missing_points():
    result = {
        "operation": "aggregate",
        "records": [{"label": "East", "value": 10}, {"label": "West", "value": None}],
    }
    spec = build_chart_spec(result, chart_type="line", x="label", y="value")
    assert spec["data"] == [
        {"x": "East", "y": 10},
        {"x": "West", "y": None},
    ]


def test_chart_builder_rejects_malformed_result_metadata_with_clear_errors():
    with pytest.raises(AnalyticsError, match="result.parameters must be a mapping"):
        build_chart_spec(
            {"operation": "aggregate", "records": [], "parameters": ["bad"]},
            x="x",
            y="y",
        )
    with pytest.raises(AnalyticsError, match="result.operation must be a string"):
        build_chart_spec(
            {"operation": ["aggregate"], "records": []},
            x="x",
            y="y",
        )
    with pytest.raises(AnalyticsError, match="title must be a string"):
        build_chart_spec(
            {"operation": "aggregate", "records": [{"x": "A", "y": 1}]},
            x="x",
            y="y",
            title=["bad"],
        )
