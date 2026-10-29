# AI_DataPilot — Manus UI polish handoff

## Scope of this patch

This patch adapts the Manus-generated analytics workspace to the existing FastAPI demo while keeping the existing API contracts and deterministic agent implementation unchanged. It is intended for a separate review branch, not a direct merge.

## Changes

- Moves the embedded page into `app/ui.html` so HTML/CSS/JavaScript can be reviewed independently of backend routes.
- Keeps the current endpoints: `/api/health`, `/api/analyze`, and `/api/diagnose-pricing`.
- Improves local CSV preview to handle quoted commas, escaped quotes, and line breaks within quoted fields; the preview is not used as the server's validation authority.
- Adds clear handling for oversized preview text and malformed CSV quoting.
- Makes the hidden file picker keyboard reachable and gives the drop zone a visible focus indicator.
- Normalizes FastAPI/Pydantic validation-error payloads for user-readable messages.
- Uses DOM `textContent` when rendering supplied cell values and results.
- Adds a small UI smoke test to catch accidental loss of key screens or API wiring.

## Verification status

- Python syntax check for `app/main.py`: passed.
- JavaScript syntax check for the inline script using Node.js: passed.
- Full Python test suite: **not independently run in this packaging environment** because a complete checkout and all branch files were not available locally.
- Browser visual inspection / Playwright: not run.
- Live Ollama/Qwen inference: not run.

The patch must still pass the full project CI suite and be checked in a browser after integration. Do not interpret syntax checks as proof of end-to-end behavior.

## Integration notes

- Base the change on `feature/agent-review-mvp`.
- Keep PR #3 open, draft, and unmerged until a reviewer confirms the integration target and the full suite passes.
- The existing `src.data` preview/prepare pipeline remains a separate integration task; this UI does not claim to replace or prove that workflow.