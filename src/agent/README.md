# AI_DataPilot Agent MVP — review build

## Current scope
This branch contains two planning paths:
- **Rules baseline**: deterministic phrase matching, available without a model.
- **Local Ollama planning adapter**: asks a local Qwen/Ollama model to produce a structured analysis plan, then validates the plan before any analytics tool runs.

Neither path is a production-ready autonomous agent. The Ollama adapter is a planner only; it does not yet generate the final explanatory narrative, infer root causes, manage multi-step diagnostic investigations, or connect to the application UI/API.

## Local setup
Install Ollama and download a compatible local model. The suggested starting point is Qwen3.5 4B:

```powershell
ollama pull qwen3.5:4b
ollama run qwen3.5:4b
```

The Ollama service normally listens at `http://127.0.0.1:11434`. Configure the model if needed:

- `AI_DATAPILOT_OLLAMA_MODEL`: defaults to `qwen3.5:4b`
- `OLLAMA_BASE_URL`: defaults to `http://127.0.0.1:11434`

Do not expose Ollama's unauthenticated API directly to the public internet. For another trusted laptop on your private LAN, configure the service deliberately, restrict access with firewall rules, and do not send private row data to it.

Example integration:

```python
from src.agent import ask
from src.data import prepare_file

dataset = prepare_file("data/raw/sales.csv")
response = ask(dataset, "What is the total sales?", planner="ollama")
print(response.to_dict())
```

For an offline deterministic baseline, omit `planner="ollama"` or use `planner="rules"`.

The adapter sends only the user's question and column names/dtypes to Ollama. It does not send raw rows, profile examples, or the full DataFrame. Every returned plan is validated against the actual column list and an allow-list of operations before execution.

## Current supported plan types
- Dataset summary / description
- One metric aggregation (sum, mean, median, min, max, count), optionally grouped by one column
- Correlation between two explicitly named columns
- Row count
- Clarification when required details are missing or unsupported

Correlation is not causation. A sales table alone does not establish that inflation, supplier behavior, or another external factor caused a price change.

## Safety boundary
- The model plans; deterministic analytics calculate.
- Never execute model-produced Python or unrestricted SQL.
- Unknown/ambiguous columns do not reach tools.
- Invalid model output, provider failure, or unsupported operations must fail closed; no made-up fallback number.
- Keep model output, execution results and final explanation as separate objects.
- Tests mock the Ollama API; no live model/API key is needed in CI.

## Next development milestones
1. Build price/cost/margin diagnostic tools using matched SKU/lot/time data.
2. Add evidence-grounded explanation that separates facts from hypotheses and cites evidence IDs.
3. Add evaluation fixtures for intent accuracy, abstention and factual-grounding failure cases.
4. Integrate with Member 4's UI/API, upload lifecycle, request timeouts and audit trail.
