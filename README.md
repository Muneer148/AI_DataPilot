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

## Team

| Member | Role |
|---|---|
| Member 1 | Data Engineering & Analytics Lead |
| Member 2 | AI / Agent Intelligence |
| Member 3 | Backend / Frontend / Visualization |

## 10-week target

- Weeks 1–2: SQL, Pandas, statistics, database/Snowflake fundamentals and data foundation
- Weeks 3–4: Natural language → SQL → validated answer MVP
- Weeks 5–6: analytics, statistics, anomaly detection/forecasting and visualization
- Weeks 7–8: safety, validation, provenance and evaluation benchmark
- Weeks 9–10: integration, testing, deployment and final documentation

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

## Status

🚧 Project initialization — Week 1
