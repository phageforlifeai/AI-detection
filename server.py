"""
FastAPI Web Server for SciGram — Pangram-Inspired AI Content &
Scientific Structure Analyzer.

Run with:
    python3 server.py
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from scigram.detector import get_detector
from scigram.parsers import extract_document_text
from scigram.report import render_markdown_report
from scigram.samples import PRESET_SAMPLES


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Pre-warm ONNX models at server startup so the first user scan is instant
    det = get_detector()
    det.ensure_loaded()
    yield


app = FastAPI(
    title="SciGram — AI Detection & Scientific Structure Analyzer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=250_000)
    title: Optional[str] = "Manuscript Draft"
    include_sentences: bool = True


class PassageRecheckRequest(BaseModel):
    original_text: str = Field(..., min_length=1, max_length=30_000)
    revised_text: str = Field(..., min_length=1, max_length=30_000)


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/health")
def health():
    det = get_detector()
    det.ensure_loaded()
    return {
        "status": "ok",
        "neural_active": det.neural_available,
        "load_error": det.load_error,
    }


@app.get("/api/samples")
def list_samples():
    return {"samples": PRESET_SAMPLES}


@app.post("/api/analyze")
def analyze_text(req: AnalyzeRequest):
    det = get_detector()
    res = det.analyze(req.text, include_sentences=req.include_sentences)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    res["title"] = req.title or "Manuscript Draft"
    return res


@app.post("/api/analyze-passage")
def analyze_passage_revision(req: PassageRecheckRequest):
    det = get_detector()
    orig_res = det.analyze(req.original_text, include_sentences=True)
    rev_res = det.analyze(req.revised_text, include_sentences=True)
    if "error" in rev_res:
        raise HTTPException(status_code=400, detail=rev_res["error"])

    orig_score = orig_res["overall_ai_pct"]
    rev_score = rev_res["overall_ai_pct"]
    return {
        "original_ai_pct": orig_score,
        "revised_ai_pct": rev_score,
        "delta_pct": round(rev_score - orig_score, 1),
        "revised": rev_res,
    }


@app.post("/api/upload")
async def upload_manuscript(
    file: UploadFile = File(...),
    strip_references: bool = Form(True),
):
    filename = file.filename or "uploaded_manuscript.txt"
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ".txt"
    allowed = {".txt", ".md", ".tex", ".latex", ".docx", ".pdf"}
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload .txt, .md, .tex, .docx, or .pdf.",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 15 MB limit.")

    try:
        extracted_text, meta = extract_document_text(
            filename, raw_bytes, strip_references=strip_references
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse {filename}: {exc}")

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No readable text found in uploaded document.")

    det = get_detector()
    res = det.analyze(extracted_text, include_sentences=True)
    res["title"] = filename
    res["extracted_text"] = extracted_text
    res["upload_meta"] = meta
    return res


@app.post("/api/export-report", response_class=PlainTextResponse)
def export_report(req: AnalyzeRequest):
    det = get_detector()
    res = det.analyze(req.text, include_sentences=False)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    md = render_markdown_report(res, title=req.title or "Manuscript Scan")
    return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
