"""Opt-in live Ollama smoke test; never contacts a model during normal CI.

Run explicitly with AI_DATAPILOT_RUN_OLLAMA_INTEGRATION=1 after starting Ollama
and pulling the configured model. This test is intentionally separate from mocks.
"""
import os

import pandas as pd
import pytest

from src.agent import ask


pytestmark = pytest.mark.skipif(
    os.getenv("AI_DATAPILOT_RUN_OLLAMA_INTEGRATION") != "1",
    reason="Set AI_DATAPILOT_RUN_OLLAMA_INTEGRATION=1 to run the live Ollama smoke test.",
)


def test_live_ollama_plan_executes_only_deterministic_analytics():
    dataset = pd.DataFrame({"sales": [100, 150, 250], "units": [1, 2, 3]})
    response = ask(
        dataset,
        "What is the total sales?",
        planner="ollama",
        ollama_model=os.getenv("AI_DATAPILOT_OLLAMA_MODEL"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL"),
    )

    assert response.status == "ok", response.clarification
    assert response.plan["operation"] == "aggregate"
    assert response.plan["metric_column"] == "sales"
    assert response.plan["aggregation"] == "sum"
    assert response.evidence["records"][0]["sales__sum"] == 500
    assert "500" in response.answer
