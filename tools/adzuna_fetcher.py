
# """
# tools/adzuna_fetcher.py
# Searches Adzuna (free tier) once for jobs matching the resume's keywords,
# returning a broad pool of results. job_aggregator.py then filters that
# single pool down per target company -- this avoids making one Adzuna API
# call per company (wasteful and quota-limited on the free tier) and avoids
# an impossible query (see note below).

# IMPORTANT ON QUERY SEMANTICS:
# Adzuna's `what` parameter is an AND search -- every word must appear in the
# job's title/description. Combining a company name with several keywords in
# one `what` string (e.g. "TCS Python Machine Learning") requires all of those
# words to appear together, which real postings almost never do (job text
# rarely repeats the employer's own name). We use `what_or` instead, which
# matches jobs containing ANY of the given words, and we do NOT put the
# company name in the query at all -- company matching happens afterward by
# looking at each result's own `company.display_name` field.
# """
# import requests
# from typing import List, Dict

# from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_BASE_URL


# def fetch_adzuna_jobs_broad(keywords: List[str], max_results: int = 100, max_pages: int = 3) -> List[Dict]:
#     """
#     Runs one (or a few, paginated) Adzuna search using resume keywords with
#     OR semantics, and returns the raw results list. Company-specific
#     filtering happens later via filter_jobs_for_company().
#     """
#     if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
#         raise RuntimeError("ADZUNA_APP_ID / ADZUNA_APP_KEY not set in environment.")

#     query = " ".join(keywords[:6]).strip()
#     if not query:
#         # No resume keywords to search with -- nothing meaningful to fetch.
#         return []

#     all_results: List[Dict] = []
#     for page in range(1, max_pages + 1):
#         url = f"{ADZUNA_BASE_URL}/{page}"
#         params = {
#             "app_id": ADZUNA_APP_ID,
#             "app_key": ADZUNA_APP_KEY,
#             "what_or": query,  # OR across keywords, not AND
#             "results_per_page": 50,
#             "content-type": "application/json",
#         }
#         try:
#             resp = requests.get(url, params=params, timeout=10)
#             resp.raise_for_status()
#             payload = resp.json()
#         except requests.RequestException as e:
#             status = getattr(getattr(e, "response", None), "status_code", None)
#             body = getattr(getattr(e, "response", None), "text", "")
#             print(f"[adzuna_fetcher] Broad search request failed on page {page} "
#                   f"(status={status}): {e} {body[:300]}")
#             break

#         page_results = payload.get("results", [])
#         if not page_results:
#             if page == 1:
#                 print(f"[adzuna_fetcher] Broad search query={query!r} returned 0 raw "
#                       f"results (API-reported total count: {payload.get('count')}).")
#             break

#         all_results.extend(page_results)
#         if len(all_results) >= max_results:
#             break

#     return all_results[:max_results]


# def filter_jobs_for_company(raw_jobs: List[Dict], company_name: str, max_jobs: int) -> List[Dict]:
#     """
#     Filters an already-fetched pool of Adzuna jobs down to ones posted by
#     `company_name`. Matches bidirectionally since Adzuna's listed employer
#     name is often shorter/different than our companies.json name
#     (e.g. "EY GDS" vs Adzuna's "EY").
#     """
#     company_lower = company_name.lower()
#     matched = []
#     for job in raw_jobs:
#         job_company = (job.get("company") or {}).get("display_name", "")
#         job_company_lower = job_company.lower()
#         if job_company_lower and (
#             company_lower in job_company_lower or job_company_lower in company_lower
#         ):
#             matched.append({
#                 "title": job.get("title", ""),
#                 "company": job_company,
#                 "location": (job.get("location") or {}).get("display_name", ""),
#                 "apply_url": job.get("redirect_url", ""),
#                 "source": "adzuna",
#                 "posted_at": job.get("created", ""),
#                 "description": job.get("description", ""),
#             })
#         if len(matched) >= max_jobs:
#             break

#     return matched


"""
tools/adzuna_fetcher.py
Searches Adzuna (free tier) once for jobs matching the resume's keywords
and returns them all, unfiltered by company. Adzuna is used as an open
discovery source here -- not tied to a fixed company list -- since
Greenhouse/Lever already cover the specific companies we track directly.

QUERY SEMANTICS NOTE:
Adzuna's `what` parameter is an AND search -- every word must appear in the
job's title/description. We use `what_or` instead, which matches jobs
containing ANY of the given keywords, since requiring all resume keywords
(or a specific company name) to appear together in one posting is almost
never satisfied by real job text.
"""
import requests
from typing import List, Dict

from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_BASE_URL


def _format_job(job: Dict) -> Dict:
    return {
        "title": job.get("title", ""),
        "company": (job.get("company") or {}).get("display_name", ""),
        "location": (job.get("location") or {}).get("display_name", ""),
        "apply_url": job.get("redirect_url", ""),
        "source": "adzuna",
        "posted_at": job.get("created", ""),
        "description": job.get("description", ""),
    }


def fetch_adzuna_jobs(keywords: List[str], max_results: int = 100, max_pages: int = 3) -> List[Dict]:
    """
    Runs an Adzuna search using resume keywords (OR semantics) and returns
    the results directly, from any company Adzuna surfaces -- no filtering
    against a fixed company list.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        raise RuntimeError("ADZUNA_APP_ID / ADZUNA_APP_KEY not set in environment.")

    query = " ".join(keywords[:6]).strip()
    if not query:
        # No resume keywords to search with -- nothing meaningful to fetch.
        return []

    all_results: List[Dict] = []
    for page in range(1, max_pages + 1):
        url = f"{ADZUNA_BASE_URL}/{page}"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what_or": query,  # OR across keywords, not AND
            "results_per_page": 50,
            "content-type": "application/json",
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            body = getattr(getattr(e, "response", None), "text", "")
            print(f"[adzuna_fetcher] Search request failed on page {page} "
                  f"(status={status}): {e} {body[:300]}")
            break

        page_results = payload.get("results", [])
        if not page_results:
            if page == 1:
                print(f"[adzuna_fetcher] Search query={query!r} returned 0 raw "
                      f"results (API-reported total count: {payload.get('count')}).")
            break

        all_results.extend(page_results)
        if len(all_results) >= max_results:
            break

    return [_format_job(job) for job in all_results[:max_results]]