import os
import sys
import json
import shutil
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure Quest root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.models import JobSpecification, CandidateDossier, ApprovalAction, ApprovalStatus
from core.pipeline import ScreeningPipeline
from core.storage import StorageManager
from core.exporters.ats_exporter import ATSExporter
from core.config import config

app = FastAPI(
    title="TalentOps AI OS Mini",
    description="Candidate Screener & Evidence Dossier Operating System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = ScreeningPipeline(data_dir=config.data_dir)
storage = StorageManager(data_dir=config.data_dir)

# Static files directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>TalentOps AI OS Mini</h1><p>UI loading...</p>"


@app.get("/api/jobs")
async def get_jobs():
    jobs = []
    job_dir = os.path.join(config.data_dir, "job_descriptions")
    if os.path.exists(job_dir):
        for fname in os.listdir(job_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(job_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        jobs.append(data)
                except Exception:
                    pass
    if not jobs:
        # Default senior backend engineer job
        jobs.append(JobSpecification().model_dump())
    return jobs


@app.get("/api/stats")
async def get_stats():
    dossiers = storage.list_dossiers()
    total = len(dossiers)
    if total == 0:
        return {
            "total_screened": 0,
            "avg_score": 0.0,
            "advance_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "injections_blocked": 0
        }
    
    avg_score = round(sum(d.get("overall_score", 0) for d in dossiers) / total, 1)
    advance_count = sum(1 for d in dossiers if d.get("recommendation") in ["Strong Advance", "Advance to Screen"])
    approved_count = sum(1 for d in dossiers if d.get("approval_status") == "Approved for Screen")
    rejected_count = sum(1 for d in dossiers if d.get("approval_status") == "Rejected")
    injections_blocked = sum(1 for d in dossiers if d.get("has_injection_risk"))

    return {
        "total_screened": total,
        "avg_score": avg_score,
        "advance_count": advance_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "injections_blocked": injections_blocked
    }


@app.get("/api/dossiers")
async def list_dossiers():
    return storage.list_dossiers()


@app.get("/api/dossiers/{dossier_id}")
async def get_dossier(dossier_id: str):
    dossier = storage.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return dossier


@app.post("/api/screen")
async def screen_candidate(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    job_id: str = Form("job-senior-backend"),
    candidate_name: Optional[str] = Form(None),
    anonymize_pii: bool = Form(False)
):
    # Find job spec
    job_spec = None
    job_dir = os.path.join(config.data_dir, "job_descriptions")
    if os.path.exists(job_dir):
        for fname in os.listdir(job_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(job_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("id") == job_id:
                            job_spec = JobSpecification(**data)
                            break
                except Exception:
                    pass

    if not job_spec:
        job_spec = JobSpecification(id=job_id)

    # Process either uploaded file or pasted text
    if file and file.filename:
        upload_dir = os.path.join(config.data_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        temp_path = os.path.join(upload_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            dossier = pipeline.process_candidate_file(
                file_path=temp_path,
                job_spec=job_spec,
                candidate_name=candidate_name,
                anonymize_pii=anonymize_pii
            )
            return dossier
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    elif raw_text and raw_text.strip():
        dossier = pipeline.process_candidate_text(
            raw_text=raw_text,
            file_name="pasted_resume.txt",
            job_spec=job_spec,
            candidate_name=candidate_name,
            anonymize_pii=anonymize_pii
        )
        return dossier
    else:
        raise HTTPException(status_code=400, detail="Either a resume file or raw_text must be provided.")


@app.post("/api/approve")
async def review_candidate(action_data: ApprovalAction):
    updated = storage.update_approval(
        dossier_id=action_data.dossier_id,
        action=action_data.action,
        recruiter_name=action_data.recruiter_name,
        notes=action_data.notes,
        overridden_score=action_data.overridden_score
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Dossier not found")
    return updated


@app.get("/api/export/{dossier_id}")
async def export_dossier(dossier_id: str, format: str = Query("greenhouse")):
    dossier = storage.get_dossier(dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found")

    if format.lower() == "markdown":
        md = ATSExporter.to_markdown_summary(dossier)
        return PlainTextResponse(md, media_type="text/markdown")
    elif format.lower() == "greenhouse":
        return ATSExporter.to_greenhouse_payload(dossier)
    else:
        return dossier.model_dump()


@app.get("/api/audit")
async def get_audit_trail(limit: int = 50):
    logs = []
    log_path = os.path.join(config.data_dir, "audit_log.jsonl")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line.strip()))
                    except Exception:
                        pass
    logs.reverse()
    return logs[:limit]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host=config.host, port=config.port, reload=config.debug)
