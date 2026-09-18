"""
config.py
Central place for environment variables and constants used across the project.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Adzuna ---
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = "in"  # India
ADZUNA_BASE_URL = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search"

# --- Email (Gmail SMTP) ---
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# --- LLM (used by CrewAI agents) ---
# Using Groq's free tier, serving OpenAI's open-weight gpt-oss models.
# These are free/open models -- not the paid OpenAI API.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Larger model for the Resume Analyzer -- this runs rarely (cached per resume),
# so it's worth spending a bigger model on getting the extraction right.
RESUME_ANALYZER_MODEL = "groq/openai/gpt-oss-120b"

# Smaller/faster model for the Summarizer -- this runs on every search,
# and writing a short blurb doesn't need the bigger model.
SUMMARIZER_MODEL = "groq/openai/gpt-oss-20b"

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPANIES_FILE = os.path.join(BASE_DIR, "companies.json")
RESUME_CACHE_FILE = os.path.join(BASE_DIR, "resume_cache.json")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOADS_DIR, exist_ok=True)

# --- Pipeline settings ---
TOP_N_JOBS = 5
MAX_JOBS_PER_COMPANY = 15  # cap per company to keep runs fast and within free-tier limits
