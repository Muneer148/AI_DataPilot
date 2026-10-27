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
