import pandas as pd

from src.agent import ask, plan_question


def sample():
    return pd.DataFrame({
        "region": ["East", "West", "East", "West"],
        "sales": [100, 80, 120, 200],
        "units": [2, 2, 3, 5],
    })


def test_sum_is_computed_by_analytics_and_evidence_is_returned():
    response = ask(sample(), "What is the total sales?")
    assert response.status == "ok"
    assert response.plan["aggregation"] == "sum"
    assert response.evidence["records"][0]["sales__sum"] == 500
    assert "500" in response.answer


def test_grouped_average_returns_real_group_records():
    response = ask(sample(), "What is the average sales by region?")
    assert response.status == "ok"
    assert response.plan["group_by"] == ["region"]
    values = {row["region"]: row["sales__mean"] for row in response.evidence["records"]}
    assert values == {"East": 110.0, "West": 140.0}


def test_summary_request_uses_descriptive_analytics():
    response = ask(sample(), "Give me a summary of this dataset")
    assert response.status == "ok"
    assert response.evidence["operation"] == "describe"


def test_ambiguous_unknown_column_abstains_instead_of_guessing():
    response = ask(sample(), "What is the total profit?")
    assert response.status == "needs_clarification"
    assert response.evidence is None
    assert "column" in response.clarification.lower()


def test_multi_metric_request_requires_clarification():
    response = ask(sample(), "What is the sum of sales and units?")
    assert response.status == "needs_clarification"


def test_planner_does_not_accept_empty_question():
    response = ask(sample(), "   ")
    assert response.status == "needs_clarification"


def test_correlation_requires_two_named_columns():
    response = ask(sample(), "What is the correlation between sales and units?")
    assert response.status == "ok"
    assert response.evidence["operation"] == "correlation"


def test_ollama_planner_is_an_explicit_opt_in(monkeypatch):
    from src.agent import AnalysisPlan
    import src.agent.orchestrator as orchestrator

    def fake_plan(question, dataset, *, model=None, base_url=None):
        assert question == "total sales"
        assert model == "qwen3.5:4b"
        return AnalysisPlan(operation="aggregate", metric_column="sales", aggregation="sum")

    monkeypatch.setattr(orchestrator, "plan_question_with_ollama", fake_plan)
    response = orchestrator.ask(sample(), "total sales", planner="ollama", ollama_model="qwen3.5:4b")
    assert response.status == "ok"
    assert response.evidence["records"][0]["sales__sum"] == 500


def test_unknown_planner_mode_returns_controlled_error():
    response = ask(sample(), "total sales", planner="other")
    assert response.status == "error"
    assert response.evidence is None
