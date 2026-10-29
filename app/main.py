"""Local-first API and HTML entry point for the AI_DataPilot review UI.

CSV text and uploaded tabular files are processed in memory. Preparation is a
separate, explicit request so the UI can show a non-destructive preview first.
"""
from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.diagnostics import diagnose_price_cost
from src.agent import ask
from src.data import DataLoader, AnalysisReadyDataset, prepare_dataset, preview_dataframe

MAX_CSV_CHARS = 1_000_000
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 5_000
MAX_COLUMNS = 50
UPLOAD_LOADER = DataLoader(max_file_size_bytes=MAX_UPLOAD_BYTES)


class AnalyzeRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARS)
    question: str = Field(min_length=1, max_length=1000)
    planner: str = Field(default="rules", pattern="^(rules|ollama)$")
    prepare: bool = False


class PreviewRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARS)


class PriceDiagnosticRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARS)


class AppInputError(ValueError):
    pass


def _enforce_frame_limits(frame: pd.DataFrame) -> None:
    """Apply application limits independently of the lower-level file parser."""
    if not isinstance(frame, pd.DataFrame):
        raise AppInputError("The uploaded dataset could not be represented as a table.")
    if frame.empty:
        raise AppInputError("The dataset contains no data rows.")
    if len(frame) > MAX_ROWS:
        raise AppInputError(f"This demo is limited to {MAX_ROWS:,} data rows.")
    if len(frame.columns) == 0:
        raise AppInputError("The dataset contains no columns.")
    if len(frame.columns) > MAX_COLUMNS:
        raise AppInputError(f"This demo is limited to {MAX_COLUMNS} columns.")


def parse_csv_text(csv_text: str) -> pd.DataFrame:
    """Parse bounded CSV text without saving it to disk."""
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
    _enforce_frame_limits(frame)
    if not frame.columns.is_unique:
        raise AppInputError("Column names must be unique. Rename duplicate headers before analysis.")
    if any(not isinstance(column, str) or not column.strip() for column in frame.columns):
        raise AppInputError("Every column must have a non-empty header.")
    return frame


async def _load_upload(file: UploadFile) -> tuple[pd.DataFrame, str, str, int]:
    """Read a bounded upload into memory and parse it by its allowed extension."""
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or not Path(filename).suffix:
        raise AppInputError("Choose a file with a supported extension: .csv, .xlsx, .xls or .json.")
    try:
        payload = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise AppInputError(f"Uploaded file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB demo limit.")
    try:
        frame = UPLOAD_LOADER.load_bytes(filename, payload)
    except (TypeError, ValueError) as exc:
        raise AppInputError(str(exc)) from exc
    _enforce_frame_limits(frame)
    return frame, filename, Path(filename).suffix.lower().lstrip("."), len(payload)


