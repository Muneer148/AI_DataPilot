# AI_DataPilot

> Explainable & Trustworthy AI Data Analyst Agent for Automated Business Intelligence

AI_DataPilot is a B.Tech major project focused on building a reliable AI-powered data analyst that answers natural-language questions over structured business data using grounded SQL, deterministic analytics, visualizations, and evidence/provenance.

## Core idea

Instead of returning an LLM-generated answer that may hallucinate numbers, AI_DataPilot will:

1. Understand the user's analytical question.
2. Inspect the available data/schema.
3. Plan the required analysis.
4. Generate and validate read-only SQL or analytical operations.
5. Execute against the analytical data layer.
6. Apply deterministic analytics/statistics where appropriate.
7. Generate visualizations from actual results.
8. Return an explainable answer with supporting evidence.

## Team roles

| Member | Role |
|---|---|
| Member 1 | Data Engineering & Data Quality |
| Member 2 | AI / Agent Intelligence |
| Member 3 | Analytics & Visualization |
| Member 4 | Application, Backend & Integration |

### Role boundaries
- **Member 1 — Data Engineering & Data Quality:** owns data ingestion, schema detection, validation, cleaning, profiling, metadata, storage preparation and analysis-ready datasets. Main question: **Is the data ready?**
- **Member 2 — AI / Agent Intelligence:** owns natural-language understanding, intent detection, planning, tool selection, agent workflow, validation and explanations. Main question: **What does the user want?**
- **Member 3 — Analytics & Visualization:** owns statistics, aggregations, correlations, trends, anomaly analysis, insight extraction, visualization generation and automatic chart selection. Main question: **What does the data tell us?**
- **Member 4 — Application, Backend & Integration:** owns frontend, backend APIs, upload/chat interfaces, module integration, error handling, integration testing and deployment. Main question: **How does the user use it?**

### Responsibility flow

```text
User Dataset
     ↓
Member 1 — Data Engineering & Data Quality
     ↓
Load → Validate → Profile → Clean → Prepare
     ↓
Analysis-Ready Data Contract
     ↓
 ┌───────────────────────┐
 │                       │
 ↓                       ↓
Member 2               Member 3
AI / Agent              Analytics &
Intelligence            Visualization
 │                       │
 └───────────┬───────────┘
             ↓
Member 4 — Application, Backend & Integration
             ↓
        User-facing results
```

The flow represents responsibility boundaries, not a strict execution order. Member 1 provides stable data interfaces that can be consumed by both the AI and analytics modules.

## Development plan

- **Week 1:** repository architecture + data ingestion foundation
- **Week 2:** validation + profiling
- **Week 3:** cleaning + analytical interfaces
- **Week 4:** initial AI/query layer + integration
- **Weeks 5–6:** richer analytics, statistics, anomaly detection/forecasting and visualization
- **Weeks 7–8:** SQL safety, validation, provenance and evaluation benchmark
- **Weeks 9–10:** integration, testing, deployment and final documentation

## Repository structure

```text
AI_DataPilot/
├── app/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── architecture/
│   ├── research/
│   └── meeting-notes/
├── evaluation/
│   ├── questions/
│   └── results/
├── notebooks/
├── src/
│   ├── agent/
│   ├── analytics/
│   ├── data/
│   ├── sql/
│   ├── validation/
│   └── visualization/
├── tests/
├── .gitignore
└── requirements.txt
```

## Data foundation status

### Ingestion
- Supports CSV, Excel (`.xlsx`, `.xls`) and JSON input.
- Checks file existence, file type, non-file paths, empty files and a configurable maximum file size (100 MiB by default).
- Includes `xlrd` for legacy `.xls` parsing.

### Schema, validation and profiling
- Structural schema inference with separate hints for date-like strings and identifier-like column names; inference does not silently coerce source data.
- Structural validation, required-column checks and configurable missing-value thresholds.
- Detection of duplicate rows/columns, blank column names, all-null columns and infinite numeric values.
- Bounded per-column profiling with missingness, cardinality, examples, common values and type-aware statistics.
- Profiles are designed to be JSON-friendly, including nested values and timestamps.

### Cleaning and analytical interfaces
- Conservative, configurable cleaning pipeline with a change audit.
- Column-name normalization and collision-safe uniqueness handling.
- String whitespace normalization and blank-string-to-missing conversion.
- Empty-row/column removal is configurable; duplicate rows are retained by default and can be dropped explicitly.
- `AnalysisReadyDataset` combines the prepared DataFrame, metadata, validation findings, profile and cleaning provenance.
- `to_model_context()` creates a bounded LLM context without raw row records; value examples and frequent values are omitted by default.
- Unit tests cover ingestion boundaries, schema hints, validation, profiling, cleaning and downstream contracts.
- GitHub Actions runs the test suite on pushes and pull requests.

## Data-layer contract

Downstream modules should depend on the public interfaces rather than internal implementation details:

```text
DataLoader.load(path)
        ↓
pandas.DataFrame
        ↓
prepare_dataset(df)
        ↓
AnalysisReadyDataset
   ├── dataframe          # source of truth for deterministic analysis
   ├── metadata           # physical types + semantic hints
   ├── profile            # bounded per-column statistics
   ├── validation         # quality findings
   ├── cleaning           # transformation audit
   └── to_model_context() # bounded LLM-facing summary, no raw records
```

**Model handoff principle:** use the LLM to interpret the question and plan the work; use local, deterministic analytics to calculate answers from the actual DataFrame. Do not send the entire dataset to an LLM by default or infer exact aggregates from a profile summary.

## Development principle

Build incrementally. Each coherent change should leave the repository testable, preserve data provenance, and keep stable contracts for integration with the other team members.
