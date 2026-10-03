# Member 4 — Application, Backend & Integration

> **Owns:** the user-facing workflow and the reliable connection between data preparation, agent planning, analytics, and results.
>
> **Project:** AI_DataPilot · **Target branch:** `feature/application`

## 1. Why this feature exists

The data, agent and analytics modules are useful only if a user can upload a dataset, understand data-quality issues, ask a question, see a result/chart, and recover from errors. This layer coordinates the modules and exposes a stable interface; it should not reimplement their business logic.

## 2. End-to-end product workflow

```text
Browser / client
   ↓
API: upload dataset
   ↓
Member 1: preview + validation
   ↓ user confirms / corrects options
Member 1: prepare AnalysisReadyDataset
   ↓
API: analytical question
   ↓
Member 2: plan + orchestrate tools
   ↓
Member 3: deterministic result + optional chart
   ↓
API response: answer + evidence + warnings
   ↓
Client renders result, chart and provenance
```

Keep the initial version small: one uploaded dataset per session, a preview-first upload flow, a small supported set of analytical questions, and clear error messages. Add multi-user persistence or complex authentication only when the team has agreed requirements for it.

## 3. Integration contract

The data foundation target is `feature/data-foundation`, latest documented commit `43a96ea444abcb9a927e88a7abdad025d70d4480`. Before implementation, bring the latest data foundation into your working branch through the team's agreed merge/rebase workflow.

The data API is exported by `src.data`:

- `preview_file(...)` / `preview_dataframe(...)` for a non-destructive preview.
- `prepare_file(...)` / `prepare_dataset(...)` for final preparation.
- `DatasetPreparationPreview.ready` and `.to_dict()` for status and safe preview metadata.
- `AnalysisReadyDataset` for downstream analytics and agent orchestration.
- `AnalysisReadyDataset.to_model_context()` for bounded model-facing metadata—not raw dataset rows.

Do not call the LLM directly from an HTTP route. Put orchestration behind a service layer so it can be tested without running the web server.

## 4. What to build

Suggested initial structure (adapt to existing repository decisions):

```text
app/
├── __init__.py
├── main.py             # FastAPI app and route registration
├── schemas.py          # request/response models
├── dependencies.py     # service wiring / configuration
├── services/
│   ├── datasets.py     # upload, preview, prepare, session lifecycle
│   └── questions.py    # agent + analytics orchestration
├── routes/
│   ├── datasets.py     # upload, preview, prepare, status
│   └── analysis.py     # ask question, retrieve result
├── static/             # optional static assets
└── README.md
tests/
└── test_api.py
```

### Build in this order

1. **Agree on API schemas.** Use typed Pydantic request/response models. Decide how a dataset/session is referenced, how a preview is approved, and how errors/warnings are represented.
2. **Create a health endpoint.** Add `GET /health` with a small predictable response and a test.
3. **Add safe upload handling.** Validate extension/content type and size, generate server-side identifiers and filenames, store uploads in a controlled temporary/data directory, and never trust a client-provided path. Do not commit uploaded datasets.
4. **Implement preview then prepare.** Call Member 1's workflow. Return quality findings and proposed changes before allowing the final prepared dataset to be used. If `preview.ready` is false, show actionable errors; do not proceed as if the data were valid.
5. **Add an analysis endpoint.** Accept a dataset/session identifier plus a natural-language question. Resolve the prepared dataset server-side, call the agent service, and return its structured answer, result table, warnings, evidence and optional chart specification.
6. **Keep request handling thin.** Routes should validate inputs and call services; they should not contain SQL generation, pandas calculations or prompts.
7. **Handle lifecycle and errors.** Add timeouts, bounded uploads/results, cleanup for temporary files, stable error codes and logging that excludes secrets/raw data.
8. **Write integration tests.** Use small synthetic CSV fixtures and mock external model calls. Test the entire upload → preview → prepare → question → response flow.
9. **Document local setup.** Explain environment variables, startup command, endpoints and sample requests. Never put API keys in README or commit a real `.env`.

## 5. Suggested API surface

These are proposed endpoints to implement and coordinate—not existing endpoints guaranteed to be present.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Confirm the API is running. |
| `POST /datasets` | Upload a CSV/XLSX/XLS/JSON file; return a dataset ID and upload status. |
| `POST /datasets/{id}/preview` | Run data-quality checks and return safe preview metadata. |
| `POST /datasets/{id}/prepare` | Finalize preparation using approved cleaning options. |
| `GET /datasets/{id}` | Return dataset status, schema summary and provenance. |
| `POST /datasets/{id}/questions` | Run a supported question and return answer, result/evidence, warnings and optional chart data. |

Use a stable error envelope, for example:

```json
{
  "error": {
    "code": "DATA_VALIDATION_FAILED",
    "message": "The dataset is not ready for analysis.",
    "details": []
  }
}
```

Never expose filesystem paths, stack traces, API keys or internal secrets in client-facing errors.

## 6. Reliability and security rules

- Uploaded filenames and paths are untrusted; use server-generated storage names and prevent path traversal.
- Set file size, request time and result-size limits.
- Never execute user-supplied Python or unrestricted SQL.
- Keep API keys in environment variables; provide a safe `.env.example` with placeholders only.
- Do not store raw data in application logs or send complete DataFrames to the LLM.
- Separate temporary upload storage from tracked source code; remove files according to a documented lifecycle.
- Make dataset IDs unguessable enough for the intended single-user prototype; do not claim multi-user authorization unless it is actually implemented.
- Return clear validation, clarification, unsupported-question and execution-error statuses.
- Do not claim a question succeeded until the agent/analytics service has returned a valid result.

## 7. Minimum acceptance criteria

- [ ] API starts locally using documented instructions and `GET /health` succeeds.
- [ ] Upload rejects unsupported, empty and oversized files with stable error codes.
- [ ] Preview shows quality findings before final preparation.
- [ ] Invalid previews cannot be treated as prepared datasets.
- [ ] Prepared datasets can be referenced without exposing server filesystem paths.
- [ ] Question endpoint returns structured answer, result/evidence, warnings and optional chart information.
- [ ] Tests cover success and failure paths using mocked model providers.
- [ ] Errors and logs do not leak raw rows, secrets or stack traces.
- [ ] Tests run with `pytest -q`; no external model key is required for the default suite.

## 8. Definition of done

A user can upload a supported dataset, review data quality, prepare it, ask a supported question and receive a grounded answer with evidence and an optional chart. The flow is covered by automated integration tests and can be run using the README instructions.

## 9. Coordination checklist

- **Member 1:** use the preview/preparation API; don't bypass validation or edit `src/data/` directly.
- **Member 2:** agree on request/response schemas, clarification states and orchestration errors.
- **Member 3:** agree how tabular results, warnings and chart specifications are returned.
- Keep route handlers thin, commit tests with each endpoint, and do not merge into `main` directly.
