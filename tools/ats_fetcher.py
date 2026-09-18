# """
# tools/ats_fetcher.py
# Fetches jobs directly from company ATS platforms that expose free,
# public, no-key JSON endpoints (Greenhouse, Lever).

# These return the REAL apply link -- the same one a LinkedIn "Apply" button
# would eventually redirect to.
# """
# import requests
# from typing import List, Dict


# def fetch_greenhouse_jobs(company_slug: str, max_jobs: int = 15) -> List[Dict]:
#     url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
#     try:
#         resp = requests.get(url, timeout=10)
#         resp.raise_for_status()
#         jobs = resp.json().get("jobs", [])
#     except requests.RequestException:
#         return []

#     return [
#         {
#             "title": job.get("title", ""),
#             "company": company_slug,
#             "location": (job.get("location") or {}).get("name", ""),
#             "apply_url": job.get("absolute_url", ""),
#             "source": "greenhouse",
#             "posted_at": job.get("updated_at", ""),
#         }
#         for job in jobs[:max_jobs]
#     ]


# def fetch_lever_jobs(company_slug: str, max_jobs: int = 15) -> List[Dict]:
#     url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
#     try:
#         resp = requests.get(url, timeout=10)
#         resp.raise_for_status()
#         jobs = resp.json()
#     except requests.RequestException:
#         return []

#     return [
#         {
#             "title": job.get("text", ""),
#             "company": company_slug,
#             "location": (job.get("categories") or {}).get("location", ""),
#             "apply_url": job.get("applyUrl") or job.get("hostedUrl", ""),
#             "source": "lever",
#             "posted_at": job.get("createdAt", ""),
#         }
#         for job in jobs[:max_jobs]
#     ]


# def fetch_ats_jobs(company: Dict, max_jobs: int = 15) -> List[Dict]:
#     """
#     Dispatches to the right fetcher based on company['ats'].
#     Expects company = {"name": ..., "ats": "greenhouse"|"lever", "slug": ...}
#     """
#     ats = company.get("ats")
#     slug = company.get("slug", "")
#     if not slug:
#         return []

#     if ats == "greenhouse":
#         return fetch_greenhouse_jobs(slug, max_jobs)
#     if ats == "lever":
#         return fetch_lever_jobs(slug, max_jobs)
#     return []

"""
tools/ats_fetcher.py
Fetches jobs directly from company ATS platforms that expose free,
public, no-key JSON endpoints (Greenhouse, Lever).

These return the REAL apply link -- the same one a LinkedIn "Apply" button
would eventually redirect to.
"""
import requests
from typing import List, Dict


def fetch_greenhouse_jobs(company_slug: str, max_jobs: int = 15) -> List[Dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except requests.RequestException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"[ats_fetcher] Greenhouse request failed for '{company_slug}' "
              f"(status={status}): {e}")
        return []

    return [
        {
            "title": job.get("title", ""),
            "company": company_slug,
            "location": (job.get("location") or {}).get("name", ""),
            "apply_url": job.get("absolute_url", ""),
            "source": "greenhouse",
            "posted_at": job.get("updated_at", ""),
        }
        for job in jobs[:max_jobs]
    ]


def fetch_lever_jobs(company_slug: str, max_jobs: int = 15) -> List[Dict]:
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        jobs = resp.json()
    except requests.RequestException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"[ats_fetcher] Lever request failed for '{company_slug}' "
              f"(status={status}): {e}")
        return []

    return [
        {
            "title": job.get("text", ""),
            "company": company_slug,
            "location": (job.get("categories") or {}).get("location", ""),
            "apply_url": job.get("applyUrl") or job.get("hostedUrl", ""),
            "source": "lever",
            "posted_at": job.get("createdAt", ""),
        }
        for job in jobs[:max_jobs]
    ]


def fetch_ats_jobs(company: Dict, max_jobs: int = 15) -> List[Dict]:
    """
    Dispatches to the right fetcher based on company['ats'].
    Expects company = {"name": ..., "ats": "greenhouse"|"lever", "slug": ...}
    """
    ats = company.get("ats")
    slug = company.get("slug", "")
    if not slug:
        return []

    if ats == "greenhouse":
        return fetch_greenhouse_jobs(slug, max_jobs)
    if ats == "lever":
        return fetch_lever_jobs(slug, max_jobs)
    return []