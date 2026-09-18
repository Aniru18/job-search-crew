"""
sent_jobs_cache.py
Tracks which jobs have already been emailed to each recipient, so the same
job isn't sent again on a later run.

Structure of the cache file:
{
  "recipient@example.com": {
    "<job_key>": "2026-08-20T14:03:00+00:00",   # ISO timestamp when sent
    ...
  },
  ...
}

Keyed per recipient email, since two different people using this app
shouldn't affect each other's "already sent" history.

A job counts as "already sent" only within SENT_JOB_EXPIRY_DAYS of when it
was last emailed -- after that window, it's treated as new again. This
keeps the cache file from growing forever and allows a genuinely
still-relevant posting to resurface as a reminder after enough time passes.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from urllib.parse import urlsplit, urlunsplit

from config import SENT_JOBS_CACHE_FILE, SENT_JOB_EXPIRY_DAYS


def get_job_key(job: Dict) -> str:
    """
    A stable identifier for a job posting. Prefers apply_url (most specific
    to one posting); falls back to title+company if apply_url is missing,
    matching the same fallback logic already used for in-run deduplication
    in job_aggregator.py.

    The query string is stripped from apply_url before use: Adzuna's
    redirect_url embeds per-request tracking params (e.g. "se", "v") that
    change on every API call even for the exact same ad, which would
    otherwise make the same job look "new" on every run. The underlying ad
    ID lives in the URL path, which stays stable.
    """
    apply_url = (job.get("apply_url") or "").strip()
    if apply_url:
        parts = urlsplit(apply_url)
        stable_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return stable_url
    title = (job.get("title") or "").lower().strip()
    company = (job.get("company") or "").lower().strip()
    return f"{title}|{company}"


def _load_cache() -> dict:
    if not os.path.exists(SENT_JOBS_CACHE_FILE):
        return {}
    with open(SENT_JOBS_CACHE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_cache(cache: dict) -> None:
    with open(SENT_JOBS_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _is_expired(sent_at_iso: str) -> bool:
    try:
        sent_at = datetime.fromisoformat(sent_at_iso)
    except (ValueError, TypeError):
        # Malformed/unrecognized timestamp -- treat as expired rather than
        # letting a bad entry permanently block a job.
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=SENT_JOB_EXPIRY_DAYS)
    return sent_at < cutoff


def filter_unsent_jobs(jobs: List[Dict], recipient_email: str) -> List[Dict]:
    """
    Returns only the jobs that either haven't been sent to this recipient
    before, or were sent long enough ago (past SENT_JOB_EXPIRY_DAYS) to be
    treated as new again.
    """
    cache = _load_cache()
    sent_for_recipient = cache.get(recipient_email, {})

    return [
        job for job in jobs
        if get_job_key(job) not in sent_for_recipient
        or _is_expired(sent_for_recipient[get_job_key(job)])
    ]


def mark_jobs_as_sent(jobs: List[Dict], recipient_email: str) -> None:
    """
    Records that these jobs were just emailed to this recipient, and prunes
    any expired entries for them while we're at it so the file doesn't grow
    unbounded.
    """
    cache = _load_cache()
    sent_for_recipient = cache.get(recipient_email, {})

    # Prune expired entries for this recipient before adding new ones.
    sent_for_recipient = {
        key: timestamp for key, timestamp in sent_for_recipient.items()
        if not _is_expired(timestamp)
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        sent_for_recipient[get_job_key(job)] = now_iso

    cache[recipient_email] = sent_for_recipient
    _save_cache(cache)