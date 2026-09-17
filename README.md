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
- **Member 3 — Analytics & Visualization:** owns statistics, aggregation, correlations, trends, anomaly analysis, insight extraction, visualization generation and automatic chart selection. Main question: **What does the data tell us?**
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

### Week 1 — Ingestion foundation
- Multi-format tabular loader for CSV, Excel and JSON.
- Basic schema/type inference.
- Dataset metadata object.
- Missing-cell and duplicate-row counts.
- Unit tests for loader and schema inference.

### Week 2 — Validation + profiling
- Structural dataset validation without mutating source data.
- Required-column checks and configurable missing-value thresholds.
- Duplicate-row, duplicate-column, blank-column and infinite-value detection.
- Bounded per-column profiling with missingness, cardinality, examples and type-aware statistics.
- JSON-friendly validation/profile reports.

### Week 3 — Cleaning + analytical interfaces
- Conservative, configurable cleaning pipeline.
- Column-name cleanup and uniqueness handling.
- String whitespace normalization and blank-string-to-missing conversion.
- Empty-row/column and duplicate-row handling with an audit report.
- `AnalysisReadyDataset` contract combining cleaned data, schema metadata, validation, profiling and cleaning provenance.
- Stable column-selection/access methods for downstream AI and analytics modules.
- Unit tests covering validation, profiling, cleaning and the downstream contract.

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
   ├── dataframe
   ├── metadata
   ├── profile
   ├── validation
   └── cleaning audit
```

## Development principle

Build incrementally. Each weekly commit should leave the repository runnable and should add a coherent capability rather than placeholder code.
