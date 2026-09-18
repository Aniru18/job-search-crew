# Dispatch — Automated Job Search (CrewAI + FastAPI)

## The problem

Job hunting today means the same repetitive ritual, multiplied across a
dozen tabs: open each company's careers page, scroll past roles that are
clearly two levels too senior, copy a job title into Naukri or LinkedIn,
skim a description written for an algorithm rather than a human, and try
to remember — was this one already open in another tab yesterday? A
fresher applying to Indian IT majors and startups alike faces a specific,
underserved version of this problem: most job aggregators rank purely by
keyword overlap, so a "Senior Backend Engineer" and an "SDE-1, New Grad"
role can end up sitting side by side just because both mention Python and
AWS. The result is hours spent filtering out roles that were never a real
match in the first place, and no memory of what's already been seen.

## What this project does about it

Dispatch turns that whole loop into a single upload. It pulls postings
directly from company career boards where a free endpoint exists,
searches the broader market for anything else matching the resume,
filters out roles that don't actually fit the candidate's experience
level rather than just their keywords, remembers what's already been sent
so the same job never shows up twice, and emails a short, ranked shortlist
with real apply links — on a schedule, with zero manual searching.

A few of the design decisions worth noting:

- **LLM cost is spent only where it earns its keep.** Ranking hundreds of
  fetched jobs is done with deterministic keyword scoring (`matcher.py`),
  not an LLM call — it needs to run on every job, every time, so keeping
  it fast and free matters more than nuance there. The LLM is reserved
  for the two places it genuinely adds value: turning a messy resume PDF
  into a structured profile once (and caching that result, so the same
  resume never triggers a second LLM call), and writing short human
  summaries for only the five jobs that actually made the final cut.
- **Experience level is a first-class ranking signal, not an afterthought.**
  A fresher's resume shouldn't surface the same "Senior" and "Lead" roles
  a five-year candidate would get. The matcher actively filters those out
  for entry-level candidates — and if a search genuinely turns up nothing
  at the right level, it says so plainly instead of quietly sending
  mismatched roles just to fill the digest.
- **Built to run entirely on free tiers.** Groq's open-weight models,
  Adzuna's free search API, free Greenhouse/Lever public endpoints, and
  Gmail SMTP — no paid infrastructure required to run this end to end.

## Project structure

```
job_search_crew/
├── main.py               # FastAPI backend (endpoints + serves the frontend)
├── pipeline.py            # Orchestrates the full run: resume -> fetch -> dedupe -> rank -> summarize -> email
├── config.py              # Env vars and constants
├── resume_cache.py        # Content-hash caching so the same resume is never re-analyzed
├── resume_parser.py       # CrewAI agent: PDF -> structured skills/experience profile
├── sent_jobs_cache.py     # Tracks jobs already emailed to each recipient, with expiry
├── job_aggregator.py      # Fetches Greenhouse/Lever boards + one broad Adzuna search, merges + dedupes
├── matcher.py             # Keyword-overlap ranking + experience-level filtering (fast, no LLM cost)
├── summarizer.py          # CrewAI agent: writes short blurbs for the top 5 jobs
├── companies.json         # Companies with a free direct Greenhouse/Lever board
├── tools/
│   ├── ats_fetcher.py      # Free Greenhouse/Lever endpoints (direct apply links)
│   ├── adzuna_fetcher.py   # One broad Adzuna search across the whole market, not tied to companies.json
│   └── emailer.py          # Swappable email sender (Gmail SMTP today)
├── static/
│   └── index.html          # Frontend: upload form + results
├── sent_jobs_cache.json   # Created automatically -- per-recipient history of emailed jobs
├── resume_cache.json      # Created automatically -- cached resume profiles by content hash
├── pyproject.toml
└── .env.example
```

## Setup (using uv)

1. **Install dependencies**
   ```bash
   uv sync
   ```
   This creates a `.venv` and installs everything from `pyproject.toml`
   (crewai, fastapi, uvicorn, requests, python-dotenv, pypdf, python-multipart).
   `crewai` must be `>=1.15.5` -- earlier versions hit a known bug where a
   caching marker leaks into requests sent through non-Anthropic providers
   like Groq, causing a `cache_breakpoint` error from the API.

2. **Configure credentials**
   ```bash
   cp .env.example .env
   ```
   Fill in:
   - `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` — from developer.adzuna.com/signup (free)
   - `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` — a 16-char App Password from
     myaccount.google.com/apppasswords (requires 2-Step Verification on)
   - `GROQ_API_KEY` — from console.groq.com/keys (free). Powers both CrewAI
     agents using OpenAI's open-weight gpt-oss models served by Groq.

3. **Run the server**
   ```bash
   uv run uvicorn main:app --reload
   ```

4. Open **http://localhost:8000** — upload a resume PDF, enter an email, submit.

   API docs (auto-generated) are at **http://localhost:8000/docs**.

