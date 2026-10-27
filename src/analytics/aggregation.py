from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from .contracts import AnalyticsError, AnalyticsResult, finite_numeric_series, get_dataset_context, json_safe, sum_numeric_values, validate_columns, validate_limit

SUPPORTED_AGGREGATIONS = {"count", "sum", "mean", "median", "min", "max", "std"}
NUMERIC_AGGREGATIONS = {"sum", "mean", "median", "std"}


def _apply_filters(dataframe: pd.DataFrame, filters: Sequence[Mapping[str, Any]] | None):
    if filters is None:
        return dataframe.copy(), []
    if not isinstance(filters, Sequence) or isinstance(filters, (str, bytes, Mapping)):
        raise AnalyticsError(
            "filters must be a list or tuple of filter objects",
            code="INVALID_FILTERS",
        )
    work = dataframe.copy()
    normalized = []
    allowed = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "is_null", "not_null", "contains"}
    for i, item in enumerate(filters):
        if not isinstance(item, Mapping):
            raise AnalyticsError("Each filter must be a mapping", code="INVALID_FILTER", details={"filter_index": i})
        column, operator, value = item.get("column"), item.get("operator"), item.get("value")
        if not isinstance(column, str) or column not in dataframe.columns:
            raise AnalyticsError(f"Unknown filter column: {column!r}", code="UNKNOWN_COLUMN", details={"filter_index": i, "column": column})
        if not isinstance(operator, str) or operator not in allowed:
            raise AnalyticsError(
                f"Unsupported filter operator: {operator!r}",
                code="INVALID_FILTER_OPERATOR",
                details={"allowed": sorted(allowed)},
            )
        series = work[column]
        try:
            if operator in {"eq", "ne", "gt", "gte", "lt", "lte"} and not pd.api.types.is_scalar(value):
                raise AnalyticsError(
                    "Comparison filter values must be scalar",
                    code="INVALID_FILTER_VALUE",
                    details={"filter_index": i, "operator": operator},
                )
            if operator in {"eq", "ne"}:
                if value is None or bool(pd.isna(value)):
                    raise AnalyticsError(
                        "Use is_null or not_null to filter missing values",
                        code="INVALID_FILTER_VALUE",
                    )
                comparison = series.eq(value) if operator == "eq" else series.ne(value)
                # Missing values should use is_null/not_null, not eq/ne.
                mask = comparison.fillna(False) & series.notna()
            elif operator in {"gt", "gte", "lt", "lte"}:
                mask = {"gt": series.gt, "gte": series.ge, "lt": series.lt, "lte": series.le}[operator](value).fillna(False)
            elif operator in {"in", "not_in"}:
                if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple, set)):
                    raise AnalyticsError(f"{operator} value must be a list, tuple or set", code="INVALID_FILTER_VALUE")
                membership_values = list(value)
                try:
                    for member in membership_values:
                        hash(member)
                except TypeError as exc:
                    raise AnalyticsError(
                        f"{operator} values must be hashable",
                        code="INVALID_FILTER_VALUE",
                    ) from exc
                mask = series.isin(membership_values)
                if operator == "not_in":
                    # Keep missing values out of negative membership filters too.
                    mask = ~mask & series.notna()
            elif operator == "is_null":
                mask = series.isna()
            elif operator == "not_null":
                mask = series.notna()
            else:
                non_null = series.dropna()
                if not isinstance(value, str) or not non_null.map(lambda x: isinstance(x, str)).all():
                    raise AnalyticsError(
                        "contains filters require a string column and a string value",
                        code="INVALID_FILTER_VALUE",
                    )
                mask = series.str.contains(value, regex=False, na=False)
        except AnalyticsError:
            raise
        except (TypeError, ValueError) as exc:
            raise AnalyticsError("Filter value is incompatible with the selected column", code="FILTER_TYPE_MISMATCH", details={"filter_index": i, "column": column, "operator": operator}) from exc
        work = work.loc[mask].copy()
        entry = {"column": column, "operator": operator}
        if operator not in {"is_null", "not_null"}:
            entry["value"] = json_safe(value)
        normalized.append(entry)
    return work, normalized


def _aggregate_series(series: pd.Series, operation: str, column: str):
    if operation == "count":
        return int(series.count())
    if operation in NUMERIC_AGGREGATIONS or (operation in {"min", "max"} and pd.api.types.is_numeric_dtype(series.dtype)):
        values, _ = finite_numeric_series(series, column)
        values = values.dropna()
    else:
        values = series.dropna()
    if values.empty:
        return None if operation != "count" else 0
    try:
        if operation == "sum":
            return json_safe(sum_numeric_values(values))
        if operation == "mean":
            return json_safe(values.mean())
        if operation == "median":
            return json_safe(values.median())
        if operation == "min":
            return json_safe(values.min())
        if operation == "max":
            return json_safe(values.max())
        if operation == "std":
            return json_safe(values.std(ddof=1)) if len(values) > 1 else None
    except (TypeError, ValueError, OverflowError) as exc:
        raise AnalyticsError(f"Aggregation '{operation}' is incompatible with '{column}'", code="INCOMPATIBLE_AGGREGATION", details={"column": column, "aggregation": operation}) from exc
    raise AnalyticsError(f"Unsupported aggregation '{operation}'", code="INVALID_AGGREGATION")


