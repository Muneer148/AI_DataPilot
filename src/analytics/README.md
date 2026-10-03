# Member 3 — Analytics & Visualization

> **Owns:** correct, reproducible calculations and charts based on the actual prepared dataset.
>
> **Project:** AI_DataPilot · **Target branch:** `feature/analytics`

## 1. Why this feature exists

The agent can understand a question, but it cannot be trusted to do arithmetic by generating prose. This module computes statistics and aggregations against real data and returns structured results that the agent can explain and the application can display.

**Rule:** pandas / NumPy calculate; the LLM interprets. Charts must be built from the same result data that is returned to the user.

## 2. Where it fits

```text
AnalysisReadyDataset (Member 1)
    ↓
Validated analysis request / plan (Member 2)
    ↓
Deterministic analytics functions (this module)
    ├── result table + metrics
    ├── warnings / assumptions
    └── chart specification or figure
              ↓
Grounded answer (Member 2) + UI/API (Member 4)
```

Member 1 owns data cleaning, quality, schema and provenance. Member 2 owns natural-language interpretation and orchestration. Member 4 owns API/UI integration. Do not duplicate ingestion or agent logic here.

## 3. Input contract

The integration target is the data foundation on `feature/data-foundation` (latest documented commit: `43a96ea444abcb9a927e88a7abdad025d70d4480`). Bring that branch into your working branch using the team's agreed workflow before relying on the API.

`AnalysisReadyDataset` is exported from `src.data` and exposes:

- `dataframe`: the authoritative, prepared pandas DataFrame.
- `metadata`: inferred column types and semantic hints.
- `profile`: bounded quality/statistical summaries.
- `validation` and `source_validation`: output and pre-cleaning findings.
- `cleaning` and `provenance`: transformations and source/preparation information.
- `get_column(name)` / `select_columns(columns)`: safe copy-returning column access helpers.

Use the DataFrame for exact calculations. Do not reconstruct exact values from the profile or send full rows to an LLM.

```python
from src.data import prepare_file
from src.analytics import describe_dataset  # proposed public API; implement/export it

dataset = prepare_file("data/raw/sales.csv")
result = describe_dataset(dataset)
```

The `src.analytics` import above is the **target API to implement**, not an existing function guaranteed to be present yet. Keep the public API small and document it.

## 4. What to build

Suggested layout (coordinate names with Member 2 before locking interfaces):

```text
src/analytics/
├── __init__.py
├── contracts.py      # request/result/warning/evidence structures
├── descriptive.py    # count, sum, mean, median, min/max, quantiles
├── aggregation.py    # group-by, sorting, top-N and filtering
├── relationships.py  # correlations and association with caveats
├── trends.py         # time bucketing and period comparisons
├── outliers.py       # transparent, configurable anomaly methods
├── service.py        # validated public facade
└── README.md
src/visualization/
├── __init__.py
├── charts.py         # chart specification / Plotly figure builders
└── README.md
tests/
├── test_analytics.py
└── test_visualization.py
```

### Build in this order

1. **Define request/result schemas.** Each request should specify operation, selected columns, grouping dimensions, filters, sorting, limit and optional time column. Validate names and types before execution.
2. **Implement descriptive statistics.** Count rows/non-null values, sum, mean, median, min/max, quantiles and missingness. Define how nulls are treated and label the denominator for every percentage.
3. **Implement aggregations.** Group-by summaries, sorted comparisons, top-N and basic filters. Bound result size and reject unsupported operations clearly.
4. **Add relationships and trends.** Correlation should use appropriate numeric columns and document pairwise missing-value handling. Time trends must parse/validate the selected time field and state the aggregation interval and timezone assumptions.
5. **Add anomaly methods only after the basics.** Begin with a documented baseline such as IQR or z-score, make thresholds configurable, and explain that flagged points are candidates for review—not proof of an error.
6. **Return evidence with every result.** Include operation, columns, filters, row count used, missing-value policy, units if known, warnings and provenance reference. Keep result records JSON-serializable.
7. **Build visualizations from result tables.** Use Plotly where appropriate. Return chart type, title, axes, labels and the data used; handle empty data, many categories, long labels and missing values. Do not invent a trend line or chart value.
8. **Add a stable facade.** Member 2 should call a small service API, not import every internal helper. Member 4 should be able to serialize the result without knowing the implementation.

## 5. Numerical and visualization rules

- Exact calculations must be reproducible from the DataFrame.
- Make null handling explicit; distinguish row count from non-null count.
- Do not silently coerce invalid strings into meaningful numbers.
- Never label correlation as causation.
- Report the sample size and caveats for correlation/anomaly results.
- For zero denominators, empty groups or insufficient samples, return a structured warning or error.
- Bound output rows and chart categories so a large dataset cannot overwhelm the UI or model context.
- Keep full row-level records out of LLM prompts unless there is an explicitly approved, bounded use case.
- Use consistent numeric precision for display without rounding the underlying result.

## 6. Minimum acceptance criteria

- [ ] Descriptive statistics and group-by/top-N work on a small known fixture.
- [ ] Results are deterministic and tested against manually calculable expected values.
- [ ] Nulls, empty datasets, non-numeric columns, duplicate labels and invalid column names are handled.
- [ ] Correlation/trend/anomaly results include sample-size or method caveats.
- [ ] Result contracts include operation, inputs/filters, row counts, warnings and provenance/evidence fields.
- [ ] Charts are based on returned result data and have readable titles/axis labels.
- [ ] Empty results and high-cardinality categories do not crash rendering.
- [ ] Tests run with `pytest -q` without requiring external services.

## 7. Definition of done

Given an `AnalysisReadyDataset` and a validated request, the module returns a deterministic, serializable result with explicit assumptions and evidence. When a chart is requested, it visualizes those same results. Both the numbers and chart inputs are covered by tests.

## 8. Coordination checklist

- **Member 1:** use the prepared DataFrame, metadata and provenance; do not modify the data foundation as a shortcut.
- **Member 2:** agree on the analytics request schema, supported operations and evidence fields.
- **Member 4:** agree how tables, warnings and chart specifications are serialized to the client.
- Commit tests with features; document unsupported operations rather than silently approximating them.
