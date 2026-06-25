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

SYSTEM_PROMPT = (
    "You are a helpful career and resume assistant. "
    "Help users improve their resumes, identify skill gaps, and prepare for job applications "
    "in the Malaysian tech job market. Be concise and practical."
)

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
    parts = [SYSTEM_PROMPT]
    if req.pdf_text.strip():
        # Truncate very large PDFs to avoid context overflow
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

    return {"locations": locations, "roles": roles}


@app.get("/api/jobs/search")
async def search_jobs(q: str = ""):
    if not DB_PATH.exists():
        return JSONResponse({"error": "Database not found"}, status_code=404)

    conn = get_db()
    if q.strip():
        rows = conn.execute(
            "SELECT source_id, job_title, company, tech_stack FROM jobs "
            "WHERE job_title LIKE ? OR company LIKE ? OR tech_stack LIKE ? LIMIT 100",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT source_id, job_title, company, tech_stack FROM jobs LIMIT 50"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
