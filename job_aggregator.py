# """
# job_aggregator.py
# The "Job source router" + "Job pool" steps from the workflow diagram.
# Loops over companies.json, sends each company to the correct fetcher,
# and returns one merged, deduplicated list of job postings.
# """
# import json
# from typing import List, Dict

# from config import COMPANIES_FILE, MAX_JOBS_PER_COMPANY
# from tools.ats_fetcher import fetch_ats_jobs
# from tools.adzuna_fetcher import fetch_adzuna_jobs_broad, filter_jobs_for_company


# def load_companies() -> List[Dict]:
#     with open(COMPANIES_FILE, "r") as f:
#         return json.load(f)


# def _dedupe(jobs: List[Dict]) -> List[Dict]:
#     seen = set()
#     unique = []
#     for job in jobs:
#         key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
#         if key not in seen:
#             seen.add(key)
#             unique.append(job)
#     return unique


# def collect_all_jobs(keywords: List[str]) -> List[Dict]:
#     """
#     keywords: resume-derived keywords, used to narrow the Adzuna search
#     (Greenhouse/Lever companies don't need keywords -- we pull their full board).

#     Adzuna companies are handled specially: we run ONE broad Adzuna search
#     with the resume keywords, then filter that single result pool per
#     company locally. This avoids hitting Adzuna's rate-limited free-tier
#     quota once per company for what would otherwise be an identical search.
#     """
#     companies = load_companies()
#     all_jobs: List[Dict] = []

#     ats_companies = [c for c in companies if c.get("ats") in ("greenhouse", "lever")]
#     adzuna_companies = [c for c in companies if c.get("ats") not in ("greenhouse", "lever")]

#     for company in ats_companies:
#         try:
#             jobs = fetch_ats_jobs(company, max_jobs=MAX_JOBS_PER_COMPANY)
#         except Exception as e:
#             print(f"[job_aggregator] Skipping {company.get('name')} due to error: {e}")
#             jobs = []
#         all_jobs.extend(jobs)

#     if adzuna_companies:
#         try:
#             raw_adzuna_jobs = fetch_adzuna_jobs_broad(keywords)
#         except Exception as e:
#             print(f"[job_aggregator] Adzuna broad search failed, skipping all "
#                   f"Adzuna-sourced companies this run: {e}")
#             raw_adzuna_jobs = []

#         for company in adzuna_companies:
#             jobs = filter_jobs_for_company(raw_adzuna_jobs, company["name"], MAX_JOBS_PER_COMPANY)
#             all_jobs.extend(jobs)

#     return _dedupe(all_jobs)

"""
job_aggregator.py
The "Job source router" + "Job pool" steps from the workflow diagram.
Loops over companies.json, sends each company to the correct fetcher,
and returns one merged, deduplicated list of job postings.
"""
import json
from typing import List, Dict

from config import COMPANIES_FILE, MAX_JOBS_PER_COMPANY
from tools.ats_fetcher import fetch_ats_jobs
from tools.adzuna_fetcher import fetch_adzuna_jobs


def load_companies() -> List[Dict]:
    with open(COMPANIES_FILE, "r") as f:
        return json.load(f)


def _dedupe(jobs: List[Dict]) -> List[Dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def collect_all_jobs(keywords: List[str]) -> List[Dict]:
    """
    keywords: resume-derived keywords, used for the Adzuna search.

    companies.json now lists only Greenhouse/Lever companies -- each fetched
    directly from its own free public board endpoint. Adzuna is a separate,
    open discovery source: one broad keyword search, with results included
    as-is (no filtering against companies.json), since Adzuna already
    surfaces whichever employers are actually posting relevant roles rather
    than being restricted to a fixed target list.
    """
    companies = load_companies()
    all_jobs: List[Dict] = []

    for company in companies:
        try:
            jobs = fetch_ats_jobs(company, max_jobs=MAX_JOBS_PER_COMPANY)
        except Exception as e:
            print(f"[job_aggregator] Skipping {company.get('name')} due to error: {e}")
            jobs = []
        all_jobs.extend(jobs)

    try:
        adzuna_jobs = fetch_adzuna_jobs(keywords)
    except Exception as e:
        print(f"[job_aggregator] Adzuna search failed, skipping Adzuna results this run: {e}")
        adzuna_jobs = []
    all_jobs.extend(adzuna_jobs)

    return _dedupe(all_jobs)