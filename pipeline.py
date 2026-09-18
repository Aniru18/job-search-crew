"""
pipeline.py
Orchestrates the full workflow end to end:
resume analysis (cached) -> fetch jobs -> rank -> summarize -> email.
"""
from typing import Dict

from resume_parser import get_resume_profile
from job_aggregator import collect_all_jobs
from matcher import rank_jobs
from summarizer import summarize_jobs
from tools.emailer import send_job_digest_email


def run_job_search_pipeline(resume_file_path: str, recipient_email: str) -> Dict:
    """
    Returns a dict with the resume profile, the final matched jobs, and status --
    used by both the API response and the email.
    """
    resume_profile = get_resume_profile(resume_file_path)

    keywords = resume_profile.get("keywords", [])
    all_jobs = collect_all_jobs(keywords)

    top_jobs = rank_jobs(all_jobs, resume_profile)
    summarized_jobs = summarize_jobs(top_jobs, resume_profile)

    if summarized_jobs:
        send_job_digest_email(recipient_email, summarized_jobs)

    return {
        "status": "completed",
        "resume_profile": resume_profile,
        "jobs_found_total": len(all_jobs),
        "jobs_sent": summarized_jobs,
    }
