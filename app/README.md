# Local review demo

This is a deliberately small, local-first application baseline for the First Review. It demonstrates a complete narrow path: CSV text input -> question -> rules or optional Ollama plan -> deterministic analytics -> answer + evidence.

## Start

From the repository root with Python 3.11 recommended:

    python -m pip install -r requirements.txt
    python -m uvicorn app.main:app --reload

Open http://127.0.0.1:8000. The health endpoint is http://127.0.0.1:8000/api/health.

The page starts with a clearly synthetic rice-pricing dataset. The dedicated price/cost diagnostic compares quantity-weighted per-product price and cost rates by period, reports whether the spread changed, and explicitly lists limitations. Try:
- What is the average selling_price_per_kg by month?
- What is the average purchase_cost_per_kg by month?
- What is the average sales_revenue by product?
- What is the correlation between purchase_cost_per_kg and selling_price_per_kg?
- Click Run price/cost diagnostic to compare each product's selling-price and purchase-cost proxy across periods.
- What is total profit? (expected to ask for clarification rather than invent a result)

To use your own data, paste a small CSV with a header row. The demo accepts at most 1,000,000 characters, 5,000 data rows and 50 columns. Duplicate or empty column headers are rejected. CSV content is processed in memory and is not written to disk by this app.

## Planner choices

- Rules baseline works without a model and should be the default during the review if the model is not confirmed working.
- Local Qwen via Ollama is optional. Install Ollama, pull the configured model, ensure the local Ollama service is running, and select it in the UI. No live-model availability is assumed by CI tests.

## Test

    python -m pytest -q

## Important limitations

- This is a review baseline, not the final application or a production deployment.
- This branch currently accepts CSV text and directly creates a pandas DataFrame for the demo. Integrate it with the audited src.data preview/prepare workflow once that branch is brought into the agreed integration baseline.
- The first Ollama integration is a planner, not a general autonomous agent. Final narrative generation and multi-step diagnosis are not implemented here.
- The example dataset is synthetic, not external market data.
- The price/cost diagnostic treats quantity-weighted purchase cost as a proxy; it is not accounting-grade cost of goods sold unless source rows correctly link costs to items actually sold.
- Internal business data alone cannot establish macroeconomic causes such as inflation. The agent must identify missing evidence and distinguish observed facts from hypotheses.
- Do not expose an unauthenticated Ollama endpoint to the public internet. Do not use this demo as a multi-user service without authentication, dataset/session isolation, safer operational logging, and deployment hardening.

## Responsive workspace UI

The FastAPI home route serves the interface from `app/ui.html`; backend endpoints remain in `app/main.py`. The UI includes CSV file selection/drag-and-drop, a pasteable CSV field, a local preview, rules/Ollama planner selection, result/evidence inspection, grouped comparison bars, and the existing price/cost diagnostic.

The browser preview handles quoted commas, escaped quotes, and line breaks inside quoted CSV fields for orientation only. It is not authoritative validation: the server-side parser and configured limits remain authoritative. Validation errors returned by FastAPI are converted to readable messages in the UI. Dataset values are rendered with DOM text APIs rather than inserted as HTML.

The UI smoke tests check that the main workspace and the real API calls remain present. These static tests do not replace browser testing, manual visual inspection, or a live Ollama inference check.

## Preview-first data preparation and file uploads

The home interface now supports CSV paste plus uploads of CSV, XLSX, XLS and JSON. Uploaded bytes are parsed in memory through `DataLoader.load_bytes`; the API caps uploads at 10 MiB, then separately enforces 5,000 rows and 50 columns. The standalone data-layer loader has a 100 MiB default limit for other trusted local workflows, but the web API applies the smaller cap.

### Workflow

1. Select a file or paste CSV.
2. Select **Validate & preview cleaning**.
3. Review source validation findings, the proposed cleaning report, and the first five source/proposed-cleaned rows.
4. Approve the proposed preparation.
5. Ask a question. The API re-runs the same deterministic preparation on the submitted input and then runs the allow-listed analytics operation.

The preview is non-destructive. The browser receives up to five source and cleaned sample rows because the user explicitly requests a preview; the application does not persist those rows. Profile example values and top values remain excluded from the serialized profile by default. The optional Ollama planner receives the question and schema context only, not uploaded row data.

API routes:
- `GET /api/health`
- `POST /api/preview` — JSON body with `csv_text`
- `POST /api/preview-upload` — multipart file upload
- `POST /api/analyze` — JSON body with `csv_text`, `question`, optional `planner`, and `prepare`
- `POST /api/analyze-upload` — multipart upload plus `question`, `planner`, and `prepare`
- `POST /api/diagnose-pricing` — pasted CSV
- `POST /api/diagnose-pricing-upload` — file upload

The prepare flag records the caller's request to run deterministic cleaning; this demo does not maintain a server-side session/token proving that an earlier preview was displayed. The UI gates its analysis button on preview and explicit approval, while API clients must implement the same preview/approval policy themselves.

Install dependencies with `python -m pip install -r requirements.txt`. XLSX parsing uses `openpyxl`; legacy XLS parsing uses `xlrd`; multipart browser uploads use `python-multipart`.

This remains a local review application. Do not expose it publicly without authentication, request/session isolation, rate limits, appropriate operational logging, and deployment hardening.
