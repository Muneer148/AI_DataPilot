# AI_DataPilot

> Explainable & Trustworthy AI Data Analyst Agent for Automated Business Intelligence

AI_DataPilot is a B.Tech major project focused on building a reliable AI-powered data analyst that answers natural-language questions over structured business data using grounded SQL, deterministic analytics, visualizations, and evidence/provenance.

## Core idea

Instead of returning an LLM-generated answer that may hallucinate numbers, AI_DataPilot will understand the user's analytical question, inspect the data/schema, plan the required analysis, execute validated operations against the actual data, and return results with supporting evidence.

## Team roles

| Member | Role |
|---|---|
| Member 1 | Data Engineering & Data Quality |
| Member 2 | AI / Agent Intelligence |
| Member 3 | Analytics & Visualization |
| Member 4 | Application, Backend & Integration |

- **Member 1:** ingestion, schema inference, validation, cleaning, profiling, metadata and analysis-ready datasets — *Is the data ready?*
- **Member 2:** natural-language understanding, intent detection, planning, tool selection, orchestration and explanations — *What does the user want?*
- **Member 3:** statistics, aggregation, correlations, trends, anomaly analysis and charts — *What does the data tell us?*
- **Member 4:** UI, backend APIs, uploads/chat, integration, error handling, integration tests and deployment — *How does the user use it?*

## Data preparation workflow

```text
File upload
    ↓
DataLoader (CSV / XLSX / XLS / JSON)
    ↓
Source validation + profile
    ↓
Cleaning preview (no mutation of original input)
    ↓
Output validation + caller approval
    ↓
AnalysisReadyDataset + provenance
    ├── dataframe: source of truth for deterministic analysis
    ├── metadata: physical schema and semantic hints
    ├── profile: bounded column-level statistics
    ├── validation: pre-clean and post-clean findings
    ├── cleaning: transformation audit
    ├── provenance: source file and preparation settings
    └── to_model_context(): bounded LLM-facing summary
```

The preview API does not modify the caller's DataFrame. It returns a separate cleaned preview, source quality findings, output validation and a cleaning audit. If the output validation fails, the preview remains inspectable but `ready` is false. The caller can then adjust the cleaning configuration or required-column rules before preparing the final dataset.

## Quick start — data layer

```python
from src.data import CleaningConfig, preview_file, prepare_file

config = CleaningConfig(drop_duplicate_rows=False)

# 1. Inspect quality and proposed changes first.
preview = preview_file(
    "data/raw/sales.csv",
    config=config,
    required_columns=["sales", "region"],
    max_missing_ratio=0.25,
)
print(preview.to_dict())  # raw row values are omitted by default

if not preview.ready:
    raise ValueError("Resolve the blocking validation findings before analysis.")

# 2. Prepare with the same approved configuration.
dataset = prepare_file(
    "data/raw/sales.csv",
    config=config,
    required_columns=["sales", "region"],
    max_missing_ratio=0.25,
)

# 3. Send bounded context to the LLM, not the full dataset.
model_context = dataset.to_model_context(max_columns=100)

# 4. Run exact calculations locally against the real DataFrame.
sales_total = dataset.dataframe["sales"].sum()
```

For an in-memory DataFrame, use `preview_dataframe(df, ...)` and `prepare_dataset(df, ...)`.

## Data foundation capabilities

### Ingestion
- Supports CSV, Excel (`.xlsx`, `.xls`) and JSON.
- Validates path existence, file type, non-file paths, empty files and a configurable maximum size (100 MiB by default).
- Includes `xlrd` for legacy `.xls` parsing and wraps common parser failures with a clear error.

### Schema, validation and profiling
- Structural type inference plus separate hints for date-like strings and identifier-like column names; source values are not silently coerced.
- Required-column and configurable missingness checks, duplicate/blank column-name checks, all-null columns and infinite numeric-value findings.
- Duplicate-row detection reports a warning; nested unhashable values produce an explicit skipped-check warning rather than crashing validation.
- Bounded column profiling supports nested values and timestamps and emits JSON-compatible summaries.

### Cleaning, preview and provenance
- Cleaning works on a copy, with configurable whitespace handling, blank-to-missing conversion and empty-row/column removal.
- Column names are normalized with collision-safe unique names.
- Duplicate records are retained by default; dropping them requires explicit configuration.
- `preview_dataframe()` / `preview_file()` expose source validation, source profile, proposed changes and output validation before final preparation.
- `prepare_dataset()` / `prepare_file()` return an `AnalysisReadyDataset` with source and output validation, cleaning audit, schema, profile and provenance (source name/format/size, input/output shape and cleaning configuration).

### Model handoff
- `to_model_context()` includes bounded schema hints, profiles, quality findings and provenance but no raw rows.
- Value examples and frequent values are excluded by default because they can contain sensitive data.
- Exact row-level calculations must be executed by deterministic tools against `dataset.dataframe`; the LLM should interpret questions and plan analysis, not guess results from summaries.

## Repository structure

```text
AI_DataPilot/
├── app/
├── data/                 # raw and processed data (do not commit private datasets)
├── docs/architecture/
├── evaluation/
├── notebooks/
├── src/
│   ├── agent/
│   ├── analytics/
│   ├── data/
│   ├── sql/
│   └── visualization/
├── tests/
└── requirements.txt
```

## Development plan

- Stabilize the data contract and quality checks.
- Integrate one end-to-end CSV question/analysis flow.
- Add safe read-only query execution, provenance and regression evaluation.
- Expand analytics/visualizations, integration testing and deployment.

## Development principle

Each coherent change should leave the repository testable, preserve data provenance, avoid unnecessary exposure of row-level data, and keep stable contracts for integration with the other team members.
