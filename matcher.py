"""
matcher.py
Scores and ranks fetched jobs against the resume profile.

Uses deterministic keyword overlap rather than an LLM call -- this needs to
run against potentially hundreds of jobs per request, so keeping it fast,
free, and predictable matters more than nuance here. The LLM is used later,
only on the already-narrowed top N, to write the summaries.
"""
import re
from typing import List, Dict

from config import TOP_N_JOBS


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-zA-Z0-9+.#]+", text.lower()))


def score_job(job: Dict, resume_keywords: List[str]) -> int:
    haystack = f"{job.get('title', '')} {job.get('description', '')}"
    job_tokens = _tokenize(haystack)
    keyword_tokens = _tokenize(" ".join(resume_keywords))
    return len(job_tokens & keyword_tokens)


def rank_jobs(jobs: List[Dict], resume_profile: Dict, top_n: int = TOP_N_JOBS) -> List[Dict]:
    keywords = resume_profile.get("keywords", []) + resume_profile.get("skills", [])
    if not keywords:
        # No signal to rank by -- return the first N as a safe fallback
        return jobs[:top_n]

    scored = [(score_job(job, keywords), job) for job in jobs]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    # Drop zero-score jobs (no overlap at all) unless that would leave nothing
    non_zero = [job for score, job in scored if score > 0]
    ranked = non_zero if non_zero else [job for _, job in scored]

    return ranked[:top_n]
