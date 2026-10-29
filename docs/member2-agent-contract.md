# Member 2 — AI Agent / Brain: Contract and Handoff

This document describes the bounded implementation on `feature/member2-agent-plan-contract`. The rules planner remains the default. This is a constrained data-analysis agent, not a general autonomous agent.

## Supported-question matrix

All examples assume exact column labels are present in the prepared dataset and any referenced numeric columns use a real numeric dtype. The examples illustrate intent that the current rules planner can ground; they are not a claim of general natural-language coverage.

| Example question | Validated plan fields (excluding `reason`) | Exact executor | Behavior |
|---|---|---|---|
| “Summarize this dataset” | `operation=describe`, `metric_column=null`, `group_by=[]`, `aggregation=null`, `limit=10` | `src.analytics.describe_dataset(dataset)` | Bounded descriptive evidence per column. |
| “How many rows are there?” | `operation=count_rows`, `metric_column=null`, `group_by=[]`, `aggregation=count_rows`, `limit=10` | `src.analytics.aggregate_dataset(dataset, aggregations={}, limit=1)` | Count comes from the analytics result's source `row_count`. |
| “What is the total sales?” | `operation=aggregate`, `metric_column=sales`, `group_by=[]`, `aggregation=sum`, `limit=10` | `src.analytics.aggregate_dataset(..., aggregations={"sales": "sum"}, limit=10)` | The answer value is read from `evidence.records[0]["sales__sum"]`. |
| “What is the average sales by region?” | `operation=aggregate`, `metric_column=sales`, `group_by=["region"]`, `aggregation=mean`, `limit=10` | `src.analytics.aggregate_dataset(..., group_by=["region"], aggregations={"sales": "mean"}, limit=10)` | Evidence contains the deterministic result per region. |
| “What is the median sales?” | `operation=aggregate`, `metric_column=sales`, `group_by=[]`, `aggregation=median`, `limit=10` | `src.analytics.aggregate_dataset(..., aggregations={"sales": "median"}, limit=10)` | Requires a real numeric sales column. |
| “What is the maximum sales by region?” | `operation=aggregate`, `metric_column=sales`, `group_by=["region"]`, `aggregation=max`, `limit=10` | `src.analytics.aggregate_dataset(..., group_by=["region"], aggregations={"sales": "max"}, limit=10)` | Group order is bounded; results are deterministic. |
| “Count non-null sales by region” | `operation=aggregate`, `metric_column=sales`, `group_by=["region"]`, `aggregation=count`, `limit=10` | `src.analytics.aggregate_dataset(..., group_by=["region"], aggregations={"sales": "count"}, limit=10)` | Counts non-null values in the metric, not all rows. |
| “Count rows by region” | `operation=aggregate`, `metric_column=null`, `group_by=["region"]`, `aggregation=count_rows`, `limit=10` | `src.analytics.aggregate_dataset(..., group_by=["region"], aggregations={}, limit=10)` | Group count is the number of rows in each group. |
| “What is the correlation between sales and units?” | `operation=correlation`, `metric_column=null`, `group_by=["sales","units"]`, `aggregation=null`, `limit=10` | `src.analytics.correlate_dataset(dataset, columns=["sales", "units"], method="pearson")` | Requires exactly two distinct real numeric columns; correlation is not causation. |

## Plan contract

`AnalysisPlan` is the typed internal plan:
- `operation`: one of `describe`, `aggregate`, `count_rows`, `correlation`.
- `metric_column`: exact column-name string or `None`.
- `group_by`: tuple of exact column-name strings; at most one grouping column for aggregation and exactly two columns for correlation.
- `aggregation`: one of `sum`, `mean`, `median`, `min`, `max`, `count`; `count_rows` is reserved for row-count plans.
- `limit`: integer from 1 through 100; booleans are rejected even though Python treats them as integers.
- `reason`: string explanation for traceability, never executable content.

The shared `src.agent.plan_validation.validate_plan(plan, dataset)` contract runs in the orchestrator after either planner and before any analytics function. It verifies runtime types, allowed operation/aggregation, referenced columns, schema uniqueness via analytics contracts, numeric dtype requirements, compatible fields, grouping shape, and result bounds. Provider-side validation is retained as a defense-in-depth layer. All computations flow only through three allow-listed functions: `describe_dataset`, `aggregate_dataset`, and `correlate_dataset`.

## Response/result contract

`ask(dataset, question, planner="rules")` returns `AgentResponse` with:
- `status`: `ok`, `needs_clarification`, or `error`.
- `answer`: user-facing text; numerical values, where rendered, are taken from the deterministic analytics result.
- `plan`: serialized validated plan when one reaches execution.
- `evidence`: serialized `AnalyticsResult` on success, or a structured `error` object for coded plan/analytics contract errors; otherwise null.
- `clarification`: clarification or safe failure explanation where applicable.
- `warnings`: analytics warnings on success.

Unknown columns/ambiguous intent must not produce a guessed number. Invalid plan contracts are errors. Unsupported/ambiguous natural-language questions abstain through clarification. Unexpected internal exceptions produce a generic error without leaking implementation details.

## Provider configuration and privacy boundary

- Default is `planner="rules"`; the rules planner requires no LLM service.
- Local Ollama is explicit opt-in only: `ask(..., planner="ollama")`.
- Model: `AI_DATAPILOT_OLLAMA_MODEL`, default `qwen3.5:4b`.
- Endpoint: `OLLAMA_BASE_URL`, default `http://127.0.0.1:11434`; use only an intentional trusted endpoint.
- Provider request timeout defaults to 45 seconds (provider maximum accepted timeout is 180 seconds).
- Provider failure or invalid structured output returns a safe error. There is no silent switch to the rules planner and no fabricated success.
- Only the question and column names/dtypes are sent to the planner. Raw data rows, example values, and row-derived profiles are not sent. Keep this boundary unless the project lead approves a redesign after privacy review.
- The model only proposes a bounded structured plan. No model-generated Python, shell commands, or unrestricted SQL are executed. Numerical results are always produced by deterministic analytics.

## Explicitly unsupported / clarification cases

The MVP does not promise general conversational understanding. It currently does not support arbitrary filters/date ranges, multi-step analysis, joins, forecasting, causal attribution, semantic mapping of business synonyms to columns, multiple grouping dimensions, open-ended SQL, user-defined code, or arbitrary chart specifications through the agent planner. It expects clearly stated supported operations and exact column labels. Correlation needs two distinct numeric columns. Unsupported or underspecified requests must be clarified or safely rejected.

## Test and CI evidence

Verification recorded for this branch: GitHub Actions run [Agent MVP tests #69](https://github.com/Muneer148/AI_DataPilot/actions/runs/40825509410) completed successfully on Python 3.11.17 after installing `requirements.txt`; command `python -m pytest -q` reported `91 passed, 2 skipped in 1.22s`. The two skips remain skips, not passes. Local tests were not run in this editing environment. Rerun the workflow after subsequent code changes.

## Next integration dependency for Member 4

Call the agent through `src.agent.ask(prepared_dataset, question, planner="rules")` (or make Ollama opt-in a deliberate UI/API setting) and serialize `AgentResponse.to_dict()`. The prepared data object must expose its analysis-ready DataFrame as `.dataframe`. Keep upload limits and API error handling in the application layer, and surface `status`, `answer`, `evidence`, and `clarification` consistently. Before merging, the team lead must reconcile this feature branch with the currently agreed `feature/data-foundation` integration baseline; do not merge the divergent branches blindly.
