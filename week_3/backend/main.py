import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from enums.models import Models
from prompt_model import prompt_model

load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "/data/jobs.db"))

SYSTEM_PROMPT = """\
You are a skill gap analyzer and resume assistant specialised in the Malaysian tech job market.
Your ONLY scope is helping users with their CV/resume, skill gaps, and tech job applications.

Rules:
- Always reply in **Markdown**.
- Use bullet lists (`- item`) with each item on its own line — never write list items inline separated by dashes.
- Use **bold** for section headings inside your reply.
- Keep answers concise and practical.
- When identifying skill gaps or listing items, produce a proper bullet list, e.g.:
  - Python
  - Docker
  - Kubernetes
- When asked to summarise a resume, structure the reply with sections: Summary, Experience, Education, Skills.
- If the attached document does not look like a CV or resume (e.g. it is an invoice, article, contract, \
or any non-career document), respond with exactly: \
"The attached document doesn't appear to be a CV or resume. \
I'm a skill gap analyzer and can only work with career documents. Please attach your resume instead."
- Do not answer questions unrelated to careers, resumes, or the tech job market. \
For off-topic questions respond: "That's outside my scope. I'm here to help with CVs, skill gaps, \
and tech job applications in Malaysia."
"""

# Phrases that indicate the user wants CV-specific analysis
_CV_ANALYSIS_PHRASES = (
    "skill gap", "skill gaps", "skills gap",
    "summarize", "summarise", "summarize my", "summarise my",
    "summary of my", "analyze my", "analyse my",
    "review my resume", "review my cv",
    "my resume", "my cv",
    "find gap", "identify gap", "missing skills",
)

def _is_cv_analysis_request(message: str) -> bool:
    lower = message.lower()
    return any(phrase in lower for phrase in _CV_ANALYSIS_PHRASES)

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", Models.LOCAL_MODELS.LLAMA3_1_LATEST)

app = FastAPI(title="Resume Helper Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    pdf_text: str = ""
    model: str = DEFAULT_MODEL


@app.post("/chat")
async def chat(req: ChatRequest):
    # Guard: CV analysis requested but no PDF attached
    if not req.pdf_text.strip() and _is_cv_analysis_request(req.message):
        return {
            "reply": (
                "I'd love to help, but I need your CV first.\n\n"
                "Please attach your resume as a PDF using the **paperclip** icon, "
                "then send your message again."
            ),
            "model": req.model,
        }

    parts = [SYSTEM_PROMPT]
    if req.pdf_text.strip():
        pdf_snippet = req.pdf_text[:8000]
        parts.append(f"\nThe user has provided their resume:\n<resume>\n{pdf_snippet}\n</resume>")
    parts.append(f"\nUser: {req.message}")
    full_prompt = "\n".join(parts)

    try:
        reply = prompt_model(req.model, full_prompt)
        return {"reply": reply, "model": req.model}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


# ── DB stats & search ─────────────────────────────────────────────────────────

@app.get("/api/stats")
async def get_stats():
    if not DB_PATH.exists():
        return JSONResponse({"error": "Database not found"}, status_code=404)

    conn = get_db()
    rows = conn.execute("SELECT job_title FROM jobs").fetchall()
    skill_rows = conn.execute(
        "SELECT tech_stack FROM jobs WHERE tech_stack IS NOT NULL AND tech_stack NOT IN ('', 'N/A')"
    ).fetchall()
    conn.close()

    locations: dict[str, int] = {}
    roles: dict[str, int] = {}

    for row in rows:
        title: str = row["job_title"]

        if " - Jobstreet" in title and " in " in title:
            loc_raw = title.split(" in ", 1)[1].split(" - Jobstreet")[0]
            parts = [p.strip() for p in loc_raw.split(",")]
            state = parts[-1] if len(parts) > 1 else parts[0]
            state = state.replace(" City Centre", "").strip()
            locations[state] = locations.get(state, 0) + 1

        role_part = title.split(" Job in ")[0].strip() if " Job in " in title else title
        rl = role_part.lower()
        if "data scientist" in rl:
            cat = "Data Scientist"
        elif "data engineer" in rl:
            cat = "Data Engineer"
        elif "data analyst" in rl or "data analysis" in rl:
            cat = "Data Analyst"
        elif "machine learning" in rl or "ml engineer" in rl:
            cat = "ML Engineer"
        elif "ai engineer" in rl or "ai application" in rl or "ai solution" in rl or "applied ai" in rl:
            cat = "AI Engineer"
        elif "software engineer" in rl or "software developer" in rl:
            cat = "Software Engineer"
        elif "automation engineer" in rl:
            cat = "Automation Engineer"
        elif "algorithm" in rl:
            cat = "Algorithm Engineer"
        elif "analyst" in rl or "programmer" in rl:
            cat = "Analyst / Programmer"
        elif "developer" in rl:
            cat = "Developer"
        else:
            cat = "Other"
        roles[cat] = roles.get(cat, 0) + 1

    # Top tech skills — count across all tagged jobs
    skill_counts: dict[str, int] = {}
    for row in skill_rows:
        for raw in row["tech_stack"].split(","):
            skill = raw.strip()
            if skill:
                skill_counts[skill.lower().title()] = skill_counts.get(skill.lower().title(), 0) + 1

    top_skills = dict(
        sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:15]
    )

    return {"locations": locations, "roles": roles, "top_skills": top_skills}


_FIELD_MAP = {
    "title":       "job_title LIKE ?",
    "company":     "company LIKE ?",
    "description": "description LIKE ?",
    "tech_stack":  "tech_stack LIKE ?",
}

@app.get("/api/jobs/search")
async def search_jobs(q: str = "", field: str = "all"):
    if not DB_PATH.exists():
        return JSONResponse({"error": "Database not found"}, status_code=404)

    conn = get_db()
    if q.strip():
        pattern = f"%{q}%"
        if field in _FIELD_MAP:
            clause = _FIELD_MAP[field]
            rows = conn.execute(
                f"SELECT source_id, job_title, company, tech_stack FROM jobs WHERE {clause} LIMIT 100",
                (pattern,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT source_id, job_title, company, tech_stack FROM jobs "
                "WHERE job_title LIKE ? OR company LIKE ? OR description LIKE ? OR tech_stack LIKE ? LIMIT 100",
                (pattern, pattern, pattern, pattern),
            ).fetchall()
    else:
        rows = conn.execute(
            "SELECT source_id, job_title, company, tech_stack FROM jobs LIMIT 50"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