## How the pieces fit together

- **Resume caching**: `resume_cache.py` hashes the uploaded file's raw bytes.
  Re-uploading the exact same resume skips the LLM call entirely and reuses
  the stored profile. Any change to the file content (even one line)
  triggers fresh analysis. The uploaded PDF itself is deleted from
  `uploads/` right after each run (`main.py`), success or failure, cache hit
  or not — only the extracted profile is kept, in `resume_cache.json`.

- **Two job sources, used differently**:
  - `companies.json` lists companies with a free, verified Greenhouse or
    Lever board. `job_aggregator.py` fetches each one directly, by slug —
    this is the only place a wrong slug would show up as a 404 in the logs.
  - Adzuna is a separate, open discovery source, not tied to
    `companies.json` at all. `tools/adzuna_fetcher.py` runs **one** broad
    search using the resume's own keywords (OR semantics, via Adzuna's
    `what_or` parameter) and returns whatever employers Adzuna surfaces —
    it does not filter by, or require, a specific company name. This
    avoids the two problems of the original per-company approach: dozens
    of near-identical API calls burning through Adzuna's free-tier quota,
    and queries that required a job's text to literally contain the
    company's own name (Adzuna's `what` parameter is an AND search, which
    made most company + keyword combinations impossible to match).

- **Experience-level-aware ranking**: `resume_parser.py`'s LLM call also
  extracts an `experience_level` (`fresher`, `junior`, `mid`, `senior`)
  from the resume. `matcher.py` uses it: for fresher/junior candidates, it
  drops jobs whose title signals a senior role (Senior, Lead, Principal,
  Manager, Director, "Engineer III", etc.) and boosts titles that
  explicitly say Fresher/Graduate/Trainee/Entry Level/Junior/Associate. If
  every fetched job turns out to be senior-level for a fresher/junior
  candidate, no digest is sent — the pipeline returns a clear note instead
  of silently sending mismatched roles or a bare "0 jobs" with no
  explanation. Mid/senior candidates aren't filtered at all.

- **No repeat jobs**: `sent_jobs_cache.py` records every job emailed to
  each recipient (keyed by a stable identifier — normally the job's apply
  URL with tracking/session query parameters stripped, since those rotate
  per API call even for the same posting; title+company as a fallback
  when no URL exists). Before ranking, already-sent jobs are filtered out
  so a repeat can't take a slot that a genuinely new match should get.
  Entries expire after `SENT_JOB_EXPIRY_DAYS` (30 by default, in
  `config.py`) — after that window, a still-open posting can resurface as
  a reminder rather than being hidden forever, and the cache file doesn't
  grow without bound. History is kept per recipient email, so different
  people using the same deployment don't affect each other's results.

- **Ranking before summarizing**: `matcher.py` does cheap keyword-overlap
  scoring (after the experience-level filter above) across potentially
  hundreds of jobs first. Only the top 5 survivors go to the
  `summarizer.py` LLM call — this keeps cost and latency down.

- **Email is swappable**: `tools/emailer.py` defines an `EmailSender`
  interface. `GmailSMTPSender` works out of the box. If you deploy this
  for other people to use, swap in a `ResendSender`/`SendGridSender`
  implementation and change one line in `get_email_sender()` — nothing
  else in the app needs to change.

- **Anyone who uses the deployed app enters their own email** in the form
  — the Gmail credentials only authenticate the *sender*, not the
  recipient.

## Known limitations / next steps

- `companies.json` should only ever contain companies with a *verified*
  Greenhouse or Lever slug — don't guess. Check the company's real careers
  page URL (it'll show `job-boards.greenhouse.io/<slug>` or
  `boards.greenhouse.io/<slug>` for Greenhouse, `jobs.lever.co/<slug>` for
  Lever), then confirm the slug works by opening
  `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs` (or the
  equivalent Lever URL) directly in a browser before adding it. A wrong
  guess just produces a harmless 404 in the logs (`tools/ats_fetcher.py`
  now prints these clearly), but it's dead weight in the config either
  way. Companies without a confirmed board are better left to Adzuna's
  broad search than given a guessed, non-working slug.
- Adzuna's `apply_url` redirects through Adzuna before reaching the
  source — Greenhouse/Lever links are the true direct apply links.
- Large Indian IT services firms and many startups often post primarily
  through their own portals or aggregators other than Adzuna, so they may
  legitimately return few or no results from the broad Adzuna search on a
  given day — that's expected, not a bug.
- The in-memory `JOBS` dict in `main.py` resets on server restart and only
  works for a single server process. Swap for Redis/a database before any
  multi-user deployment.
- Gmail SMTP caps around 500 emails/day and is best for personal use — see
  the emailer note above for scaling this up.
- Adzuna's free tier has a daily call quota; the broad-search design keeps
  usage to a small, fixed number of calls per run regardless of how many
  companies or keywords are involved.