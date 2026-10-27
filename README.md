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
Clean / Validated / Analysis-Ready Data
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

## 25-week project roadmap

The planned project horizon is **25 weeks in total**. Work may overlap after the team agrees on stable interfaces. A phase is complete only when its deliverables can be demonstrated, not merely when documentation is written.

| Weeks | Focus | Primary owners | Exit criteria |
|---|---|---|---|
| 1–2 | Problem definition and requirements | All members | Agreed use cases, project scope, functional and non-functional requirements, representative datasets, success metrics and privacy constraints |
| 3–4 | Architecture and engineering baseline | All members | Architecture, four-member ownership, module boundaries, data/result contracts, branch workflow, test layout and baseline CI agreed |
| 5–7 | Ingestion and schema foundation | Member 1 | CSV/XLSX/XLS/JSON loading, file safeguards, schema metadata and loader tests |
| 8–10 | Data quality, cleaning and provenance | Member 1; Members 2 and 3 review the contract | Validation, profiling, preview-first cleaning, cleaning audit, provenance, `AnalysisReadyDataset` and bounded model context |
| 11–13 | Agent intent and planning | Member 2 | Typed request/plan contracts, supported intent patterns, schema-aware planning, clarification path and provider adapter with mocked tests |
| 14–16 | Safe query and tool execution | Member 2 with Member 1 | Approved tool interface, read-only SQL validation/execution or an agreed deterministic alternative, parameterization, limits, controlled errors and evidence |
| 17–19 | Analytics and visualization | Member 3 | Tested descriptive statistics and aggregations, selected trends/relationships/anomaly baseline, serializable results and charts generated from actual results |
| 20–21 | Application and API workflow | Member 4 | Local startup, health endpoint, safe upload, preview/prepare flow, question/result endpoint and stable error responses |
| 22–23 | End-to-end integration and evaluation | All members | Demonstrable upload → preview → prepare → question → grounded result/chart/provenance workflow, evaluation fixtures and a recorded defect list |
| 24 | Hardening, deployment and documentation | All members | Regression/integration tests, safe configuration, time/result limits, reproducible setup instructions and resolved critical defects |
| 25 | Final validation and submission | All members | Frozen review scope, fresh full test run, repeatable demo, final report/references, presentation and viva preparation |

### Milestone gates

1. **Week 4:** module boundaries and contracts are agreed before parallel implementation expands.
2. **Week 10:** downstream modules can consume the tested data-foundation contract.
3. **Week 16:** a supported question can reach an approved deterministic execution tool safely.
4. **Week 23:** the integrated happy path and key failure paths are demonstrated end to end.
5. **Week 25:** the submission reflects only verified functionality, with limitations stated honestly.

Use focused feature branches and reviewable commits. Integrate through the team's agreed pull-request/review process; rerun relevant tests after integration. Keep raw customer datasets, credentials and local environment files out of version control.
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

## Data foundation snapshot on main

This section describes the older `main` snapshot only; feature branches may contain newer implementation. The code represented here includes:

- Multi-format tabular loader for CSV, Excel and JSON.
- Basic schema/type inference.
- Dataset metadata object.
- Missing-cell and duplicate-row counts.
- Unit tests for loader and schema inference.

## Development principle

Build incrementally. Each weekly commit should leave the repository runnable and should add a coherent capability rather than placeholder code.
