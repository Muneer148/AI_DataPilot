# AI_DataPilot Agent MVP — review build

## What this is
A deterministic, rule-based orchestration baseline that maps a limited set of explicit questions to existing analytics functions. It is **not yet an LLM-powered conversational agent**. The purpose is to demonstrate the control flow and the non-negotiable rule that numerical answers come from executed analytics, not model guesses.

## Supported examples
- `What is the total sales?`
- `What is the average sales by region?`
- `Give me a summary of this dataset`
- `What is the correlation between sales and units?`

Column names must be stated explicitly and match dataset labels. Unsupported or ambiguous questions return `needs_clarification` without inventing a value.

## Flow
`question -> schema-aware rule planner -> allow-listed analytics function -> evidence envelope -> short explanation`

## Safety
- Does not execute generated Python or SQL.
- Does not require an API key or send dataset contents to a remote model.
- Uses existing deterministic analytics functions for calculations.
- Returns the underlying result envelope in `evidence`.
- Abstains when the intent or column mapping is unclear.
- Treats unexpected execution errors as failure, never as a reason to guess a result.

## Known limitations
- Rule-based phrase matching; no general language understanding, memory, multi-step planning, or LLM provider integration.
- No automatic filtering/time-window extraction or chart recommendation in this MVP.
- Count-row behavior and response wording should be refined in a later integration pass.
- This is not production-ready; API/UI integration belongs to Member 4.

## Run tests
`python -m pytest -q tests/test_agent.py`

Tests are designed to run without live model credentials.
