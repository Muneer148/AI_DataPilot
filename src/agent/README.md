# AI_DataPilot Agent MVP

## What works today

The agent is integrated with the local FastAPI demo (app/main.py) and exposes the question-driven flow through POST /api/analyze. The UI can select one of two planning modes:

- **Rules baseline**: deterministic phrase matching; no model required.
- **Local Ollama planner**: an installed local model proposes a structured plan. The plan is type-checked, checked against the dataset schema, and restricted to supported operations before deterministic analytics execute.

The agent returns a status, answer, plan, calculation evidence, clarification (when needed), and warnings. The UI displays the evidence separately from the answer.

This is a bounded, single-step analyst copilot—not a production-ready autonomous agent, SOC agent, or general-purpose assistant. It does not execute model-generated code or unrestricted SQL, and it does not claim to infer root causes from correlation.

## Local setup

From the repository root, install dependencies and start the API:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. The rules baseline works without Ollama.

For local model planning, install Ollama and pull a compatible local model:

```powershell
ollama pull qwen3.5:4b
ollama run qwen3.5:4b
```

Configuration:

- AI_DATAPILOT_OLLAMA_MODEL: model name; defaults to qwen3.5:4b
- OLLAMA_BASE_URL: endpoint; defaults to http://127.0.0.1:11434

Keep Ollama bound to loopback for local use. Do not expose its unauthenticated API to the public internet. A remote endpoint must be deliberately trusted and protected.

## Supported operations

- Dataset summary / description
- One metric aggregation: sum, mean, median, min, max, or count; optionally grouped by one column
- Correlation between two explicitly named columns
- Row count, optionally grouped by one column
- Clarification when intent or column selection is ambiguous or unsupported

The planner proposes intent; deterministic analytics calculate the result. The returned records are the source of truth. Correlation does not establish causation.

## Safety and privacy boundaries

- CSV text is bounded by the demo's input, row, and column limits and is processed in memory; this demo does not persist uploaded datasets.
- Rules mode does not call Ollama.
- Ollama mode sends the question and column names/types, not raw dataset rows or example records.
- Model output is validated against required fields, supported operations, column names, and argument constraints before execution.
- Only explicitly allow-listed analytics operations execute. Model-produced Python, shell commands, and unrestricted SQL are not executed.
- Provider failures and invalid plans fail closed; there is no automatic fallback that could silently change the intended analysis.
- Answers, plans, and evidence are separate objects. The app does not use the LLM to invent calculation results.

## Verification

Run the full test suite:

```powershell
python -m pytest -q
```

The Ollama provider tests mock HTTP responses, so CI does not require a running model or API key. Test coverage is a signal about exercised lines, not proof of security or correctness.

## Deliberate limitations / next milestones

1. Expand intent and abstention evaluation with representative business questions and adversarial malformed model responses.
2. Add multi-step diagnostic workflows only after each tool has an explicit input/output contract and bounded execution.
3. Add evidence IDs and an explanation format that separates observed facts, hypotheses, and missing data.
4. Add deployment-level controls (authentication, request rate limits, audit policy, and protected hosting) before exposing the API beyond a trusted local environment.
