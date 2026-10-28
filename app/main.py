"""Minimal local demo UI/API for the AI_DataPilot review.

Run from the repository root:
    python -m uvicorn app.main:app --reload

CSV text is parsed in memory; this demo does not persist uploaded data.
"""
from __future__ import annotations

import csv
from io import StringIO
from typing import Any

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.agent import ask

MAX_CSV_CHARS = 1_000_000
MAX_ROWS = 5_000
MAX_COLUMNS = 50


class AnalyzeRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=MAX_CSV_CHARS)
    question: str = Field(min_length=1, max_length=1000)
    planner: str = Field(default="rules", pattern="^(rules|ollama)$")


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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return r"""
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI_DataPilot | Business Analyst Copilot</title>
<style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#111c2e;--border:#2a3a50;--text:#e7eef8;--muted:#9fb0c6;--accent:#55d6be}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#0b1220,#111b2b 60%,#102b37);color:var(--text);font:15px/1.55 system-ui,Segoe UI,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:30px 18px 60px}.eyebrow{color:var(--accent);font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:12px}
h1{font-size:clamp(30px,4vw,44px);line-height:1.1;margin:10px 0}h2{font-size:18px;margin:0 0 12px}.sub{color:var(--muted);max-width:800px}.pill{display:inline-block;border:1px solid var(--border);border-radius:999px;padding:4px 10px;color:var(--muted);font-size:12px;margin:4px 4px 0 0}
.layout{display:grid;grid-template-columns:1.05fr .95fr;gap:16px;margin-top:24px}.panel{background:rgba(17,28,46,.92);border:1px solid var(--border);border-radius:16px;padding:18px;min-width:0}
textarea,input,select{width:100%;background:#0b1423;border:1px solid #34465f;border-radius:9px;color:var(--text);padding:11px;font:13px ui-monospace,SFMono-Regular,Consolas,monospace}
textarea{min-height:300px;resize:vertical}input{font:15px system-ui;margin:6px 0 10px}select{font:14px system-ui;margin:6px 0 10px}
label{display:block;font-weight:650;font-size:13px;margin:13px 0 4px}.muted{color:var(--muted);font-size:13px}
button{border:0;border-radius:9px;background:var(--accent);color:#07231f;font-weight:800;padding:12px 16px;cursor:pointer}button.secondary{background:#23364e;color:var(--text);border:1px solid #3b506b}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:14px}.chips{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}.chips button{font-size:12px;padding:7px 10px}.result{white-space:pre-wrap;overflow-wrap:anywhere;background:#0b1423;border:1px solid var(--border);border-radius:10px;padding:13px;max-height:440px;overflow:auto;font:12px/1.6 ui-monospace,monospace}
.status{font-weight:800;color:var(--accent)}.status.warn{color:#ffc979}.foot{margin-top:18px;color:var(--muted);font-size:12px}.full{grid-column:1/-1}
@media(max-width:820px){.layout{grid-template-columns:1fr}.full{grid-column:auto}textarea{min-height:230px}}
</style></head><body><main>
<div class="eyebrow">Batch 16 · Review baseline · v0.1</div>
<h1>AI_DataPilot</h1>
<p class="sub">An AI-driven business intelligence analyst copilot. Ask a question, inspect calculation evidence, and see what available data can—and cannot—justify. This assists the analyst; it does not replace business judgement.</p>
<span class="pill">Deterministic analytics</span><span class="pill">Evidence returned</span><span class="pill">Local Ollama optional</span><span class="pill">No dataset persistence</span>
<div class="layout">
<section class="panel"><h2>1 · Dataset</h2>
<p class="muted">The included sample is synthetic. Replace it with a small CSV by pasting your data below.</p>
<label for="csv">CSV content</label><textarea id="csv" spellcheck="false"></textarea>
<div class="actions"><button class="secondary" id="reset">Load sample dataset</button></div>
<label for="planner">Planning mode</label><select id="planner"><option value="rules">Rules baseline — works offline</option><option value="ollama">Local Qwen via Ollama — requires Ollama running</option></select>
<div class="foot">Limits: 1 MB CSV text, 5,000 rows, 50 columns. Data is processed in memory and not written to disk by this app.</div>
</section>
<section class="panel"><h2>2 · Ask the analyst copilot</h2>
<label for="question">Business question</label><input id="question" value="What is the average selling_price_per_kg by month?" maxlength="1000">
<div class="chips">
<button class="secondary" data-q="What is the average selling_price_per_kg by month?">Selling price trend</button>
<button class="secondary" data-q="What is the average purchase_cost_per_kg by month?">Purchase cost trend</button>
<button class="secondary" data-q="What is the average sales_revenue by product?">Revenue by product</button>
<button class="secondary" data-q="What is the correlation between purchase_cost_per_kg and selling_price_per_kg?">Cost/price correlation</button>
</div>
<div class="actions"><button id="run">Analyze question</button><span id="status" class="muted" aria-live="polite"></span></div>
<label>Answer</label><div id="answer" class="result">Run an analysis to see the answer and its evidence.</div>
</section>
<section class="panel full"><h2>3 · Inspect evidence and limitations</h2>
<p class="muted">The result includes operation parameters, records, assumptions and warnings. A correlation does not prove causation.</p>
<div id="evidence" class="result">No evidence yet.</div>
<div class="foot">For this review build, Ollama proposes a structured plan and deterministic analytics perform calculations. It cannot prove external causes such as inflation from internal sales data alone.</div>
</section></div></main>
<script>
const sample = `month,product,supplier,purchase_cost_per_kg,selling_price_per_kg,quantity_sold_kg,sales_revenue
2026-01,Regular Rice,Mill A,42,48,120,5760
2026-02,Regular Rice,Mill A,41,49,135,6615
2026-03,Regular Rice,Mill B,43,52,150,7800
2026-04,Regular Rice,Mill B,42,55,145,7975
2026-05,Regular Rice,Mill C,40,56,170,9520
2026-06,Regular Rice,Mill C,39,58,180,10440
2026-01,Premium Rice,Mill P,58,68,70,4760
2026-02,Premium Rice,Mill P,57,69,75,5175
2026-03,Premium Rice,Mill Q,59,72,80,5760
2026-04,Premium Rice,Mill Q,58,74,82,6068
2026-05,Premium Rice,Mill R,56,76,88,6688
2026-06,Premium Rice,Mill R,55,78,95,7410
`;
const csv=document.getElementById('csv'), question=document.getElementById('question'), planner=document.getElementById('planner');
const statusBox=document.getElementById('status'), answerBox=document.getElementById('answer'), evidenceBox=document.getElementById('evidence');
csv.value=sample;
document.getElementById('reset').addEventListener('click',()=>{csv.value=sample;});
document.querySelectorAll('[data-q]').forEach(btn=>btn.addEventListener('click',()=>{question.value=btn.dataset.q;}));
document.getElementById('run').addEventListener('click',async()=>{
 statusBox.textContent='Analyzing…';answerBox.textContent='Waiting for validated analytics results…';evidenceBox.textContent='Waiting for evidence…';
 try{
  const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({csv_text:csv.value,question:question.value,planner:planner.value})});
  const payload=await response.json();
  statusBox.textContent=payload.status||(response.ok?'completed':'error');statusBox.className='status'+(payload.status==='ok'?'':' warn');
  answerBox.textContent=[payload.answer||'',payload.clarification?'\n\nClarification: '+payload.clarification:'',payload.privacy_note?'\n\n'+payload.privacy_note:''].join('');
  evidenceBox.textContent=JSON.stringify({dataset:payload.dataset,plan:payload.plan,evidence:payload.evidence,warnings:payload.warnings},null,2);
 }catch(err){statusBox.textContent='request failed';statusBox.className='status warn';answerBox.textContent='The request failed. Verify the app is running and inspect the terminal.';evidenceBox.textContent=String(err);}
});
</script></body></html>
"""
