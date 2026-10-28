"""Local Ollama adapter for schema-constrained analysis planning.

The model sees the question and column names/dtypes only. It never receives
raw dataset rows, and its plan is validated before any analytics tool runs.
"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

from .planner import AnalysisPlan


class OllamaProviderError(RuntimeError):
    """Ollama was unavailable or returned an invalid planning response."""


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["describe", "aggregate", "correlation", "count_rows", "clarify"]},
        "metric_column": {"type": ["string", "null"]},
        "group_by": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
        "aggregation": {"type": ["string", "null"], "enum": ["sum", "mean", "median", "min", "max", "count", "count_rows", None]},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "clarification": {"type": "string"},
    },
    "required": ["operation", "metric_column", "group_by", "aggregation", "limit", "clarification"],
    "additionalProperties": False,
}

_ALLOWED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count"}


def _dataframe(dataset: Any) -> pd.DataFrame:
    frame = dataset if isinstance(dataset, pd.DataFrame) else getattr(dataset, "dataframe", None)
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("The dataset is not prepared. Load and validate a dataset first.")
    if not frame.columns.is_unique:
        raise ValueError("The dataset has duplicate column labels; resolve the schema ambiguity first.")
    return frame


def _validate_plan(raw: Any, frame: pd.DataFrame) -> AnalysisPlan:
    if not isinstance(raw, dict):
        raise OllamaProviderError("Ollama plan must be a JSON object.")
    required = {"operation", "metric_column", "group_by", "aggregation", "limit", "clarification"}
    if set(raw) != required:
        raise OllamaProviderError("Ollama plan has missing or unexpected fields.")

    operation = raw["operation"]
    metric = raw["metric_column"]
    group_by = raw["group_by"]
    aggregation = raw["aggregation"]
    limit = raw["limit"]
    clarification = raw["clarification"]

    if operation == "clarify":
        message = clarification.strip() if isinstance(clarification, str) else ""
        raise ValueError(message or "Please clarify which metric, dimension or period you want to analyze.")
    if operation not in {"describe", "aggregate", "correlation", "count_rows"}:
        raise OllamaProviderError("Ollama requested an unsupported operation.")
    if not isinstance(group_by, list) or len(group_by) > 2 or any(not isinstance(c, str) for c in group_by):
        raise OllamaProviderError("Ollama returned invalid grouping columns.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise OllamaProviderError("Ollama returned an invalid result limit.")
    if not isinstance(clarification, str):
        raise OllamaProviderError("Ollama returned an invalid clarification field.")

    available = [str(c) for c in frame.columns]
    requested = list(group_by)
    if metric is not None:
        if not isinstance(metric, str):
            raise OllamaProviderError("Ollama returned an invalid metric column.")
        requested.append(metric)
    if any(column not in available for column in requested):
        unknown = sorted(set(requested) - set(available))
        raise ValueError("The plan references columns that do not exist: " + ", ".join(unknown) + ". Please clarify the column names.")

    if operation == "describe":
        if metric is not None or group_by or aggregation is not None:
            raise OllamaProviderError("A dataset summary must not include aggregation arguments.")
        return AnalysisPlan(operation="describe", limit=limit, reason="Ollama proposed a schema-validated dataset summary.")
    if operation == "count_rows":
        if metric is not None or aggregation not in {None, "count_rows"}:
            raise OllamaProviderError("A row-count plan contains incompatible arguments.")
        if len(group_by) > 1:
            raise ValueError("Grouped row count currently supports one grouping column.")
        return AnalysisPlan(operation="aggregate" if group_by else "count_rows", group_by=tuple(group_by), aggregation="count_rows", limit=limit, reason="Ollama proposed a bounded row-count analysis.")
    if operation == "correlation":
        if metric is not None or aggregation is not None or len(group_by) != 2 or group_by[0] == group_by[1]:
            raise ValueError("Correlation requires exactly two distinct numeric column names.")
        return AnalysisPlan(operation="correlation", group_by=tuple(group_by), limit=limit, reason="Ollama proposed an explicit two-column correlation.")
    if not isinstance(metric, str) or metric not in available:
        raise ValueError("Please identify one metric column from the dataset.")
    if aggregation not in _ALLOWED_AGGREGATIONS:
        raise OllamaProviderError("Ollama proposed an unsupported aggregation.")
    if len(group_by) > 1:
        raise ValueError("This MVP supports one grouping column per request.")
    if metric in group_by:
        raise ValueError("The metric and grouping column must be different.")
    return AnalysisPlan(
        operation="aggregate",
        metric_column=metric,
        group_by=tuple(group_by),
        aggregation=aggregation,
        limit=limit,
        reason="Ollama proposed an allow-listed, schema-validated aggregation.",
    )


def plan_question_with_ollama(
    question: str,
    dataset: Any,
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = 45.0,
) -> AnalysisPlan:
    """Ask Ollama for a JSON plan, validate it, and return only safe plan fields.

    Default endpoint is loopback. Override OLLAMA_BASE_URL only for an intentional
    trusted service endpoint; do not expose an unauthenticated Ollama server to the
    public internet.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please enter a question about the dataset.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 180:
        raise ValueError("timeout must be between 0 and 180 seconds.")
    frame = _dataframe(dataset)
    if frame.empty:
        raise ValueError("The dataset has no rows to analyze.")

    chosen_model = model or os.getenv("AI_DATAPILOT_OLLAMA_MODEL", "qwen3.5:4b")
    endpoint = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("OLLAMA_BASE_URL must be a valid HTTP(S) endpoint without embedded credentials.")
    if not isinstance(chosen_model, str) or not chosen_model.strip():
        raise ValueError("An Ollama model name is required.")

    # Only schema labels and dtypes are sent. No row values or profile examples.
    schema = [{"name": str(column), "dtype": str(frame[column].dtype)} for column in frame.columns]
    system = (
        "You are an analysis planner, not an answer generator. Return only a plan matching the supplied JSON schema. "
        "Never calculate or invent business results. Use only exact dataset column names. "
        "If the question is ambiguous, needs unavailable data, requests causal proof from observational data, "
        "or asks for unsupported behavior, choose operation='clarify' and explain what is missing. "
        "Supported operations: describe; aggregate with one metric and optional one group_by column; "
        "correlation with exactly two numeric columns; count_rows. Supported aggregation: sum, mean, median, min, max, count. "
        "Do not infer an external cause (for example inflation) from a sales table alone."
    )
    user = json.dumps({"question": question, "columns": schema}, ensure_ascii=False)
    body = {
        "model": chosen_model,
        "stream": False,
        "format": PLAN_SCHEMA,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    request = Request(
        endpoint + "/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=float(timeout)) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise OllamaProviderError("Could not reach Ollama. Check that it is running, the model is installed, and the endpoint is reachable.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OllamaProviderError("Ollama returned an invalid API response.") from exc

    try:
        content = response_body["message"]["content"]
        raw_plan = json.loads(content)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise OllamaProviderError("Ollama did not return a valid structured plan.") from exc
    return _validate_plan(raw_plan, frame)