def _sample_records(frame: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    """Return only a small JSON-safe sample for the user's explicit browser preview."""
    try:
        return json.loads(frame.head(limit).to_json(orient="records", date_format="iso"))
    except (TypeError, ValueError):
        # This fallback still avoids placing values into HTML strings.
        return [{"value": str(value) for value in row} for row in frame.head(limit).itertuples(index=False, name=None)]


def _preview_result(
    frame: pd.DataFrame,
    *,
    source_name: str,
    source_format: str,
    source_size_bytes: int | None,
) -> dict[str, Any]:
    preview = preview_dataframe(
        frame,
        source_name=source_name,
        source_format=source_format,
        source_size_bytes=source_size_bytes,
    )
    return {
        "status": "ready" if preview.ready else "needs_attention",
        "ready": preview.ready,
        "preview": preview.to_dict(),
        "source_sample": {
            "columns": frame.columns.astype(str).tolist(),
            "records": _sample_records(frame),
        },
        "cleaned_sample": {
            "columns": preview.cleaned_dataframe.columns.astype(str).tolist(),
            "records": _sample_records(preview.cleaned_dataframe),
        },
        "privacy_note": (
            "The preview sample is returned only to this client for inspection. "
            "The app does not save the dataset or send its rows to the planning model."
        ),
    }


def _analysis_response(
    frame: pd.DataFrame,
    question: str,
    *,
    planner: str,
    prepare: bool,
    source_name: str,
    source_format: str,
    source_size_bytes: int | None,
) -> dict[str, Any]:
    subject: pd.DataFrame | AnalysisReadyDataset = frame
    prepared: AnalysisReadyDataset | None = None
    if prepare:
        try:
            prepared = prepare_dataset(
                frame,
                source_name=source_name,
                source_format=source_format,
                source_size_bytes=source_size_bytes,
            )
        except (TypeError, ValueError) as exc:
            return {
                "status": "invalid_dataset",
                "answer": "Preparation failed validation. The dataset was not analyzed.",
                "clarification": str(exc),
                "plan": None,
                "evidence": None,
                "warnings": [],
                "dataset": {"rows": int(frame.shape[0]), "columns": [str(c) for c in frame.columns]},
                "preparation": None,
            }
        subject = prepared

    response = ask(subject, question, planner=planner)
    analyzed_frame = prepared.dataframe if prepared is not None else frame
    return {
        "status": response.status,
        "answer": response.answer,
        "plan": response.plan,
        "evidence": response.evidence,
        "clarification": response.clarification,
        "warnings": response.warnings or [],
        "dataset": {
            "rows": int(analyzed_frame.shape[0]),
            "columns": [str(c) for c in analyzed_frame.columns],
        },
        "preparation": prepared.to_dict() if prepared is not None else None,
        "privacy_note": (
            "Dataset processed in memory and not saved by this demo. Ollama planning receives the question and column names/types, not raw dataset rows."
            if planner == "ollama"
            else "Dataset processed in memory and not saved by this demo."
        ),
    }


def run_analysis(
    csv_text: str,
    question: str,
    planner: str = "rules",
    *,
    prepare: bool = False,
) -> dict[str, Any]:
    """Keep the existing CSV-text API usable while supporting approved preparation."""
    frame = parse_csv_text(csv_text)
    return _analysis_response(
        frame,
        question,
        planner=planner,
        prepare=prepare,
        source_name="pasted.csv",
        source_format="csv",
        source_size_bytes=len(csv_text.encode("utf-8")),
    )


app = FastAPI(
    title="AI_DataPilot — Business Analyst Copilot",
    version="0.2.0-review",
    description="Local review baseline: data preview/preparation, deterministic analytics and optional local Ollama planning.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "AI_DataPilot review baseline"}


@app.post("/api/preview")
def preview(payload: PreviewRequest) -> dict[str, Any]:
    try:
        frame = parse_csv_text(payload.csv_text)
        return _preview_result(
            frame,
            source_name="pasted.csv",
            source_format="csv",
            source_size_bytes=len(payload.csv_text.encode("utf-8")),
        )
    except AppInputError as exc:
        return {
            "status": "invalid_dataset",
            "ready": False,
            "answer": "The dataset could not be previewed.",
            "clarification": str(exc),
        }


@app.post("/api/preview-upload")
async def preview_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        frame, filename, source_format, size_bytes = await _load_upload(file)
        return _preview_result(
            frame,
            source_name=filename,
            source_format=source_format,
            source_size_bytes=size_bytes,
        )
    except AppInputError as exc:
        return {
            "status": "invalid_dataset",
            "ready": False,
            "answer": "The dataset could not be previewed.",
            "clarification": str(exc),
        }


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
    try:
        return run_analysis(payload.csv_text, payload.question, payload.planner, prepare=payload.prepare)
    except AppInputError as exc:
        return {"status": "invalid_dataset", "answer": "The dataset was not analyzed.", "clarification": str(exc)}


@app.post("/api/analyze-upload")
async def analyze_upload(
    file: UploadFile = File(...),
    question: str = Form(..., min_length=1, max_length=1000),
    planner: str = Form("rules", pattern="^(rules|ollama)$"),
    prepare: bool = Form(False),
) -> dict[str, Any]:
    try:
        frame, filename, source_format, size_bytes = await _load_upload(file)
        if not question.strip():
            return {"status": "needs_clarification", "answer": "Enter an analytical question first.", "clarification": "Question cannot be blank."}
        return _analysis_response(
            frame,
            question,
            planner=planner,
            prepare=prepare,
            source_name=filename,
            source_format=source_format,
            source_size_bytes=size_bytes,
        )
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


@app.post("/api/diagnose-pricing-upload")
async def diagnose_pricing_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        frame, _, _, _ = await _load_upload(file)
        return diagnose_price_cost(frame)
    except AppInputError as exc:
        return {
            "status": "needs_data",
            "summary": "The uploaded dataset could not be analyzed.",
            "missing_columns": [],
            "records": [],
            "product_findings": [],
            "limitations": [str(exc)],
        }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the separate UI file for maintainability and review."""
    return Path(__file__).with_name("ui.html").read_text(encoding="utf-8")
