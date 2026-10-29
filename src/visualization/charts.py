from __future__ import annotations

import math
import numbers
from typing import Any, Mapping

from src.analytics.contracts import AnalyticsError, json_safe, validate_limit

SUPPORTED_CHART_TYPES = {"bar", "line", "scatter", "pie"}


def _is_finite_number(value: Any) -> bool:
    """Return whether a numeric value is representable as a finite chart number."""
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


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
    if not isinstance(chart_type, str) or chart_type not in SUPPORTED_CHART_TYPES:
        raise AnalyticsError(
            f"chart_type must be one of {sorted(SUPPORTED_CHART_TYPES)}",
            code="INVALID_CHART_TYPE",
        )
    if not isinstance(x, str) or not x or not isinstance(y, str) or not y:
        raise AnalyticsError("x and y must be non-empty field names", code="INVALID_CHART_FIELDS")
    if title is not None and not isinstance(title, str):
        raise AnalyticsError("title must be a string", code="INVALID_CHART_TITLE")
    max_points = validate_limit(max_points, parameter="max_points")
    operation = source.get("operation")
    if operation is not None and not isinstance(operation, str):
        raise AnalyticsError(
            "result.operation must be a string",
            code="INVALID_CHART_RESULT",
        )

    raw_parameters = source.get("parameters")
    if raw_parameters is None:
        parameters = {}
    elif not isinstance(raw_parameters, Mapping):
        raise AnalyticsError(
            "result.parameters must be a mapping",
            code="INVALID_CHART_RESULT",
        )
    else:
        parameters = raw_parameters

    records = source.get("records", [])
    known_fields = set()
    returned_columns = parameters.get("returned_columns") if isinstance(parameters, Mapping) else None
    if isinstance(returned_columns, list) and all(isinstance(field, str) for field in returned_columns):
        known_fields.update(returned_columns)
    operation_fields = {
        "describe": {
            "column", "dtype", "non_null_count", "missing_count", "missing_ratio",
            "numeric_count", "non_finite_count", "sum", "mean", "median", "min",
            "max", "std", "quantiles",
        },
        "correlation": {"column_a", "column_b", "correlation", "sample_size"},
        "trend": {"period", "value"},
        "outliers": {
            "row_position", "value", "outlier_score", "side", "lower_fence", "upper_fence",
        },
    }
    known_fields.update(operation_fields.get(operation, set()))
    missing = sorted({
        field for field in (x, y)
        if (
            any(field not in row for row in records)
            if records
            else bool(known_fields) and field not in known_fields
        )
    })
    if missing:
        raise AnalyticsError(
            f"Chart fields are missing from result records: {missing}",
            code="UNKNOWN_CHART_FIELD",
            details={"fields": missing},
        )
    raw_warnings = source.get("warnings", [])
    if raw_warnings is None:
        raw_warnings = []
    if not isinstance(raw_warnings, list) or any(not isinstance(warning, str) for warning in raw_warnings):
        raise AnalyticsError("result.warnings must be a list of strings", code="INVALID_CHART_RESULT")
    warnings = list(raw_warnings)
    if not records:
        warnings.append("No result records were available to plot.")
        points = []
    else:
        if len(records) > max_points:
            warnings.append(f"Chart data was limited to {max_points} of {len(records)} result records.")
        bounded_records = records[:max_points]
        for index, row in enumerate(bounded_records):
            raw_x = row.get(x)
            if (
                isinstance(raw_x, numbers.Real)
                and not isinstance(raw_x, bool)
                and not _is_finite_number(raw_x)
            ):
                raise AnalyticsError(
                    "Chart x values must be finite numbers or null",
                    code="INVALID_CHART_VALUES",
                    details={"field": x, "record_index": index},
                )
            x_value = json_safe(raw_x)
            if x_value is not None and not isinstance(
                x_value, (str, int, float, bool)
            ):
                raise AnalyticsError(
                    "Chart x values must be scalar strings, numbers, booleans, or null",
                    code="INVALID_CHART_VALUES",
                    details={"field": x, "record_index": index},
                )

            raw_y = row.get(y)
            if chart_type != "pie" and (
                raw_y is not None
                and isinstance(raw_y, numbers.Real)
                and not isinstance(raw_y, bool)
                and not _is_finite_number(raw_y)
            ):
                raise AnalyticsError(
                    "Chart y values must be finite numbers or null",
                    code="INVALID_CHART_VALUES",
                    details={"field": y, "record_index": index},
                )

            y_value = json_safe(raw_y)
            if chart_type != "pie" and y_value is not None:
                valid_numeric = (
                    isinstance(y_value, numbers.Real)
                    and not isinstance(y_value, bool)
                )
                if not valid_numeric:
                    raise AnalyticsError(
                        "Bar, line, and scatter charts require numeric or null y values",
                        code="INVALID_CHART_VALUES",
                        details={"field": y, "record_index": index},
                    )

        if chart_type == "pie":
            for index, row in enumerate(bounded_records):
                value = row.get(y)
                valid_pie_value = (
                    isinstance(value, numbers.Real)
                    and not isinstance(value, bool)
                )
                if valid_pie_value:
                    try:
                        numeric_value = float(value)
                        valid_pie_value = math.isfinite(numeric_value) and numeric_value >= 0
                    except (OverflowError, TypeError, ValueError):
                        valid_pie_value = False
                if not valid_pie_value:
                    raise AnalyticsError(
                        "Pie charts require finite, non-negative numeric values in the y field",
                        code="INVALID_PIE_VALUES",
                        details={"field": y, "record_index": index, "value": json_safe(value)},
                    )
        points = [{"x": json_safe(row.get(x)), "y": json_safe(row.get(y))} for row in bounded_records]
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
