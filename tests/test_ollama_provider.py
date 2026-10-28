import json
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest

from src.agent.ollama_provider import (
    OllamaProviderError,
    _validate_plan,
    plan_question_with_ollama,
)


def frame():
    return pd.DataFrame({"region": ["East", "West"], "sales": [10, 20], "units": [1, 2]})


def plan(**overrides):
    value = {
        "operation": "aggregate",
        "metric_column": "sales",
        "group_by": ["region"],
        "aggregation": "sum",
        "limit": 10,
        "clarification": "",
    }
    value.update(overrides)
    return value


def test_valid_plan_is_converted_to_internal_plan():
    actual = _validate_plan(plan(), frame())
    assert actual.operation == "aggregate"
    assert actual.metric_column == "sales"
    assert actual.group_by == ("region",)
    assert actual.aggregation == "sum"


def test_unknown_column_abstains_instead_of_reaching_tools():
    with pytest.raises(ValueError, match="do not exist"):
        _validate_plan(plan(metric_column="profit"), frame())


def test_extra_or_missing_fields_are_rejected():
    with pytest.raises(OllamaProviderError, match="missing or unexpected"):
        _validate_plan({"operation": "aggregate"}, frame())


def test_unsupported_operation_is_rejected():
    with pytest.raises(OllamaProviderError, match="unsupported operation"):
        _validate_plan(plan(operation="execute_python"), frame())


def test_ambiguous_plan_requests_clarification():
    with pytest.raises(ValueError, match="Which metric"):
        _validate_plan(plan(operation="clarify", metric_column=None, group_by=[], aggregation=None, clarification="Which metric do you mean?"), frame())


def test_duplicate_column_labels_are_blocked():
    bad = pd.DataFrame([[1, 2]], columns=["sales", "sales"])
    with pytest.raises(ValueError, match="duplicate column"):
        plan_question_with_ollama("sum sales", bad)


def test_request_contains_schema_but_no_raw_rows():
    response = {
        "message": {
            "content": json.dumps({
                "operation": "aggregate", "metric_column": "sales", "group_by": [],
                "aggregation": "sum", "limit": 10, "clarification": "",
            })
        }
    }
    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        prompt = payload["messages"][1]["content"]
        assert "sales" in prompt
        assert "10" not in prompt  # raw row values are not sent in the schema prompt
        assert payload["format"]["required"]
        return BytesIO(json.dumps(response).encode("utf-8"))

    with patch("src.agent.ollama_provider.urlopen", side_effect=fake_urlopen):
        result = plan_question_with_ollama("What is the total sales?", frame())
    assert result.metric_column == "sales"
    assert result.aggregation == "sum"
