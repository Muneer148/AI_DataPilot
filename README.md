# AI_DataPilot

> Explainable & Trustworthy AI Data Analyst Agent for Automated Business Intelligence

AI_DataPilot is a B.Tech major project focused on building a reliable AI-powered data analyst that can answer natural-language questions over structured business data using grounded SQL, statistical analysis, visualizations, and evidence/provenance.

## Core idea

Instead of returning an LLM-generated answer that may hallucinate numbers, AI_DataPilot will:

1. Understand the user's analytical question.
2. Inspect the available data/schema.
3. Plan the required analysis.
4. Generate and validate read-only SQL.
5. Execute the query against the analytical database.
6. Apply deterministic analytics/statistics where appropriate.
7. Generate visualizations from actual results.
8. Return an explainable answer with supporting evidence.

## Team roles

| Member | Role | Primary responsibility |
|---|---|---|
| Member 1 | Data Engineering & Data Quality | Ingestion, schema inference, validation, cleaning, profiling, provenance and analysis-ready datasets |
| Member 2 | AI / Agent Intelligence | Natural-language understanding, intent detection, planning, safe tool selection and grounded explanations |
| Member 3 | Analytics & Visualization | Deterministic statistics, aggregations, trends, relationships, anomaly analysis and charts |
| Member 4 | Application, Backend & Integration | User interface, backend APIs, upload/chat workflow, integration, error handling, tests and deployment |

### Responsibility boundaries

- **Member 1 — Data Engineering & Data Quality:** establishes whether uploaded data is usable and prepares a validated, traceable dataset.
- **Member 2 — AI / Agent Intelligence:** determines what the user is asking and plans a safe analysis; it does not invent numerical results.
- **Member 3 — Analytics & Visualization:** computes results from the actual prepared dataset and creates charts from those same results.
- **Member 4 — Application, Backend & Integration:** connects the modules into a usable application and makes the complete workflow testable and deployable.

A role guide or branch is not evidence that its feature is implemented; acceptance requires working code, tests and a demonstrable result.

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
## Principles

- Data-grounded numerical answers
- Read-only database access
- No fabricated results
- Evidence and provenance for important conclusions
- Measurable evaluation rather than demo-only claims
- Free/local-first development wherever practical

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

## Branch status note

This branch's root scaffold and README describe the project architecture and roadmap, not completed implementations in every module. Check the source files, tests and latest CI run on the relevant feature branch before treating a component as implemented or integrated.
