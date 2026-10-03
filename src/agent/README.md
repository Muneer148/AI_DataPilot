# Member 2 — AI / Agent Intelligence

> **Owns:** turning a user's natural-language question into a safe, executable analysis plan, then explaining the verified result.
>
> **Project:** AI_DataPilot · **Target branch:** `feature/ai-agent`

## 1. Why this feature exists

Users should be able to ask questions such as “Which region had the highest sales last quarter?” without writing SQL or Python. The agent interprets the question and coordinates tools, but it must **not invent numbers or treat an LLM response as evidence**.

The agent's job is to decide *what analysis to run*. Deterministic SQL / analytics tools do the actual computation. The final response should explain the result and identify the evidence used.

## 2. Where it fits

```text
User question
    ↓
Intent + entity / time / metric extraction
    ↓
Dataset context + schema inspection
    ↓
Structured analysis plan
    ↓
Tool selection and safety checks
    ↓
SQL / analytics execution (other modules)
    ↓
Validate returned evidence
    ↓
Natural-language explanation + provenance
```

Member 1 owns ingestion, cleaning, validation, profiling and the analysis-ready data contract. Member 3 owns deterministic statistics and visualization. Member 4 owns API/UI and request lifecycle. **Do not reimplement those modules inside the agent.**

## 3. Data contract to integrate with

The integration target is the data foundation on `feature/data-foundation` (latest documented commit: `43a96ea444abcb9a927e88a7abdad025d70d4480`). Before implementing, bring the current data-foundation branch into your working branch through the team's agreed merge/rebase workflow.

The public API is exported from `src.data`:

- `preview_file(...)` / `preview_dataframe(...)`: inspect quality before preparation.
- `prepare_file(...)` / `prepare_dataset(...)`: create an `AnalysisReadyDataset`.
- `AnalysisReadyDataset.dataframe`: local source of truth for deterministic analysis.
- `AnalysisReadyDataset.metadata`, `.profile`, `.validation`, `.source_validation`, `.cleaning`, `.provenance`: evidence for planning and explanation.
- `AnalysisReadyDataset.to_model_context(max_columns=100)`: bounded schema/profile context; raw rows and example values are excluded by default.

Example:

```python
from src.data import prepare_file

dataset = prepare_file("data/raw/sales.csv")
context = dataset.to_model_context(max_columns=100)
# Give the agent context for planning. Do not send the whole DataFrame to the LLM.
```

Keep model context bounded. Exact answers must come from an executed tool result, not from the profile or the model's general knowledge.

## 4. What to build

Suggested module layout (adjust if the existing codebase already establishes a better pattern):

```text
src/agent/
├── __init__.py
├── schemas.py       # Pydantic/dataclass request, plan, tool-result, answer contracts
├── intent.py        # extract metric, dimensions, filters, time range and answer type
├── planner.py       # convert intent + dataset context into a structured plan
├── tools.py         # tool registry and typed tool interfaces
├── orchestrator.py # execute approved steps, manage errors and evidence
├── prompts.py       # concise versioned prompts; no business logic hidden in prompts
└── README.md
tests/
└── test_agent.py
```

### Build in this order

1. **Define typed contracts first.** Create an `AnalysisRequest`, `AnalysisPlan`, `PlanStep`, `ToolResult`, and `GroundedAnswer`. A plan step should identify the operation, required columns, filters, output shape and expected evidence.
2. **Start with deterministic intent routing.** Support a small set of clear question types: aggregate/sum/average/count, group-by comparison, sorting/top-N, filtering, trend-over-time, and descriptive summary. Return “unsupported / need clarification” when key details are ambiguous.
3. **Add an LLM provider adapter.** Keep provider-specific SDK calls behind one interface. Validate model output against your schema; retry only in a bounded way, then return a useful error. Keep secrets in environment variables and out of Git.
4. **Plan before execution.** Check that referenced columns exist in dataset metadata. Make missing/ambiguous column names a clarification request rather than silently guessing.
5. **Connect tools through interfaces.** Call Member 3's analytics functions and the team's approved SQL execution layer. Do not use `eval`, execute arbitrary model-generated Python, or give the model unrestricted database access.
6. **Ground the answer.** Build the final response from tool outputs: result values, units, filters, time window, row counts where useful, warnings and provenance. If execution fails, say so; never fabricate a fallback number.
7. **Add traces and tests.** Record the plan, selected tool, validation outcome and evidence identifiers without logging secrets or unnecessary raw records.

## 5. Safety and reliability rules

- Treat model output and uploaded data as untrusted input.
- Prefer structured tool arguments over free-form generated code.
- SQL, if used, must be read-only and pass the shared SQL validator; parameterize user values.
- Enforce allowed operations, timeouts, result-size limits and step limits.
- Never claim a calculation succeeded unless a tool returned a successful result.
- Preserve the distinction between **plan**, **execution result**, and **explanation**.
- If the data is invalid or required columns are absent, stop and return the data-quality finding instead of guessing.
- Do not place API keys, real customer data, or secrets in prompts, logs, fixtures, or commits.

## 6. Minimum acceptance criteria

- [ ] At least 5 supported question patterns have schema-validated plans.
- [ ] Unknown columns and ambiguous questions trigger clarification or a clear unsupported response.
- [ ] Tool errors/timeouts produce controlled errors, not invented answers.
- [ ] The agent can consume `AnalysisReadyDataset.to_model_context()`.
- [ ] Final numerical claims are linked to actual tool output/evidence.
- [ ] No arbitrary Python execution or unrestricted SQL is possible.
- [ ] Unit tests cover valid plans, malformed model output, missing columns, tool failure and prompt-injection-like input.
- [ ] Tests run with `pytest -q`; no live API key is required for the default test suite (mock the provider).

## 7. Definition of done

A user can ask one of the supported analytical questions about a prepared dataset; the agent creates a typed plan, calls the appropriate deterministic tool, checks the result, and produces an explanation that matches the returned evidence. The happy path and failure paths are tested.

## 8. Coordination checklist

- **Member 1:** use the exported data contract; request changes through a focused issue rather than editing `src/data/` directly.
- **Member 3:** agree on function signatures and result/evidence schemas before wiring tools.
- **Member 4:** agree on the request/response schema and how the API reports clarification, validation and execution errors.
- Keep commits small and focused; add tests with each behavior. Do not merge into `main` directly.