def aggregate_dataset(
    dataset: Any,
    *,
    group_by: Sequence[str] = (),
    aggregations: Mapping[str, str | Sequence[str]] | None = None,
    filters: Sequence[Mapping[str, Any]] | None = None,
    sort_by: str | None = None,
    ascending: bool = False,
    limit: int = 100,
) -> AnalyticsResult:
    """Perform bounded group-by aggregation and supported comparisons."""
    dataframe, provenance, warnings = get_dataset_context(dataset)
    groups = validate_columns(dataframe, group_by, parameter="group_by", allow_empty=True)
    if "row_count" in groups:
        raise AnalyticsError("row_count is reserved for the group-size output field", code="RESERVED_OUTPUT_COLUMN")
    limit = validate_limit(limit)
    if not isinstance(ascending, bool):
        raise AnalyticsError("ascending must be a boolean", code="INVALID_SORT")
    if aggregations is None:
        aggregations = {}
    if not isinstance(aggregations, Mapping):
        raise AnalyticsError("aggregations must map source columns to operation names", code="INVALID_AGGREGATIONS")
    normalized_aggs = {}
    for column, ops in aggregations.items():
        validate_columns(dataframe, [column], parameter="aggregations")
        if isinstance(ops, str):
            operation_list = [ops]
        elif isinstance(ops, Sequence) and not isinstance(ops, (str, bytes)):
            operation_list = list(ops)
        else:
            operation_list = None

        if not operation_list:
            raise AnalyticsError(
                f"Aggregations for '{column}' must be a name or non-empty sequence",
                code="INVALID_AGGREGATIONS",
            )
        if any(not isinstance(operation, str) for operation in operation_list):
            raise AnalyticsError(
                f"Aggregation names for '{column}' must be strings",
                code="INVALID_AGGREGATIONS",
                details={"column": column},
            )
        if len(set(operation_list)) != len(operation_list):
            raise AnalyticsError(
                f"Duplicate aggregation names for '{column}'",
                code="DUPLICATE_AGGREGATIONS",
            )
        for operation in operation_list:
            if operation not in SUPPORTED_AGGREGATIONS:
                raise AnalyticsError(
                    f"Unsupported aggregation '{operation}'",
                    code="INVALID_AGGREGATION",
                    details={"allowed": sorted(SUPPORTED_AGGREGATIONS)},
                )
            series = dataframe[column]
            if operation in NUMERIC_AGGREGATIONS and (not pd.api.types.is_numeric_dtype(series.dtype) or pd.api.types.is_bool_dtype(series.dtype) or pd.api.types.is_complex_dtype(series.dtype)):
                raise AnalyticsError(f"Aggregation '{operation}' requires a real numeric column", code="NON_NUMERIC_COLUMN", details={"column": column, "dtype": str(series.dtype)})
            if operation in {"min", "max"} and pd.api.types.is_complex_dtype(series.dtype):
                raise AnalyticsError(f"Aggregation '{operation}' does not support complex values", code="INCOMPATIBLE_AGGREGATION")
        normalized_aggs[column] = operation_list

    work, normalized_filters = _apply_filters(dataframe, filters)
    if groups:
        if normalized_aggs:
            grouped = work.groupby(groups, dropna=False, sort=False, observed=True)
            pieces = [grouped.size().rename("row_count")]
            for column, ops in normalized_aggs.items():
                for operation in ops:
                    name = f"{column}__{operation}"
                    if name in groups or name == "row_count":
                        raise AnalyticsError(f"Output name collision: {name}", code="OUTPUT_NAME_COLLISION")
                    pieces.append(grouped[column].agg(lambda values, op=operation, col=column: _aggregate_series(values, op, col)).rename(name))
            result_frame = pd.concat(pieces, axis=1).reset_index()
        else:
            result_frame = work.groupby(groups, dropna=False, sort=False, observed=True).size().rename("row_count").reset_index()
    else:
        row = {"row_count": int(len(work))}
        for column, ops in normalized_aggs.items():
            for operation in ops:
                name = f"{column}__{operation}"
                if name == "row_count":
                    raise AnalyticsError("Output name collision: row_count", code="OUTPUT_NAME_COLLISION")
                row[name] = _aggregate_series(work[column], operation, column)
        result_frame = pd.DataFrame([row])

    if sort_by is not None:
        if not isinstance(sort_by, str):
            raise AnalyticsError("sort_by must be a returned column name", code="INVALID_SORT_COLUMN")
        if sort_by not in result_frame.columns:
            raise AnalyticsError(
                f"sort_by must be one of {result_frame.columns.tolist()}",
                code="INVALID_SORT_COLUMN",
                details={"sort_by": sort_by},
            )
        try:
            result_frame = result_frame.sort_values(sort_by, ascending=ascending, kind="mergesort", na_position="last")
        except (TypeError, ValueError) as exc:
            raise AnalyticsError(f"Cannot sort by '{sort_by}'", code="INVALID_SORT", details={"sort_by": sort_by}) from exc

    group_count = len(result_frame)
    if group_count > limit:
        warnings.append(f"Aggregation produced {group_count} groups; output was limited to {limit} records.")
        result_frame = result_frame.head(limit)
    records = json_safe(result_frame.to_dict(orient="records"))
    return AnalyticsResult(
        operation="aggregate", columns=list(dict.fromkeys([*groups, *normalized_aggs.keys()])),
        row_count=len(work), records=records,
        metrics={"group_count": group_count, "returned_group_count": len(records)},
        parameters={"group_by": groups, "aggregations": normalized_aggs, "filters": normalized_filters, "sort_by": sort_by, "ascending": ascending, "limit": limit, "returned_columns": list(result_frame.columns)},
        warnings=list(dict.fromkeys(warnings)),
        assumptions=[
            "row_count is the number of filtered rows in a group; count counts non-null values.",
            "Numeric calculations exclude infinities; count retains pandas non-null semantics.",
            "Missing grouping values are retained as a group.",
            "No string-to-number conversion is performed.",
            "Without grouping dimensions, global aggregation returns one record even for empty filtered input.",
        ],
        provenance=provenance,
    )
