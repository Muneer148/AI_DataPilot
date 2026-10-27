"""Deterministic analytics for AI_DataPilot.

Pandas and NumPy calculate; the LLM interprets. A DataFrame is the source of truth.
Prepared dataset objects are supported by their .dataframe contract without
importing or duplicating Member 1's implementation.
"""

from .aggregation import aggregate_dataset
from .contracts import AnalyticsError, AnalyticsResult
from .descriptive import describe_dataset
from .outliers import detect_outliers
from .relationships import correlate_dataset
from .trends import trend_dataset

__all__ = [
    "AnalyticsError", "AnalyticsResult", "aggregate_dataset", "correlate_dataset",
    "describe_dataset", "detect_outliers", "trend_dataset",
]
