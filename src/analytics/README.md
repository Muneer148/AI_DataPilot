# Member 3 — Analytics & Visualization

> Owns deterministic calculations and charts based on the actual prepared dataset.
> Project: AI_DataPilot · target branch: feature/analytics.

## Responsibility boundary

Member 1 owns ingestion, cleaning, validation, schema, profiling and provenance. Member 2 owns natural-language interpretation and orchestration. Member 3 computes numerical results from the actual DataFrame. Member 4 owns API/UI integration. This module does not copy or merge Member 1's implementation.

**Design rule:** pandas and NumPy calculate; the LLM interprets; charts visualize returned calculation results.

## Public API

- describe_dataset(dataset, columns=None, quantiles=(0.25, 0.5, 0.75), max_columns=100)
- aggregate_dataset(dataset, group_by=(), aggregations=None, filters=None, sort_by=None, ascending=False, limit=100)
- correlate_dataset(dataset, columns=None, method="pearson", min_periods=2, max_pairs=1000, max_columns=100)
- trend_dataset(dataset, time_column, value_column, interval="day", aggregation="sum", timezone="UTC", limit=1000)
- detect_outliers(dataset, column, method="iqr", threshold=1.5, max_results=100)
- build_chart_spec(result, chart_type="bar", x=..., y=..., max_points=100)
- build_figure(result, chart_type="bar", x=..., y=..., max_points=100)

All analytics functions accept a pandas DataFrame or a prepared data-layer object exposing a DataFrame as .dataframe. Provenance and available validation warnings are carried forward. The prepared object is duck-typed so this branch does not duplicate Member 1's module. A contract integration test runs when `src.data` is present in the combined PR environment and skips on the isolated analytics branch.

Each analytics call returns AnalyticsResult. Use result.to_dict() for JSON-friendly data or result.to_json() for strict JSON. Invalid requests raise AnalyticsError with a stable code, message and details.

## Reproducible example

~~~python
import pandas as pd
from src.analytics import aggregate_dataset, describe_dataset
from src.visualization import build_chart_spec, build_figure

sales = pd.DataFrame({
    "region": ["East", "West", "East"],
    "sales": [100, 80, 120],
})
description = describe_dataset(sales)
summary = aggregate_dataset(
    sales,
    group_by=["region"],
    aggregations={"sales": ["sum", "mean", "count"]},
    sort_by="sales__sum",
    ascending=False,
)
print(description.to_json())
print(summary.to_dict())
spec = build_chart_spec(summary, chart_type="bar", x="region", y="sales__sum")
figure = build_figure(summary, chart_type="bar", x="region", y="sales__sum")
figure.write_html("sales_by_region.html")
~~~

## Module map for project review

- `contracts.py`: Defines `AnalyticsError`, `AnalyticsResult`, JSON-safe conversion, prepared-dataset extraction, numeric filtering, column checks, and result-limit checks.
- `descriptive.py`: Implements `describe_dataset` for row counts, missingness, finite numeric summaries, and quantiles.
- `aggregation.py`: Implements `aggregate_dataset` for filters, grouping, summary operations, stable sorting, and bounded records.
- `relationships.py`: Implements `correlate_dataset` for pairwise Pearson, Spearman, or Kendall correlations with pair-specific sample counts.
- `trends.py`: Implements `trend_dataset` for aggregating a numeric measure into time buckets.
- `outliers.py`: Implements `detect_outliers` with IQR fences or absolute population z-scores.
- `src/visualization/charts.py`: Implements `build_chart_spec` and `build_figure`. It plots returned analytics records; it does not repeat the statistical calculation.
- `tests/test_analytics.py` and `tests/test_visualization.py`: Contain deterministic examples and regression tests for the contracts above.

## Minimal examples for each capability

All examples can be run from the repository root. They use a small DataFrame and need no LLM or API key.

~~~python
import pandas as pd
from src.analytics import (
    aggregate_dataset,
    correlate_dataset,
    describe_dataset,
    detect_outliers,
    trend_dataset,
)
from src.visualization import build_chart_spec, build_figure

sales = pd.DataFrame({
    "region": ["East", "West", "East", "West"],
    "sales": [100.0, 80.0, 120.0, 200.0],
    "units": [2, 2, 3, 5],
    "date": ["2025-01-01", "2025-01-02", "2025-02-01", "2025-02-02"],
})

# 1. Describe selected columns.
description = describe_dataset(sales, columns=["sales"])
print(description.to_dict()["records"])

# 2. Filter rows, group by region, and sum sales.
summary = aggregate_dataset(
    sales,
    group_by=["region"],
    aggregations={"sales": "sum"},
    filters=[{"column": "sales", "operator": "gte", "value": 100}],
    sort_by="sales__sum",
    ascending=False,
)
print(summary.to_dict()["records"])

