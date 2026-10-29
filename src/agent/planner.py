"""Small, conservative natural-language planner for the review MVP.

This is a rule-based baseline, not an LLM or general natural-language system.
It only plans operations whose intent and columns can be grounded in the schema.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class AnalysisPlan:
    operation: str
    metric_column: str | None = None
    group_by: tuple[str, ...] = ()
    aggregation: str | None = None
    limit: int = 10
    reason: str = "Matched a supported deterministic question pattern."

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["group_by"] = list(self.group_by)
        return result


def _column_matches(question: str, columns: list[str]) -> list[str]:
    q = question.casefold()
    matches = []
    for col in columns:
        # Match full column labels, not fragments, to reduce false positives.
        label = str(col).casefold().strip()
        if label and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", q):
            matches.append(str(col))
    return matches


def plan_question(question: str, dataset: Any) -> AnalysisPlan:
    """Build a safe plan or raise ValueError with a clarification-oriented message."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Please enter a question about the dataset.")
    dataframe = dataset if isinstance(dataset, pd.DataFrame) else getattr(dataset, "dataframe", None)
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("The dataset is not prepared. Load and validate a dataset first.")
    if dataframe.empty:
        raise ValueError("The dataset has no rows to analyze.")
    columns = [str(c) for c in dataframe.columns]
    q = question.casefold().strip()

    # This MVP has no filter/date-range, forecasting, causal, or multi-step tools.
    # Refuse common scope markers instead of silently answering only part of a request.
    unsupported_scope = (
        r"\\b(?:forecast|predict|prediction|caus(?:e|es|ed|al)|causality|impact|effect)\\b",
        r"\\b(?:where|filtered\\s+by|greater\\s+than|less\\s+than|at\\s+least|at\\s+most|above|below|between|excluding|except)\\b",
        r"\\b(?:last|previous|past|during|since|before|after|monthly|weekly|daily|quarterly)\\b",
        r"\\b20\\d{2}\\b",
    )
    if any(re.search(pattern, q) for pattern in unsupported_scope):
        raise ValueError(
            "This request appears to need filtering, a time period, forecasting, or causal analysis that this MVP does not support. "
            "Please ask for one supported unfiltered summary, aggregation, row count, or two-column correlation."
        )

    matched = _column_matches(q, columns)
    summary_requested = any(token in q for token in ("describe", "summary", "summarize", "profile", "overview"))
    aggregation_requested = any(token in q for token in ("average", "mean", "avg", "median", "maximum", "highest", "largest", "max", "minimum", "lowest", "smallest", "min", "count", "how many", "sum", "total", "overall"))
    if summary_requested and aggregation_requested:
        raise ValueError("The request combines a dataset summary with a separate metric calculation. Please ask one question at a time.")
    if summary_requested:
        return AnalysisPlan(operation="describe", reason="Matched a dataset-summary request.")

    # Resolve a grouping dimension from an explicit 'by <column>' phrase.
    group_candidates = []
    for col in columns:
        label = col.casefold()
        if re.search(r"\bby\s+" + re.escape(label) + r"(?!\w)", q):
            group_candidates.append(col)
    if len(group_candidates) > 1:
        raise ValueError("The grouping dimension is ambiguous. Ask for one 'by <column>' dimension.")
    group_col = group_candidates[0] if group_candidates else None

    metric_candidates = [c for c in matched if c != group_col]
    # Avoid treating a group column as the metric when the user said 'count rows'.
    if any(token in q for token in ("count rows", "number of rows", "row count", "how many rows")):
        if group_col:
            return AnalysisPlan(operation="aggregate", group_by=(group_col,), aggregation="count_rows")
        return AnalysisPlan(operation="count_rows", aggregation="count_rows")
    if not metric_candidates and group_col is None:
        raise ValueError("I couldn't map the question to a dataset column. Include an exact column name or ask for a dataset summary.")
    if len(metric_candidates) > 1:
        # A two-column correlation is supported only when explicitly requested.
        if any(token in q for token in ("correlation", "correlate", "relationship")) and len(metric_candidates) == 2:
            return AnalysisPlan(operation="correlation", group_by=tuple(metric_candidates), reason="Explicit correlation request with two matched columns.")
        raise ValueError("More than one possible metric column matched. Name one metric column, or ask explicitly for correlation.")
    metric = metric_candidates[0] if metric_candidates else None

    if any(token in q for token in ("correlation", "correlate", "relationship")):
        if len(metric_candidates) != 2:
            raise ValueError("Correlation needs exactly two numeric column names. Please name both columns.")
        return AnalysisPlan(operation="correlation", group_by=tuple(metric_candidates), reason="Explicit correlation request.")
    if any(token in q for token in ("average", "mean", "avg")):
        op = "mean"
    elif any(token in q for token in ("median",)):
        op = "median"
    elif any(token in q for token in ("maximum", "highest", "largest", "max")):
        op = "max"
    elif any(token in q for token in ("minimum", "lowest", "smallest", "min")):
        op = "min"
    elif any(token in q for token in ("count", "how many")):
        op = "count"
    elif any(token in q for token in ("sum", "total", "overall")):
        op = "sum"
    else:
        raise ValueError("I understand the column name, but not the requested operation. Try sum, average, median, min/max, count, correlation, or summary.")

    if group_col:
        return AnalysisPlan(operation="aggregate", metric_column=metric, group_by=(group_col,), aggregation=op)
    return AnalysisPlan(operation="aggregate", metric_column=metric, aggregation=op, reason="Matched a supported single-column aggregation.")
