"""
resume_parser.py
Extracts raw text from an uploaded resume PDF, then uses a CrewAI agent to
turn it into a structured profile (skills, experience level, target roles).

Caching (resume_cache.py) ensures this LLM call only happens once per unique
resume file -- re-uploading the same file reuses the stored result instantly.
"""
import json
from pypdf import PdfReader
from crewai import Agent, Task, Crew, Process, LLM

from resume_cache import get_file_hash, get_cached_profile, save_profile
from config import RESUME_ANALYZER_MODEL
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _build_resume_analyzer_agent() -> Agent:
    llm = LLM(model=RESUME_ANALYZER_MODEL)
    return Agent(
        role="Resume Analyzer",
        goal="Extract a structured profile of skills, experience level, and target job roles from a resume",
        backstory=(
            "You are an expert technical recruiter who has read thousands of resumes. "
            "You are precise, and you never invent information that isn't in the resume."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _build_analysis_task(agent: Agent, resume_text: str) -> Task:
    return Task(
        description=(
            "Analyze the following resume text and extract a structured profile.\n\n"
            f"RESUME TEXT:\n{resume_text}\n\n"
            "Return ONLY a valid JSON object (no markdown, no commentary) with these keys:\n"
            "- \"skills\": list of strings (technical skills, tools, frameworks)\n"
            "- \"experience_level\": one of \"fresher\", \"junior\", \"mid\", \"senior\"\n"
            "- \"target_roles\": list of 3-6 job title strings this candidate should search for\n"
            "- \"keywords\": list of 8-15 strings to use as job-search keywords, ordered by relevance\n"
        ),
        agent=agent,
        expected_output="A single valid JSON object with keys skills, experience_level, target_roles, keywords.",
    )


def _run_resume_analysis(resume_text: str) -> dict:
    agent = _build_resume_analyzer_agent()
    task = _build_analysis_task(agent, resume_text)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()

    raw = str(result).strip()
    # Strip accidental markdown code fences if the model adds them
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1) if raw.startswith("json\n") else raw

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: return a minimal safe structure rather than crashing the pipeline
        return {
            "skills": [],
            "experience_level": "fresher",
            "target_roles": [],
            "keywords": [],
            "parse_error": True,
            "raw_output": raw,
        }


def get_resume_profile(file_path: str) -> dict:
    """
    Main entry point. Returns a structured resume profile.
    Uses the cache if this exact resume has been analyzed before.
    """
    resume_hash = get_file_hash(file_path)
    cached = get_cached_profile(resume_hash)
    if cached is not None:
        cached["_source"] = "cache"
        return cached

    resume_text = extract_text_from_pdf(file_path)
    profile = _run_resume_analysis(resume_text)
    profile["_source"] = "fresh_analysis"
    save_profile(resume_hash, profile)
    return profile
