# """
# matcher.py
# Scores and ranks fetched jobs against the resume profile.

# Uses deterministic keyword overlap rather than an LLM call -- this needs to
# run against potentially hundreds of jobs per request, so keeping it fast,
# free, and predictable matters more than nuance here. The LLM is used later,
# only on the already-narrowed top N, to write the summaries.
# """
# import re
# from typing import List, Dict

# from config import TOP_N_JOBS


# def _tokenize(text: str) -> set:
#     return set(re.findall(r"[a-zA-Z0-9+.#]+", text.lower()))


# def score_job(job: Dict, resume_keywords: List[str]) -> int:
#     haystack = f"{job.get('title', '')} {job.get('description', '')}"
#     job_tokens = _tokenize(haystack)
#     keyword_tokens = _tokenize(" ".join(resume_keywords))
#     return len(job_tokens & keyword_tokens)


# def rank_jobs(jobs: List[Dict], resume_profile: Dict, top_n: int = TOP_N_JOBS) -> List[Dict]:
#     keywords = resume_profile.get("keywords", []) + resume_profile.get("skills", [])
#     if not keywords:
#         # No signal to rank by -- return the first N as a safe fallback
#         return jobs[:top_n]

#     scored = [(score_job(job, keywords), job) for job in jobs]
#     scored.sort(key=lambda pair: pair[0], reverse=True)

#     # Drop zero-score jobs (no overlap at all) unless that would leave nothing
#     non_zero = [job for score, job in scored if score > 0]
#     ranked = non_zero if non_zero else [job for _, job in scored]

#     return ranked[:top_n]


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

# Title keywords that signal a role is too senior for a fresher/junior candidate.
# Matched as whole words against the job title so "Senior" doesn't also match
# something like "Seniority" (not realistic, but keeps the regex honest).
SENIOR_TITLE_KEYWORDS = [
    "senior", "sr", "lead", "principal", "staff", "architect",
    "manager", "head of", "director", "vp", "vice president",
]

# Roman-numeral / letter level suffixes handled separately since they need to
# anchor near the end of the title (e.g. "Engineer III") to avoid false hits.
SENIOR_LEVEL_SUFFIXES = ["ii", "iii", "iv", "v"]

# Title keywords that signal a role is explicitly aimed at freshers/entry level.
ENTRY_TITLE_KEYWORDS = [
    "fresher", "freshers", "graduate", "grad", "entry level", "entry-level",
    "trainee", "intern", "internship", "junior", "jr", "associate",
    "campus", "new grad",
]


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-zA-Z0-9+.#]+", text.lower()))


def _title_has_any(title: str, phrases: List[str]) -> bool:
    title_lower = title.lower()
    return any(re.search(rf"\b{re.escape(phrase)}\b", title_lower) for phrase in phrases)


def _title_has_senior_signal(title: str) -> bool:
    if _title_has_any(title, SENIOR_TITLE_KEYWORDS):
        return True
    # Level suffix like "Engineer III" -- only counts near the end of the title.
    tail = title.strip().split()[-1].lower() if title.strip() else ""
    return tail in SENIOR_LEVEL_SUFFIXES


def score_job(job: Dict, resume_keywords: List[str]) -> int:
    haystack = f"{job.get('title', '')} {job.get('description', '')}"
    job_tokens = _tokenize(haystack)
    keyword_tokens = _tokenize(" ".join(resume_keywords))
    return len(job_tokens & keyword_tokens)


def _filter_by_experience_level(jobs: List[Dict], experience_level: str) -> List[Dict]:
    """
    For fresher/junior candidates, drop obviously senior-titled roles.
    Never filters mid/senior candidates -- they can judge seniority fits themselves,
    and over-filtering there risks losing all results for a niche search.

    No fallback here: if every fetched job looks senior, the caller (rank_jobs)
    needs to know that plainly rather than silently receiving senior jobs back.
    """
    if experience_level not in ("fresher", "junior"):
        return jobs

    return [
        job for job in jobs
        if not _title_has_senior_signal(job.get("title", ""))
    ]


def rank_jobs(jobs: List[Dict], resume_profile: Dict, top_n: int = TOP_N_JOBS) -> Dict:
    """
    Returns {"jobs": [...], "note": str or None}.

    "note" is set when the result needs an explanation beyond a plain job list --
    specifically, when jobs were found overall but none matched the candidate's
    experience level, so the caller can tell the user that plainly instead of
    silently sending a shorter (or empty) list with no context.
    """
    keywords = resume_profile.get("keywords", []) + resume_profile.get("skills", [])
    experience_level = resume_profile.get("experience_level", "")
    is_entry_candidate = experience_level in ("fresher", "junior")

    level_filtered = _filter_by_experience_level(jobs, experience_level)

    if is_entry_candidate and jobs and not level_filtered:
        # We had jobs, but every single one looked senior-level for a
        # fresher/junior candidate -- say so instead of returning nothing
        # unexplained, or worse, sending senior roles anyway.
        return {
            "jobs": [],
            "note": (
                f"We found {len(jobs)} job(s) matching your skills today, but none "
                f"were at a {experience_level}-appropriate level -- they all looked "
                "like senior/lead roles. No digest was sent. Try again another day, "
                "or broaden your target roles if this keeps happening."
            ),
        }

    jobs = level_filtered

    if not keywords:
        # No signal to rank by -- return the first N as a safe fallback
        return {"jobs": jobs[:top_n], "note": None}

    scored = []
    for job in jobs:
        score = score_job(job, keywords)
        # Give entry-level-labeled roles a bump so they surface above generic
        # postings that merely share keywords but don't state a level.
        if is_entry_candidate and _title_has_any(job.get("title", ""), ENTRY_TITLE_KEYWORDS):
            score += 3
        scored.append((score, job))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    # Drop zero-score jobs (no overlap at all) unless that would leave nothing
    non_zero = [job for score, job in scored if score > 0]
    ranked = non_zero if non_zero else [job for _, job in scored]

    return {"jobs": ranked[:top_n], "note": None}