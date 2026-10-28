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