# 3. Measure a relationship between numeric columns.
correlations = correlate_dataset(
    sales, columns=["sales", "units"], method="pearson"
)
print(correlations.to_dict()["records"])

# 4. Aggregate sales into monthly time buckets.
monthly = trend_dataset(
    sales, time_column="date", value_column="sales",
    interval="month", aggregation="sum", timezone="UTC",
)
print(monthly.to_dict()["records"])

# 5. Flag unusual sales values for review.
outliers = detect_outliers(sales, column="sales", method="iqr")
print(outliers.to_dict()["records"])

# 6. Use the exact values from an analytics result to make a chart.
spec = build_chart_spec(summary, chart_type="bar", x="region", y="sales__sum")
figure = build_figure(summary, chart_type="bar", x="region", y="sales__sum")
figure.write_html("sales_by_region.html")
~~~

## Result shape and error handling

Every analytics function returns an `AnalyticsResult` with these fields:

- `operation`: stable operation name such as `describe`, `aggregate`, `correlation`, `trend`, or `outliers`.
- `columns`: source or output columns relevant to the operation.
- `row_count`: the number of rows considered by that operation (see each function's assumptions and metrics for more detail).
- `records`: a list of dictionaries containing returned values.
- `metrics`: operation totals such as possible correlation pairs or outlier candidates.
- `parameters`: normalized options used for the calculation.
- `warnings` and `assumptions`: information callers should retain when explaining a result.
- `provenance`: the prepared dataset's provenance when supplied by the data layer; it is `None` for a bare DataFrame.

Use `result.to_dict()` for JSON-friendly Python values or `result.to_json()` for strict JSON text. Missing and non-finite values are represented as JSON `null`; result errors use `AnalyticsError`, whose `code`, message, and JSON-safe details can be returned to an API client. Do not silently discard warnings: they can explain skipped rows or truncated results.

A chart specification returned by `build_chart_spec` contains `type`, `title`, `x` and `y` field/label objects, `data` (a list of `{"x": ..., "y": ...}` points), `source_operation`, `record_count`, and `warnings`. Bar, line, and scatter charts need finite numeric `y` values or nulls for missing points; `x` must be a scalar value. Pie charts require finite, non-negative numeric `y` values and do not accept null pie values. `build_figure` consumes the same bounded chart points to construct the Plotly figure; it does not calculate a new summary.

Column selection and correlation are limited to 100 columns by default (and at most 100). Correlation returns at most 1,000 pairs; chart specifications at most 1,000 points; and public result-limit arguments accept values from 1 to 1,000. The default limits are lower for aggregation (`limit=100`) and outlier candidates (`max_results=100`). Invalid columns, methods, intervals, filters, aggregation operations, and limit values raise `AnalyticsError` with a stable error code. Read the warnings and metrics to distinguish a complete result from a bounded or skipped-data result.

## Numerical and privacy policies

- Missing ratios use all rows as the denominator. An empty dataset has a zero missing ratio.
- Numeric calculations exclude positive and negative infinity and report or warn about them. Numeric-looking strings are not coerced.
- Standard deviation uses ddof=1 and is null when fewer than two usable values are available. Integer sums use Python integer accumulation to avoid fixed-width integer overflow; floating-point results still follow floating-point precision limits.
- Aggregation count counts non-null values; row_count counts all filtered rows in each group. Missing grouping keys are retained. Equality, inequality and negative-membership filters exclude missing values; use is_null/not_null for missingness.
- Correlation supports Pearson, Spearman and Kendall; it uses pairwise-complete finite observations and reports per-pair sample size. It analyzes at most 100 columns and returns at most 1,000 pairs by default; correlation does not prove causation.
- Numeric time columns are rejected rather than silently interpreted as nanoseconds. Missing measures and infinite measures are reported separately. Other trend timestamps are parsed with invalid values coerced to missing. Naive timestamps are interpreted as UTC; the requested timezone is applied before hour/day/week/month/quarter/year bucketing. Week buckets use pandas' weekly frequency and are labeled at the week end.
- Outlier flags use IQR or population z-score thresholds. They are candidates for investigation, not proof of error or fraud.
- Result records, returned columns and chart points are bounded. Pie charts require finite, non-negative numeric values. Outlier results omit unrelated row fields.
- Results are JSON-serializable; non-finite numbers become null. Charts use the same records returned by analytics and do not independently recompute values.

## Tests and integration

Run from the repository root:

~~~bash
python -m pytest -q
~~~

The GitHub Actions workflow runs the same test command on pushes and pull requests. Tests use synthetic fixtures and need no API keys or external services.

The latest feature/analytics branch did not contain the data-foundation code. That branch remains unmerged here; the API is compatible with its documented .dataframe and provenance fields. After the team approves integration, run the combined branch regression suite. Agent orchestration and UI/API wiring remain the responsibility of Members 2 and 4.
