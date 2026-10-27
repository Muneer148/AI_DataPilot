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

All analytics functions accept a pandas DataFrame or a prepared data-layer object exposing a DataFrame as .dataframe. Provenance and available validation warnings are carried forward. The prepared object is duck-typed so this branch does not duplicate Member 1's module.

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

## Numerical and privacy policies

- Missing ratios use all rows as the denominator. An empty dataset has a zero missing ratio.
- Numeric calculations exclude positive and negative infinity and report or warn about them. Numeric-looking strings are not coerced.
- Standard deviation uses ddof=1 and is null when fewer than two usable values are available.
- Aggregation count counts non-null values; row_count counts all filtered rows in each group. Missing grouping keys are retained. Equality, inequality and negative-membership filters exclude missing values; use is_null/not_null for missingness.
- Correlation supports Pearson, Spearman and Kendall; it uses pairwise-complete finite observations and reports per-pair sample size. It analyzes at most 100 columns and returns at most 1,000 pairs by default; correlation does not prove causation.
- Numeric time columns are rejected rather than silently interpreted as nanoseconds. Missing measures and infinite measures are reported separately. Other trend timestamps are parsed with invalid values coerced to missing. Naive timestamps are interpreted as UTC; the requested timezone is applied before hour/day/week/month/quarter/year bucketing.
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
