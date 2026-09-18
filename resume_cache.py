"""
resume_cache.py
Content-based caching for resume analysis.

If the exact same resume (by file content, not filename) has been analyzed
before, we reuse the cached profile instead of calling the LLM again.
"""
import hashlib
import json
import os
from typing import Optional

from config import RESUME_CACHE_FILE


def get_file_hash(file_path: str) -> str:
    """Compute a SHA-256 fingerprint of a file's contents."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_cache() -> dict:
    if not os.path.exists(RESUME_CACHE_FILE):
        return {}
    with open(RESUME_CACHE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_cache(cache: dict) -> None:
    with open(RESUME_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached_profile(resume_hash: str) -> Optional[dict]:
    """Return a previously extracted resume profile, or None if not cached."""
    cache = _load_cache()
    return cache.get(resume_hash)


def save_profile(resume_hash: str, profile: dict) -> None:
    """Persist a newly extracted resume profile under its content hash."""
    cache = _load_cache()
    cache[resume_hash] = profile
    _save_cache(cache)
