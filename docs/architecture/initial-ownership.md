# DataPilot Architecture — Initial Ownership

## Module responsibilities

### Member 1 — Data Engineering & Data Quality (25%)
Owns ingestion, schema inference, validation, cleaning, profiling, metadata and analysis-ready datasets.

### Member 2 — AI / Agent Intelligence (30%)
Owns natural-language understanding, intent detection, planning, tool selection, agent orchestration, validation and explanations.

### Member 3 — Analytics & Visualization (22.5%)
Owns deterministic statistics, aggregation, correlation/trend/anomaly analysis and chart generation.

### Member 4 — Application, Backend & Integration (22.5%)
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
  |
  v
Analytics (Member 3)
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

## Initial module contract

The data layer should expose a small stable interface first:

- `DataLoader.load(path) -> pandas.DataFrame`
- `infer_schema(df) -> DatasetMetadata`

Future modules should consume these interfaces instead of reaching into implementation details.
