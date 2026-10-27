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


## Feature implementation guides

The feature branches contain a build guide for each remaining team member. Each guide explains the purpose, boundaries, suggested module structure, implementation order, integration contract, safety rules, tests and definition of done. These are implementation specifications; they do not claim the corresponding feature code already exists.

- [Member 2 — AI / Agent Intelligence](https://github.com/Muneer148/AI_DataPilot/blob/feature/ai-agent/src/agent/README.md)
- [Member 3 — Analytics & Visualization](https://github.com/Muneer148/AI_DataPilot/blob/feature/analytics/src/analytics/README.md)
- [Member 4 — Application, Backend & Integration](https://github.com/Muneer148/AI_DataPilot/blob/feature/application/app/README.md)

**Integration baseline:** use the current `feature/data-foundation` branch as the source of truth. Check its latest commit and CI status when integrating; do not pin downstream work to an older documented commit. Bring the current branch into the relevant feature branch through the team's agreed merge/rebase workflow. Keep each member's code ownership separate and integrate through documented contracts and tests.

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

## Run the data foundation demo

From the repository root, preview the built-in synthetic sales dataset:

```bash
python -m examples.data_foundation_demo
```

The command prints a JSON quality report and proposed cleaning audit without raw row values. Preparation is deliberately a separate, explicit step:

```bash
python -m examples.data_foundation_demo --prepare
```

To inspect a real local file, pass its path. Repeat any required-column option as needed; review the preview before using `--prepare`.

```bash
python -m examples.data_foundation_demo path/to/sales.csv --required-column sales --required-column region --max-missing-ratio 0.25
python -m examples.data_foundation_demo path/to/sales.csv --required-column sales --required-column region --max-missing-ratio 0.25 --prepare
```

The demo uses the same cleaning configuration for preview and preparation, blocks preparation when output validation fails, and emits bounded model context without raw rows or value examples by default.

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
## Development principle

Each coherent change should leave the repository testable, preserve data provenance, avoid unnecessary exposure of row-level data, and keep stable contracts for integration with the other team members.
