# Dispatch — Automated Job Search (CrewAI + FastAPI)

Upload your resume once. The app checks direct company career pages (Greenhouse/Lever)
and Adzuna (for TCS, Accenture, Amazon, Google, Microsoft, EY GDS, etc.), ranks the
results against your resume, and emails you the top 5 with real apply links.

## Project structure

```
job_search_crew/
├── main.py              # FastAPI backend (endpoints + serves the frontend)
├── pipeline.py           # Orchestrates the full run: resume -> fetch -> rank -> summarize -> email
├── config.py             # Env vars and constants
├── resume_cache.py       # Content-hash caching so the same resume is never re-analyzed
├── resume_parser.py      # CrewAI agent: PDF -> structured skills/experience profile
├── job_aggregator.py     # Routes each company to the right fetcher, merges + dedupes
├── matcher.py            # Deterministic keyword-overlap ranking (fast, no LLM cost)
├── summarizer.py         # CrewAI agent: writes short blurbs for the top 5 jobs
├── companies.json        # Target companies + which source to use for each
├── tools/
│   ├── ats_fetcher.py     # Free Greenhouse/Lever endpoints (direct apply links)
│   ├── adzuna_fetcher.py  # Adzuna search, filtered by company name
│   └── emailer.py         # Swappable email sender (Gmail SMTP today)
├── static/
│   └── index.html         # Frontend: upload form + results
├── requirements.txt
└── .env.example
```

## Setup (using uv)

1. **Install dependencies**
   ```bash
   uv sync
   ```
   This creates a `.venv` and installs everything from `pyproject.toml`
   (crewai, fastapi, uvicorn, requests, python-dotenv, pypdf, python-multipart).

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

- **Resume caching**: `resume_cache.py` hashes the uploaded file. Re-uploading the
  exact same resume skips the LLM call entirely and reuses the stored profile.
  Any change to the file content (even one line) triggers fresh analysis.

- **Two job sources**: `companies.json` marks each company with `"ats": "greenhouse"`,
  `"lever"`, or `"adzuna"`. `job_aggregator.py` routes accordingly — free direct
  endpoints where available, Adzuna as the fallback for companies without one
  (most large Indian/global enterprises).

- **Ranking before summarizing**: `matcher.py` does cheap keyword-overlap scoring
  across potentially hundreds of jobs first. Only the top 5 survivors go to the
  `summarizer.py` LLM call — this keeps cost and latency down.

- **Email is swappable**: `tools/emailer.py` defines an `EmailSender` interface.
  `GmailSMTPSender` works out of the box. If you deploy this for other people to
  use, swap in a `ResendSender`/`SendGridSender` implementation and change one
  line in `get_email_sender()` — nothing else in the app needs to change.

- **Anyone who uses the deployed app enters their own email** in the form — the
  Gmail credentials only authenticate the *sender*, not the recipient.

## Known limitations / next steps

- `companies.json` is a starting list — add more companies as you find them.
  Check a company's careers page URL: `boards.greenhouse.io/x` or
  `jobs.lever.co/x` means the free direct-fetch path works for them.
- Adzuna's `apply_url` redirects through Adzuna before reaching the source —
  Greenhouse/Lever links are the true direct apply links.
- The in-memory `JOBS` dict in `main.py` resets on server restart and only
  works for a single server process. Swap for Redis/a database before any
  multi-user deployment.
- Gmail SMTP caps around 500 emails/day and is best for personal use — see the
  emailer note above for scaling this up.
