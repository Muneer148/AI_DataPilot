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
