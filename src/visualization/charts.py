from __future__ import annotations

from typing import Any, Mapping

from src.analytics.contracts import AnalyticsError, json_safe, validate_limit

SUPPORTED_CHART_TYPES = {"bar", "line", "scatter", "pie"}


def _as_result_dict(result: Any) -> dict[str, Any]:
    if callable(getattr(result, "to_dict", None)):
        result = result.to_dict()
    if not isinstance(result, Mapping):
        raise AnalyticsError("result must be an AnalyticsResult or mapping", code="INVALID_CHART_RESULT")
    records = result.get("records", [])
    if not isinstance(records, list) or any(not isinstance(row, Mapping) for row in records):
        raise AnalyticsError("result.records must be a list of objects", code="INVALID_CHART_RESULT")
    return dict(result)


def build_chart_spec(result: Any, *, chart_type: str = "bar", x: str, y: str, title: str | None = None, max_points: int = 100) -> dict[str, Any]:
    """Create a bounded chart spec from the result records; do not recalculate analytics."""
    source = _as_result_dict(result)
    if chart_type not in SUPPORTED_CHART_TYPES:
        raise AnalyticsError(f"chart_type must be one of {sorted(SUPPORTED_CHART_TYPES)}", code="INVALID_CHART_TYPE")
    if not isinstance(x, str) or not x or not isinstance(y, str) or not y:
        raise AnalyticsError("x and y must be non-empty field names", code="INVALID_CHART_FIELDS")
    max_points = validate_limit(max_points, parameter="max_points")
    records = source.get("records", [])
    missing = sorted({field for field in (x, y) if any(field not in row for row in records)})
    if missing:
        raise AnalyticsError(f"Chart fields are missing from result records: {missing}", code="UNKNOWN_CHART_FIELD", details={"fields": missing})
    warnings = list(source.get("warnings") or [])
    if not records:
        warnings.append("No result records were available to plot.")
        points = []
    else:
        if len(records) > max_points:
            warnings.append(f"Chart data was limited to {max_points} of {len(records)} result records.")
        points = [{"x": json_safe(row.get(x)), "y": json_safe(row.get(y))} for row in records[:max_points]]
    return {
        "type": chart_type, "title": title or f"{str(source.get('operation', 'Analysis')).title()}: {y} by {x}",
        "x": {"field": x, "label": x}, "y": {"field": y, "label": y}, "data": points,
        "source_operation": source.get("operation"), "record_count": len(points),
        "warnings": list(dict.fromkeys(warnings)),
    }


def build_figure(result: Any, *, chart_type: str = "bar", x: str, y: str, title: str | None = None, max_points: int = 100):
    """Create a Plotly figure from the same bounded values used by build_chart_spec."""
    spec = build_chart_spec(result, chart_type=chart_type, x=x, y=y, title=title, max_points=max_points)
    import plotly.graph_objects as go

    xs = [point["x"] for point in spec["data"]]
    ys = [point["y"] for point in spec["data"]]
    figure = go.Figure()
    if chart_type == "bar":
        figure.add_trace(go.Bar(x=xs, y=ys, name=spec["y"]["label"]))
    elif chart_type == "line":
        figure.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=spec["y"]["label"]))
    elif chart_type == "scatter":
        figure.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=spec["y"]["label"]))
    else:
        figure.add_trace(go.Pie(labels=xs, values=ys, name=spec["y"]["label"]))
    figure.update_layout(title=spec["title"], xaxis_title=None if chart_type == "pie" else spec["x"]["label"], yaxis_title=None if chart_type == "pie" else spec["y"]["label"], template="plotly_white", meta=spec)
    return figure
