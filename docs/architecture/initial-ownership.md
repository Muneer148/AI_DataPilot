# DataPilot Architecture — Data Foundation Contracts

## Module responsibilities

### Member 1 — Data Engineering & Data Quality
Owns ingestion, schema inference, validation, cleaning, profiling, metadata, preparation preview, provenance and analysis-ready datasets.

### Member 2 — AI / Agent Intelligence
Owns natural-language understanding, intent detection, planning, tool selection, agent orchestration, validation and explanations.

### Member 3 — Analytics & Visualization
Owns deterministic statistics, aggregation, correlation/trend/anomaly analysis and chart generation.

### Member 4 — Application, Backend & Integration
Owns UI, backend APIs, upload/chat interfaces, module integration, error handling, integration tests and deployment.

## Responsibility flow

```text
Uploaded dataset
       |
       v
Member 1: load -> inspect -> preview cleaning -> validate -> prepare
       |
       v
AnalysisReadyDataset
       |                         |
       v                         v
Member 2: interpret         Member 3: calculate
and plan analysis           on the real DataFrame
       |                         |
       +------------+------------+
                    v
Member 4: integrate and present grounded results
```

The diagram represents ownership and integration contracts, not a strict execution order. Both the agent and analytics components consume the stable data contract. Only deterministic analytics tools should calculate exact row-level results.

## Public data contracts

- `DataLoader.load(path) -> pandas.DataFrame`
- `infer_schema(df) -> DatasetMetadata`
- `validate_dataframe(df, ...) -> ValidationReport`
- `profile_dataframe(df, ...) -> DatasetProfile`
- `clean_dataframe(df, config) -> (pandas.DataFrame, CleaningReport)`
- `preview_dataframe(df, ...) -> DatasetPreparationPreview`
- `preview_file(path, ...) -> DatasetPreparationPreview`
- `prepare_dataset(df, ...) -> AnalysisReadyDataset`
- `prepare_file(path, ...) -> AnalysisReadyDataset`
- `AnalysisReadyDataset.to_model_context(...) -> dict`

## Preview-before-prepare lifecycle

1. Load the supported input format (CSV, XLSX, XLS or JSON) under the configured file-size guard.
2. Validate and profile the original input so quality issues are not hidden by cleaning.
3. Clean a copy using an explicit `CleaningConfig`; do not mutate caller-owned data.
4. Validate the proposed output against required columns and missingness constraints.
5. Return a preview containing source findings, a bounded profile, the cleaned DataFrame, a cleaning audit and output validation. The preview remains inspectable even when `ready` is false.
6. After reviewing the preview, call `prepare_file` or `prepare_dataset` with the accepted configuration to build the final `AnalysisReadyDataset`.
7. Use `to_model_context()` to share bounded metadata with the LLM. Use the contained DataFrame for deterministic analytics.

## AnalysisReadyDataset contract

The prepared object contains:

- `dataframe`: source of truth for exact calculations; not included in metadata serialization.
- `metadata`: row/column counts, physical types and conservative semantic hints.
- `profile`: per-column missingness, cardinality and type-aware statistics.
- `validation`: findings on the prepared output.
- `source_validation`: findings on the original input before cleaning.
- `cleaning`: audit of row/column removals, blank replacements and column renames.
- `provenance`: source name/format/size, input/output dimensions and the effective cleaning configuration.
- `to_model_context()`: bounded LLM context, no raw row records, no examples/top values by default.

## Data-quality and safety principles

1. **Preserve caller data.** Cleaning and previewing operate on a copy.
2. **Prefer deterministic transformations.** The same input and configuration should produce the same output.
3. **Make changes auditable.** Report row/column removals, blank replacements and column renames.
4. **Retain duplicate records by default.** Duplicates are findings, not proof of bad data.
5. **Do not silently coerce business meaning.** Date-like strings and identifier-like names are hints, not automatic conversions.
6. **Keep source and output findings separate.** Cleaning must not hide issues discovered in the uploaded dataset.
7. **Fail clearly on invalid prepared output.** Required columns, duplicate column names and configured missingness limits can block readiness.
8. **Keep LLM context bounded.** Omit raw rows and value examples by default; exact calculations use local deterministic tools.
9. **Guard ingestion.** Check file type, path, empty files and configurable file-size limits before parsing.
10. **Report skipped checks.** Unhashable nested values should not crash validation; any skipped duplicate check is made explicit.
