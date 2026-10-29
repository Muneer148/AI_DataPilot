"""Runtime plan contract shared by every planner before analytics execution."""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.analytics.contracts import AnalyticsError, get_dataset_context

from .planner import AnalysisPlan

_ALLOWED_OPERATIONS = {"describe", "aggregate", "count_rows", "correlation"}
_ALLOWED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count", "count_rows"}
_NUMERIC_AGGREGATIONS = {"sum", "mean", "median"}
_MAX_PLAN_RESULT_ROWS = 100


def _invalid(message: str, code: str = "INVALID_PLAN", **details: Any) -> AnalyticsError:
    return AnalyticsError(message, code=code, details=details)


def validate_plan(plan: Any, dataset: Any) -> AnalysisPlan:
    """Validate types, operation shape, schema references and bounds before execution.

    This function is intentionally applied in the orchestrator after *any* planner
    returns. Provider-side checks remain useful, but are not the execution boundary.
    """
    if not isinstance(plan, AnalysisPlan):
        raise _invalid("The planner did not return a valid AnalysisPlan.")

    if not isinstance(plan.operation, str) or plan.operation not in _ALLOWED_OPERATIONS:
        raise _invalid("The plan requested an unsupported operation.", operation=repr(plan.operation))
    if plan.metric_column is not None and not isinstance(plan.metric_column, str):
        raise _invalid("The metric column must be a string or null.")
    if not isinstance(plan.group_by, tuple) or any(not isinstance(column, str) for column in plan.group_by):
        raise _invalid("group_by must be a tuple of column-name strings.")
    if len(set(plan.group_by)) != len(plan.group_by):
        raise _invalid("group_by cannot contain duplicate columns.")
    if plan.aggregation is not None and not isinstance(plan.aggregation, str):
        raise _invalid("The aggregation must be a string or null.")
    if isinstance(plan.limit, bool) or not isinstance(plan.limit, int) or not 1 <= plan.limit <= _MAX_PLAN_RESULT_ROWS:
        raise _invalid(
            f"The result limit must be an integer between 1 and {_MAX_PLAN_RESULT_ROWS}.",
            code="INVALID_LIMIT",
            maximum=_MAX_PLAN_RESULT_ROWS,
        )
    if not isinstance(plan.reason, str):
        raise _invalid("The plan reason must be a string.")

    dataframe, _, _ = get_dataset_context(dataset)
    if dataframe.empty:
        raise _invalid("The dataset has no rows to analyze.", code="EMPTY_DATASET")

    available = list(dataframe.columns)
    requested = list(plan.group_by)
    if plan.metric_column is not None:
        requested.append(plan.metric_column)
    unknown = [column for column in requested if column not in available]
    if unknown:
        raise _invalid(
            "The plan references columns that do not exist. Please clarify the column names.",
            code="UNKNOWN_COLUMN",
            columns=list(dict.fromkeys(unknown)),
        )

    operation = plan.operation
    metric = plan.metric_column
    groups = plan.group_by
    aggregation = plan.aggregation

    if operation == "describe":
        if metric is not None or groups or aggregation is not None:
            raise _invalid("A dataset summary cannot include metric, grouping, or aggregation arguments.")
        return plan

    if operation == "count_rows":
        if metric is not None or groups or aggregation not in {None, "count_rows"}:
            raise _invalid("A row-count plan cannot include a metric, grouping, or value aggregation.")
        return plan

    if operation == "correlation":
        if metric is not None or aggregation is not None or len(groups) != 2 or groups[0] == groups[1]:
            raise _invalid("Correlation requires exactly two distinct numeric columns.")
        for column in groups:
            series = dataframe[column]
            if (
                not pd.api.types.is_numeric_dtype(series.dtype)
                or pd.api.types.is_bool_dtype(series.dtype)
                or pd.api.types.is_complex_dtype(series.dtype)
            ):
                raise _invalid(
                    "Correlation requires real numeric columns.",
                    code="NON_NUMERIC_COLUMN",
                    column=column,
                    dtype=str(series.dtype),
                )
        return plan

    # The aggregate operation supports at most one grouping dimension in this MVP.
    if len(groups) > 1:
        raise _invalid("This MVP supports only one grouping column per aggregation.")
    if aggregation == "count_rows":
        if metric is not None:
            raise _invalid("Grouped row count must not specify a metric column.")
        return plan
    if metric is None or not metric.strip():
        raise _invalid("An aggregation requires one metric column.")
    if aggregation not in _ALLOWED_AGGREGATIONS - {"count_rows"}:
        raise _invalid(
            "The plan requested an unsupported aggregation.",
            code="INVALID_AGGREGATION",
            allowed=sorted(_ALLOWED_AGGREGATIONS - {"count_rows"}),
        )
    if metric in groups:
        raise _invalid("The metric and grouping column must be different.")

    metric_series = dataframe[metric]
    if aggregation in _NUMERIC_AGGREGATIONS and (
        not pd.api.types.is_numeric_dtype(metric_series.dtype)
        or pd.api.types.is_bool_dtype(metric_series.dtype)
        or pd.api.types.is_complex_dtype(metric_series.dtype)
    ):
        raise _invalid(
            f"Aggregation '{aggregation}' requires a real numeric metric column.",
            code="NON_NUMERIC_COLUMN",
            column=metric,
            dtype=str(metric_series.dtype),
        )
    if aggregation in {"min", "max"} and pd.api.types.is_complex_dtype(metric_series.dtype):
        raise _invalid(
            f"Aggregation '{aggregation}' does not support complex values.",
            code="NON_NUMERIC_COLUMN",
            column=metric,
            dtype=str(metric_series.dtype),
        )
    return plan
