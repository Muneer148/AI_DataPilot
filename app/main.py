"""Minimal local demo UI/API for the AI_DataPilot review.

Run from the repository root:
    python -m uvicorn app.main:app --reload

CSV text is parsed in memory; this demo does not persist uploaded data.
"""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.agent import ask
from app.diagnostics import diagnose_price_cost

MAX_CSV_CHARS = 1_000_000
MAX_ROWS = 5_000
MAX_COLUMNS = 50


class AnalyzeRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARS)
    question: str = Field(min_length=1, max_length=1000)
    planner: str = Field(default="rules", pattern="^(rules|ollama)$")


class PriceDiagnosticRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARS)


class AppInputError(ValueError):
    pass


def parse_csv_text(csv_text: str) -> pd.DataFrame:
    """Parse bounded CSV input without saving it to disk."""
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise AppInputError("Paste a non-empty CSV dataset first.")
    if len(csv_text) > MAX_CSV_CHARS:
        raise AppInputError(f"CSV input exceeds the {MAX_CSV_CHARS:,}-character demo limit.")
    try:
        header = next(csv.reader(StringIO(csv_text)))
    except (csv.Error, StopIteration) as exc:
        raise AppInputError("The CSV must start with a valid header row.") from exc
    normalized_header = [name.strip() for name in header]
    if any(not name for name in normalized_header):
        raise AppInputError("Every column must have a non-empty header.")
    if len(set(normalized_header)) != len(normalized_header):
        raise AppInputError("Column names must be unique. Rename duplicate headers before analysis.")
    try:
        frame = pd.read_csv(StringIO(csv_text))
    except Exception as exc:
        raise AppInputError("The CSV could not be parsed. Check its header, delimiters and quoting.") from exc
    if frame.empty:
        raise AppInputError("The CSV contains no data rows.")
    if len(frame) > MAX_ROWS:
        raise AppInputError(f"This demo is limited to {MAX_ROWS:,} data rows.")
    if len(frame.columns) > MAX_COLUMNS:
        raise AppInputError(f"This demo is limited to {MAX_COLUMNS} columns.")
    if not frame.columns.is_unique:
        raise AppInputError("Column names must be unique. Rename duplicate headers before analysis.")
    if any(not isinstance(column, str) or not column.strip() for column in frame.columns):
        raise AppInputError("Every column must have a non-empty header.")
    return frame


def run_analysis(csv_text: str, question: str, planner: str = "rules") -> dict[str, Any]:
    frame = parse_csv_text(csv_text)
    response = ask(frame, question, planner=planner)
    return {
        "status": response.status,
        "answer": response.answer,
        "plan": response.plan,
        "evidence": response.evidence,
        "clarification": response.clarification,
        "warnings": response.warnings or [],
        "dataset": {"rows": int(frame.shape[0]), "columns": [str(c) for c in frame.columns]},
        "privacy_note": (
            "Dataset processed in memory and not saved by this demo. Ollama planning sends the question and column names/types only, not raw rows."
            if planner == "ollama"
            else "Dataset processed in memory and not saved by this demo."
        ),
    }


app = FastAPI(
    title="AI_DataPilot — Business Analyst Copilot",
    version="0.1.0-review",
    description="Local review baseline: deterministic analytics with optional local Ollama planning.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "AI_DataPilot review baseline"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
    try:
        return run_analysis(payload.csv_text, payload.question, payload.planner)
    except AppInputError as exc:
        return {"status": "invalid_dataset", "answer": "The dataset was not analyzed.", "clarification": str(exc)}


@app.post("/api/diagnose-pricing")
def diagnose_pricing(payload: PriceDiagnosticRequest) -> dict[str, Any]:
    try:
        frame = parse_csv_text(payload.csv_text)
        return diagnose_price_cost(frame)
    except AppInputError as exc:
        return {
            "status": "needs_data",
            "summary": "The CSV dataset could not be analyzed.",
            "missing_columns": [],
            "records": [],
            "product_findings": [],
            "limitations": [str(exc)],
        }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the local UI as a separate file for easier review and maintenance."""
    return Path(__file__).with_name("ui.html").read_text(encoding="utf-8")
