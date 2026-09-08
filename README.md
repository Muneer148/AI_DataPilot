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

## Team ownership

| Member | Role | Share |
|---|---|---:|
| Member 1 | Data Engineering & Data Quality | 25% |
| Member 2 | AI / Agent Intelligence | 30% |
| Member 3 | Analytics & Visualization | 22.5% |
| Member 4 | Application, Backend & Integration | 22.5% |

### Role boundaries
- **Member 1:** ingestion, schema detection, validation, cleaning, profiling, metadata and analysis-ready datasets.
- **Member 2:** natural-language understanding, intent detection, planning, tool selection, agent workflow, validation and explanations.
- **Member 3:** statistics, aggregation, correlations, trends, anomaly analysis and visualization generation.
- **Member 4:** frontend, backend APIs, module integration, error handling, testing and deployment.

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

## Week 1 status

Implemented the first data-layer foundation:

- Multi-format tabular loader for CSV, Excel and JSON.
- Basic schema/type inference.
- Dataset metadata object.
- Missing-cell and duplicate-row counts.
- Unit tests for loader and schema inference.

## Development principle

Build incrementally. Each weekly commit should leave the repository runnable and should add a coherent capability rather than placeholder code.
