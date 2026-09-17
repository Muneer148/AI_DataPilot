# DataPilot Architecture — Initial Ownership

## Module responsibilities

### Member 1 — Data Engineering & Data Quality
Owns ingestion, schema inference, validation, cleaning, profiling, metadata and analysis-ready datasets.

### Member 2 — AI / Agent Intelligence
Owns natural-language understanding, intent detection, planning, tool selection, agent orchestration, validation and explanations.

### Member 3 — Analytics & Visualization
Owns deterministic statistics, aggregation, correlation/trend/anomaly analysis and chart generation.

### Member 4 — Application, Backend & Integration
Owns UI, backend APIs, module contracts, integration, error handling, testing and deployment.

## Responsibility flow

```text
User
  |
  v
Application / Backend (Member 4)
  |
  v
AI / Agent (Member 2) -----> Data schema/metadata (Member 1)
  |                                  |
  v                                  v
Analytics (Member 3) <----- AnalysisReadyDataset
  |
  v
Verified result + visualization
  |
  v
Application / Backend (Member 4)
  |
  v
User
```

The diagram represents ownership and interaction, not a strict execution order. The data layer can be queried by both the agent and analytics components.

## Data foundation contracts

The data layer exposes small, stable interfaces so downstream modules do not depend on implementation details:

- `DataLoader.load(path) -> pandas.DataFrame`
- `infer_schema(df) -> DatasetMetadata`
- `validate_dataframe(df, ...) -> ValidationReport`
- `profile_dataframe(df, ...) -> DatasetProfile`
- `clean_dataframe(df, ...) -> (pandas.DataFrame, CleaningReport)`
- `prepare_dataset(df, ...) -> AnalysisReadyDataset`

`AnalysisReadyDataset` packages the cleaned DataFrame together with schema metadata, a bounded profile, validation findings and a cleaning audit report.

## Data-quality principles

1. **Do not mutate caller-owned data.** Cleaning operates on a deep copy.
2. **Prefer deterministic transformations.** The same input and configuration should produce the same result.
3. **Keep cleaning auditable.** Row/column removals, blank replacements and column renames are reported.
4. **Do not silently coerce business meaning.** Type-changing or domain-specific transformations should be explicit future steps.
5. **Fail clearly on structural invalidity.** Required columns, duplicate column names and excessive missingness can block the analysis-ready contract.
6. **Keep reports bounded.** Profiling returns compact examples and top values rather than dumping entire columns.
