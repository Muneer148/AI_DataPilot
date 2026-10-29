# AI_DataPilot — Team Lead Integration Plan

**State:** active integration checklist; this is coordination documentation, not evidence of a release.

## 1. Non-negotiable ownership boundaries

| Owner | Owns | Must not independently rewrite |
|---|---|---|
| Member 1 — Data Engineering & Data Quality | `src/data/`: loading, schema, validation, cleaning, profiling, provenance, `AnalysisReadyDataset`, preparation preview | Agent planner, analytics math, web UI |
| Member 2 — Agent Intelligence | `src/agent/`: intent/planning, provider adapter, approved tool selection, safe orchestration, clarification | Data preparation algorithms, chart generation, application shell |
| Member 3 — Analytics & Visualization | `src/analytics/`, `src/visualization/`: deterministic calculations, result contracts, chart specifications/figures | File loaders, UI routes, LLM-generated numerical answers |
| Member 4 — Application & Integration | `app/`: API wiring, file upload, preview/approval workflow, UI, user-facing errors, local run instructions | Reimplementing data cleaning, analytics calculations or agent planning |
| Project lead / integrator | Contracts, issue/branch coordination, PR reviews, integration gates, final evaluation and demo readiness | Quietly bypassing module owners or describing untested work as complete |

The shared integration branch must keep each module as the source of truth. Avoid copying algorithms between modules to "make the demo work."

## 2. Cross-module contracts

### Data foundation → Agent and Analytics

- Downstream code accepts a pandas DataFrame or an `AnalysisReadyDataset` object exposing `.dataframe`.
- The prepared contract carries `metadata`, `profile`, `validation`, `source_validation`, `cleaning`, and `provenance`.
- Call `AnalysisReadyDataset.to_dict()` or `to_model_context()` for bounded metadata; examples/top values are opt-in because they can reveal sensitive values.
- Do not assume `duplicate_rows == 0` when `duplicate_check_skipped == true`; the count can be unknown.
- Cleaning must be non-mutating and auditable. Duplicate rows remain unless an explicit configuration says otherwise.
- Preview output and final preparation must use the same cleaning configuration.

### Agent → Analytics

- The agent returns a validated, allow-listed plan; it never executes model-generated code or arbitrary SQL.
- Numerical computation remains deterministic within `src/analytics/`.
- Unsupported/ambiguous requests ask for clarification. Provider errors fail closed; they do not silently change planner mode.
- Evidence records/metrics/assumptions/warnings from analytics are the source of truth for displayed numbers.

### Backend → UI

- The UI calls the real API; it must not ship fabricated answer/evidence/chart data.
- Data preparation is preview-first in the UI: validate/preview, review source findings and proposed changes, explicit approval, then analyze.
- The request carries the explicit `prepare` choice; API clients other than the UI must implement the same preview/approval interaction. This local demo does not keep a session proving that an earlier preview was viewed.
- Uploaded bytes are parsed in memory. Web uploads are capped at 10 MiB, 5,000 rows and 50 columns.
- Supported upload extensions are CSV, XLSX, XLS and JSON when the corresponding parsing engine is installed.
- The browser receives only five source and proposed-cleaned sample rows in the explicit preview response. It must render all dataset values with DOM text APIs, never unsafe HTML insertion.
- Keep privacy notes accurate: preview sample values are returned to the local user's browser when requested; raw dataset rows are not included in Ollama planner context.

## 3. Current workstreams and PR coordination

- **PR #1 — Member 3 analytics:** draft; target `feature/data-foundation`.
- **PR #2 — Member 1 data-quality audit:** draft; target `feature/data-foundation`.
- **PR #3 — Agent MVP:** draft; target `feature/analytics`.
- **PR #6 — UI and end-to-end integration candidate:** draft; branch `feature/manus-ui-polish`, target `feature/analytics`. It contains the UI plus a copy of the data foundation needed to test the combined branch; do not treat this as an instruction to bypass PR review.
- **PR #7 — Member 1 foundation hardening:** draft; target `feature/data-foundation`.

These branches currently have differing bases. Do not blindly merge every PR into the default branch or assume one feature branch already contains another branch's latest commit. The lead must inspect the actual merge base, changed files and CI on the intended integration branch before each merge. Do not retarget or merge a PR just to make a green status appear.

## 4. Recommended integration sequence

1. Review and pass Member 1's data foundation and follow-up hardening, including duplicate-status reporting, lossless rename audit details, and byte-based upload tests.
2. Ensure Member 3 analytics tests pass with a real prepared dataset and verify that provenance/warnings survive serialization.
3. Integrate Member 2's agent against the agreed prepared-data contract; retain plan validation and fail-closed behavior.
4. Integrate Member 4's API/UI with preview-first preparation and the real analysis/evidence result contract.
5. Run the full suite on the same combined branch. Test data source → preview → approval → preparation → question → deterministic result/evidence → chart.
6. Test at least one malformed input, one blocked validation, one unsupported question, one no-Ollama run, one Ollama-unavailable case, and one upload parse/size error.
7. Review accessibility, safe rendering, resource limits, secret handling, no unintended data persistence, and setup documentation.
8. Only after a reviewed PR, passing CI, reproducible local demo and team sign-off may the lead mark the integration PR ready or merge it. The project lead must not state that live Ollama inference or deployment passed unless directly verified.

## 5. Required pull-request template

Each member's PR must state:

- **Scope / non-goals:** exactly what changed and what did not.
- **Files changed:** short reason for each important file.
- **Contract impact:** request/result schema changes and downstream consumers.
- **Test evidence:** exact commands, run URLs, passed/failed/skipped results.
- **Security/privacy impact:** data path, logging, resource limits and secret handling.
- **Known gaps:** features not implemented and checks not run.
- **Demo steps:** reproducible commands and example input/output.
- **Integration dependencies:** what must be merged or available before this module is usable.

## 6. Acceptance commands

From the repository root, after integrating the intended branches:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000`, confirm `/api/health`, and manually verify the preview/approval path and a real question. CI cannot verify visual quality or live Ollama/Qwen unless those checks are explicitly configured.

## 7. Release blockers

Do not release if any of the following remain:
- a claimed result is not grounded in returned analytics records;
- cleaning changes data without a preview/config/report;
- duplicate detection silently returns zero when it was skipped;
- UI or API returns source rows to an external provider without an explicit approved design;
- unsupported operations are passed to the execution layer;
- upload content can bypass byte/row/column limits;
- an exception leaks sensitive internals;
- the web UI has non-functional buttons or sample/fake metrics presented as real;
- tests or deployment are claimed as successful without evidence.

## 8. Demo scope statement

The current goal is a bounded, local-first analytics copilot for a reproducible academic demo. It is not yet a production multi-user BI platform, autonomous multi-step agent, or production SOC assistant. Keep claims aligned with functionality that has actually been tested.
