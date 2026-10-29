import pandas as pd
import pytest

from src.agent import ask, plan_question
from src.agent.planner import AnalysisPlan


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


def test_ollama_failure_fails_closed_without_rules_fallback(monkeypatch):
    import src.agent.orchestrator as orchestrator
    from src.agent.ollama_provider import OllamaProviderError

    def fail_ollama(*args, **kwargs):
        raise OllamaProviderError("simulated model unavailable")

    def unexpected_rules_fallback(*args, **kwargs):
        raise AssertionError("rules fallback must not run silently")

    monkeypatch.setattr(orchestrator, "plan_question_with_ollama", fail_ollama)
    monkeypatch.setattr(orchestrator, "plan_question", unexpected_rules_fallback)

    response = ask(sample(), "What is the total sales?", planner="ollama")

    assert response.status == "error"
    assert response.evidence is None
    assert "could not be used" in response.answer
    assert "500" not in response.answer


def test_every_planner_output_is_validated_before_execution(monkeypatch):
    import src.agent.orchestrator as orchestrator

    def forbidden_execution(*args, **kwargs):
        raise AssertionError("invalid plans must not reach the analytics executor")

    monkeypatch.setattr(orchestrator, "_execute", forbidden_execution)
    bad_plans = [
        AnalysisPlan(operation="execute_python"),
        AnalysisPlan(operation="aggregate", metric_column="profit", aggregation="sum"),
        AnalysisPlan(operation="aggregate", metric_column="sales", aggregation="execute_sql"),
        AnalysisPlan(operation="aggregate", metric_column="sales", aggregation="sum", limit=True),
        AnalysisPlan(operation="aggregate", metric_column="sales", aggregation="sum", group_by=["region"]),
        AnalysisPlan(operation="aggregate", metric_column="region", aggregation="sum"),
    ]
    for bad_plan in bad_plans:
        monkeypatch.setattr(orchestrator, "plan_question", lambda *args, **kwargs: bad_plan)
        response = ask(sample(), "What is the total sales?")
        assert response.status == "error"
        assert response.evidence is not None
        assert response.evidence.get("error", {}).get("code")


def test_grouped_row_count_uses_plan_limit(monkeypatch):
    import src.agent.orchestrator as orchestrator

    captured = {}

    def fake_aggregate(dataset, **kwargs):
        captured.update(kwargs)
        from src.analytics.contracts import AnalyticsResult
        return AnalyticsResult(
            operation="aggregate", row_count=4,
            records=[{"region": "East", "row_count": 2}],
        )

    monkeypatch.setattr(orchestrator, "aggregate_dataset", fake_aggregate)
    plan = AnalysisPlan(operation="aggregate", group_by=("region",), aggregation="count_rows", limit=1)
    response = orchestrator.ask(sample(), "count rows by region")
    # The normal planner creates this same row-count plan with its default limit=10.
    # This direct path primarily ensures execution uses the plan's bound.
    validated = orchestrator.validate_plan(plan, sample())
    orchestrator._execute(sample(), validated)
    assert captured["limit"] == 1
    assert response.status == "ok"


def test_evidence_and_answer_share_the_same_calculated_value():
    response = ask(sample(), "What is the total sales?")
    evidence_value = response.evidence["records"][0]["sales__sum"]
    assert response.status == "ok"
    assert str(evidence_value) in response.answer


def test_unexpected_execution_error_does_not_leak_internals(monkeypatch):
    import src.agent.orchestrator as orchestrator

    def fail_execution(*args, **kwargs):
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(orchestrator, "_execute", fail_execution)
    response = ask(sample(), "What is the total sales?")

    assert response.status == "error"
    assert "sensitive internal detail" not in response.answer
    assert "sensitive internal detail" not in (response.clarification or "")
    assert response.evidence is None


@pytest.mark.parametrize("question", [
    "What is total sales in 2025?",
    "What is total sales for the last month?",
    "What is total sales where region is East?",
    "Why did sales increase?",
    "Summarize the dataset and calculate total sales",
])
def test_unsupported_scope_or_mixed_intent_clarifies_instead_of_partially_answering(question):
    response = ask(sample(), question)
    assert response.status == "needs_clarification"
    assert response.evidence is None
    assert response.clarification


def test_non_numeric_correlation_is_rejected_before_execution():
    response = ask(sample(), "What is the correlation between sales and region?")
    assert response.status == "error"
    assert response.evidence["error"]["code"] == "NON_NUMERIC_COLUMN"
