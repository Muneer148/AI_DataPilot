# AI_DataPilot — Team Prompts for All Four Members

Use the **Shared Brief** before the prompt assigned to each member. Give each person only their own module prompt first; do not ask all four members or their AI tools to rewrite the whole repository. The repo and test output are the source of truth.

## Shared Brief — paste before every member prompt

You are contributing to **AI_DataPilot**, a B.Tech project for an explainable, evidence-grounded business-data analyst. The system should turn a user's data question into a validated analytical plan, run approved deterministic analytics, and present results with evidence and limitations.

Repository: `Muneer148/AI_DataPilot`

Current work to inspect: `feature/agent-review-mvp`, analytics/data feature branches and their open draft PRs, plus the new UI review branch `feature/manus-ui-polish`.

Rules for every contributor:

1. Inspect the actual branch, source, contracts, tests and PR diff before proposing code. Do not treat README roadmap items or AI-generated summaries as proof that a feature is implemented.
2. Work only in the branch assigned by the project lead. Do not edit another member's files, merge a PR, force-push, rewrite history, or commit to the default branch.
3. Avoid duplicate implementations. Reuse existing data-preparation, analytics, visualization and agent functions through their real contracts.
4. Numerical results must come from deterministic computations on the actual dataset. The model may interpret intent and propose a validated plan; it must not invent values or evidence.
5. Do not execute model-generated Python, shell commands, arbitrary SQL, or other code. Do not send private datasets or secrets to external services. Preserve server-side validation and configured limits.
6. Add focused tests for edge cases and failure modes. Clearly distinguish tests that actually ran from tests that were only proposed or reviewed.
7. Do not claim that code is secure, production-ready, integrated, deployed, or passing unless the relevant behavior was verified. Report assumptions and unknowns explicitly.
8. Keep the change small and reviewable. Before coding, return a brief plan and acceptance criteria. After coding, report exact files changed, commands run, actual results, remaining risks, and the handoff needed by the next module.

The goal is a reliable, demonstrable end-to-end path—not four disconnected demos.

---

## Prompt for Member 1 — Data Engineering & Data Quality

You own the **data foundation**: ingestion, schema detection, validation, cleaning, profiling, provenance, and the analysis-ready data contract.

First inspect the current data module and the `feature/data-foundation` work. Map what is genuinely implemented and tested before changing anything. Do not infer completeness from the root README or the planned 25-week roadmap.

Your tasks:

1. Document the actual loaders/formats supported, schema/type inference, validation checks, cleaning behavior, profiling output, provenance fields, and error handling.
2. Check empty files, malformed CSV, quoted delimiters/newlines, duplicate or blank headers, mixed types, missing values, duplicate rows, oversized input, and preservation of the source dataset.
3. Define the stable `AnalysisReadyDataset` (or current equivalent) contract that Member 2 and Member 3 can consume. Specify field names/types, null/missing-value semantics, provenance, and what the module guarantees versus what it does not.
4. Ensure previews and logs do not expose sensitive values unnecessarily. Keep examples or raw-value serialization opt-in if the current design requires it.
5. Add focused tests with synthetic fixtures, including edge cases. For cleaning, show before/after values and record what transformation occurred.
6. Coordinate the contract with Member 3 before changing public interfaces. Do not silently change column names or missing-value semantics downstream modules rely on.

**Acceptance criteria:** documented supported formats and actual behavior; a stable, typed handoff contract; tests for malformed/empty/duplicate/missing/oversized inputs; provenance and transformation reporting; no unrelated edits.

**Handoff to the team:** exact entry points and contracts, files changed, hand-calculated fixtures where applicable, actual test output, known parsing/cleaning limitations, and any contract decisions requiring team approval.

---

## Prompt for Member 2 — AI Agent / “Brain”

You own the **agent intelligence**: question interpretation, intent/plan creation, validation, safe operation selection, orchestration, and user-facing clarification/abstention behavior.

Start by inspecting `src/agent/`, especially the current planner, orchestrator, provider adapter, and tests on `feature/agent-review-mvp`. This branch already contains a bounded agent MVP; preserve it unless code evidence demonstrates a defect. Do not replace it with a general autonomous agent.

Your tasks:

1. Create a supported-question matrix mapping example questions to validated plan fields and the exact analytics function that executes each plan.
2. Ensure every plan is validated for field types, allow-listed operation, referenced columns, aggregation, grouping, and result bounds before execution.
3. Use deterministic analytics for numerical results. The model must never provide the final numerical answer as the source of truth.
4. Ensure ambiguous, unsupported, malformed, or ungrounded questions return a clarification or safe error rather than a guessed value.
5. Preserve explicit opt-in for the local Ollama planner and fail-closed behavior when the provider is unavailable. Never silently switch planners or generate fake success.
6. Preserve the data privacy boundary: no raw dataset rows are sent to the planner unless the project lead explicitly approves a redesigned data flow after privacy review. Do not execute generated code or unrestricted SQL.
7. Test malformed model responses, unknown columns, unsupported operations, unexpected exceptions, provider timeouts/failures, and evidence consistency.

**Acceptance criteria:** typed/validated plan schema; safe clarification and failure paths; no execution of model-generated code; numerical output comes from deterministic analytics; provider-failure tests and actual CI evidence.

