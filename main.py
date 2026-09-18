# """
# main.py
# FastAPI backend for the job search crew.

# Endpoints:
#   POST /run-search   -> upload resume + email, starts the pipeline in the background
#   GET  /status/{job_id} -> poll for progress/result
#   GET  /            -> serves the frontend
# """
# import os
# import re
# import uuid
# from typing import Dict

# from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
# from fastapi.responses import HTMLResponse
# from fastapi.middleware.cors import CORSMiddleware

# from config import UPLOADS_DIR
# from pipeline import run_job_search_pipeline

# app = FastAPI(title="CrewAI Job Search")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # tighten this before any public deployment
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # In-memory job store. Fine for a personal/single-user tool.
# # For multi-user deployment, replace with Redis or a database.
# JOBS: Dict[str, Dict] = {}

# EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# def _run_pipeline_background(job_id: str, file_path: str, email: str) -> None:
#     try:
#         result = run_job_search_pipeline(file_path, email)
#         JOBS[job_id] = {"status": "completed", **result}
#     except Exception as e:
#         JOBS[job_id] = {"status": "failed", "error": str(e)}


# @app.post("/run-search")
# async def run_search(
#     background_tasks: BackgroundTasks,
#     resume: UploadFile = File(...),
#     email: str = Form(...),
# ):
#     if not EMAIL_REGEX.match(email):
#         raise HTTPException(status_code=400, detail="Invalid email address.")

#     if not resume.filename.lower().endswith(".pdf"):
#         raise HTTPException(status_code=400, detail="Please upload a PDF resume.")

#     job_id = str(uuid.uuid4())
#     file_path = os.path.join(UPLOADS_DIR, f"{job_id}.pdf")

#     with open(file_path, "wb") as f:
#         f.write(await resume.read())

#     JOBS[job_id] = {"status": "running"}
#     background_tasks.add_task(_run_pipeline_background, job_id, file_path, email)

#     return {"job_id": job_id, "status": "running"}


# @app.get("/status/{job_id}")
# async def get_status(job_id: str):
#     job = JOBS.get(job_id)
#     if job is None:
#         raise HTTPException(status_code=404, detail="Job not found.")
#     return job


# @app.get("/", response_class=HTMLResponse)
# async def serve_frontend():
#     frontend_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
#     with open(frontend_path, "r") as f:
#         return f.read()


"""
main.py
FastAPI backend for the job search crew.

Endpoints:
  POST /run-search   -> upload resume + email, starts the pipeline in the background
  GET  /status/{job_id} -> poll for progress/result
  GET  /            -> serves the frontend
"""
import os
import re
import uuid
from typing import Dict

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from config import UPLOADS_DIR
from pipeline import run_job_search_pipeline

app = FastAPI(title="CrewAI Job Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before any public deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store. Fine for a personal/single-user tool.
# For multi-user deployment, replace with Redis or a database.
JOBS: Dict[str, Dict] = {}

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _run_pipeline_background(job_id: str, file_path: str, email: str) -> None:
    try:
        result = run_job_search_pipeline(file_path, email)
        JOBS[job_id] = {"status": "completed", **result}
    except Exception as e:
        JOBS[job_id] = {"status": "failed", "error": str(e)}
    finally:
        # The resume's extracted profile is already cached (by content hash)
        # in resume_cache.json, so the raw uploaded PDF has no further use --
        # remove it whether this run hit the cache, ran fresh analysis,
        # succeeded, or failed. Otherwise uploads/ grows by one file per
        # search, forever.
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as e:
            print(f"[main] Could not delete uploaded file {file_path}: {e}")


@app.post("/run-search")
async def run_search(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    email: str = Form(...),
):
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address.")

    if not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")

    job_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOADS_DIR, f"{job_id}.pdf")

    with open(file_path, "wb") as f:
        f.write(await resume.read())

    JOBS[job_id] = {"status": "running"}
    background_tasks.add_task(_run_pipeline_background, job_id, file_path, email)

    return {"job_id": job_id, "status": "running"}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(frontend_path, "r") as f:
        return f.read()