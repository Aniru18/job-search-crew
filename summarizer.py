"""
summarizer.py
Takes the top-ranked jobs and writes a short, human-readable blurb for
each one, explaining why it matches the candidate's resume.
"""
import json
from typing import List, Dict
from crewai import Agent, Task, Crew, Process, LLM

from config import SUMMARIZER_MODEL
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

def _build_summarizer_agent() -> Agent:
    llm = LLM(model=SUMMARIZER_MODEL)
    return Agent(
        role="Job Summarizer",
        goal="Write short, honest summaries of why each job matches the candidate",
        backstory=(
            "You are a career coach who writes concise, useful job blurbs. "
            "You never invent details not present in the job data."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )


def _build_summary_task(agent: Agent, jobs: List[Dict], resume_profile: Dict) -> Task:
    jobs_json = json.dumps(jobs, indent=2)
    profile_json = json.dumps(resume_profile, indent=2)
    return Task(
        description=(
            "Given this candidate profile:\n"
            f"{profile_json}\n\n"
            "And these shortlisted jobs:\n"
            f"{jobs_json}\n\n"
            "For each job, write a 2-3 sentence summary covering: what the role involves, "
            "and why it fits this candidate's skills/experience level. "
            "Return ONLY a valid JSON list, same order as input, where each item is:\n"
            '{"title": ..., "company": ..., "apply_url": ..., "location": ..., "summary": "..."}'
        ),
        agent=agent,
        expected_output="A valid JSON list of job objects with a summary field added to each.",
    )


def summarize_jobs(jobs: List[Dict], resume_profile: Dict) -> List[Dict]:
    if not jobs:
        return []

    agent = _build_summarizer_agent()
    task = _build_summary_task(agent, jobs, resume_profile)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()

    raw = str(result).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1) if raw.startswith("json\n") else raw

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: attach a generic summary rather than failing the whole run
        return [
            {
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "apply_url": j.get("apply_url", ""),
                "location": j.get("location", ""),
                "summary": "This role matched your resume keywords.",
            }
            for j in jobs
        ]