**Handoff to the team:** supported-question matrix, plan/result contract, provider configuration, exact test run and output, unsupported cases, privacy boundary, and the next integration dependency for Member 4.

---

## Prompt for Member 3 — Analytics & Visualization

You own **deterministic analytics and visualization specifications**. Reuse `src/analytics/` and its current result/chart contracts; do not create a second analytics engine inside the agent or FastAPI layer.

Your tasks:

1. Audit the existing analytics functions for descriptive statistics, aggregations/groupings, correlation, trends, outlier candidates, limits, warnings, and JSON-serializable results. Report the actual supported operations and their missing cases.
2. For each metric, state inputs, required types, null handling, filters, grouping semantics, units, result keys, warnings, and limitations.
3. Build small fixtures where expected values can be hand-calculated independently. Cover empty/all-null/mixed-type data, infinity/NaN, duplicate names, overflow-prone sums, missing dates, zero denominators, invalid filters, and small sample counts as appropriate to the implemented functions.
4. Ensure chart specifications are derived from actual computed results and that chart labels/values match the evidence table. Validate chart data types and finite numeric values; handle missing values explicitly.
5. Label correlations, trends, and outlier candidates as descriptive evidence, not proven causes. Do not use an LLM to compute or alter metric values.
6. Coordinate the input contract with Member 1 and the result/display contract with Member 4. Avoid changing public names without an agreed migration and tests.

**Acceptance criteria:** documented metric semantics; hand-calculated fixtures; regression tests for numeric/data edge cases; chart-to-result consistency checks; explicit limitations and warnings.

**Handoff to the team:** public function/result/chart contracts, exact tests and outcomes, examples with expected numbers, known statistical limitations, and any frontend requirements that are truly necessary.

---

## Prompt for Member 4 — Application, Backend & Integration

You own the **application shell, FastAPI routes, UI/UX, API integration, and end-to-end workflow**. The new Manus UI work has been published to `feature/manus-ui-polish` as a review branch. Inspect that branch and its diff; do not paste its source files over the repository blindly.

Your tasks:

1. Trace the real request path from UI to route, data validation/preparation, agent/analytics call, result/evidence contract, and rendering. Identify where the current CSV demo does or does not use Member 1's analysis-ready data workflow.
2. Review `app/main.py`, `app/ui.html`, current API schemas, `tests/`, and the UI-polish review notes. Keep the existing FastAPI backend and API behavior unless a specific gap justifies a tested change.
3. Maintain the working paths for `/api/health`, `/api/analyze`, and `/api/diagnose-pricing`. Verify request and response shapes rather than guessing them.
4. Preserve server-side validation and resource limits. The browser CSV preview is for orientation only, not authoritative validation. Handle FastAPI/Pydantic error arrays clearly and safely.
5. Ensure user-provided cell values and model output are inserted as text, not executable HTML. Keep errors actionable without showing stack traces, secret configuration, or private data.
6. Implement and test loading, empty, successful, clarification, invalid-data, API-unavailable, Ollama-unavailable, and diagnostic-limitation states. Keep the file picker keyboard accessible and the layout responsive.
7. Align the UI with Member 1's data-preview/prepare contract and Member 3's evidence/chart schema. Do not duplicate data cleaning or analytics within JavaScript.
8. Run actual backend tests and the browser checks available in the environment. If you cannot run Playwright or inspect a browser visually, report that as unverified rather than claiming end-to-end validation.

**Acceptance criteria:** local app starts from documented commands; UI calls real routes; successful results and evidence come from the backend; limits and failure states are tested; responsive/keyboard behavior is reviewed; no unrelated agent/data/analytics rewrites.

**Handoff to the team:** files/routes changed, API contract notes, screenshots or browser test evidence if actually captured, all commands and outputs, unresolved integration gaps, startup instructions, and the exact commit/branch/PR for review.

---

## Prompt for Project Lead / Integrator

You coordinate the four workstreams. Start with the open draft PRs and latest commits. Identify the approved integration base and dependencies; do not assume that merging by branch order alone will produce a working application.

1. Keep one owner per module and one active code-editing task per shared working tree. Have members return scoped branches/PRs and handoffs rather than editing the same files concurrently.
2. Track cross-module contracts: analysis-ready dataset, plan schema, analytics result/evidence, chart specification, and API request/response.
3. Maintain a decision log for any contract changes. Record decision, alternatives, reason, compatibility impact, owner, and validation required.
4. Review each diff for scope, tests, secrets, duplicated logic, unsupported claims, unsafe execution, and accidental data disclosure.
5. Integrate incrementally. After each integration, run the complete test suite and relevant end-to-end checks on the combined branch—not merely on separate feature branches.
6. For the demo, verify the sequence: upload/read dataset → server validation/preparation → question → validated plan → deterministic calculation → evidence/result → chart/table → honest limitations.
7. Do not mark a feature complete because a model says it is done. Record actual CI links, commands/output, browser evidence, and failures.
8. Do not merge or change PR readiness until the owners have reviewed their contracts, the combined tests pass, and the project lead explicitly approves the integration.

**Required output:** current branch/PR map, dependency order, contract decisions, prioritized tickets, acceptance checklist, combined test results, demo blockers, and a truthful status report distinguishing verified, partial, missing, and unknown.