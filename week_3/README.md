# KYouth AI — Week 3: Resume Helper

A containerised full-stack chatbot that analyses CVs, identifies skill gaps, and surfaces Malaysian tech job market insights. Built with a FastAPI backend, a FastAPI/Jinja2 frontend, and an optional local LLM via Ollama — all orchestrated with Docker Compose.

---

## Project Overview

| Layer | Technology | Role |
|---|---|---|
| Frontend | FastAPI + Jinja2 + Bootstrap 5 | Dark-theme chat UI and job dashboard |
| Backend | FastAPI + SQLite | `/chat` endpoint, job stats, job search |
| LLM | Ollama (local) or Gemini (cloud) | CV analysis and skill gap detection |
| Data | SQLite (`jobs.db` from Week 2) | 98 scraped Malaysian tech jobs with tech stack tags |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x with Docker Compose v2
- (Optional, for local models) Docker Desktop memory set to **8 GiB+** under Settings → Resources → Memory

---

## Setup

### 1. Clone and enter the project

```bash
git clone <repo-url>
cd week_3
```

### 2. Create your environment file

```bash
cp docker.example.env docker.env
```

Edit `docker.env` and fill in your values:

```env
# Ollama server — use service name when running via docker compose
OLLAMA_HOST=http://ollama:11434

# Choose a model:
#   Local  — must be pulled into the Ollama container first
DEFAULT_MODEL=llama3.1:latest
#   Cloud  — requires GEMINI_API_KEY
# DEFAULT_MODEL=gemini-2.5-flash-lite

# Required only when using a Gemini model
GEMINI_API_KEY=your_key_here

# Do not change — path inside the backend container
DB_PATH=/data/jobs.db

# URL the browser uses to reach the backend
BACKEND_URL=http://localhost:8001
```

> `docker.env` is gitignored. Never commit API keys.

---

## Usage

### Run with Docker Compose

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (chat + dashboard) | http://localhost:8000 |
| Backend API | http://localhost:8001 |
| Ollama (local LLM) | http://localhost:11434 |

Stop all services:

```bash
docker compose down
```

### Expected inputs and outputs

**Chat tab**
- Type a question about careers, CVs, or the Malaysian tech job market
- Optionally attach a PDF resume using the paperclip icon
- The chatbot responds in formatted Markdown with bullet lists and bold headings

**Dashboard tab**
- Automatically loads charts: job roles by category, jobs by location, top 15 tech skills
- Use the search bar to filter 98 jobs by title, company, description, or tech stack

### Using a local Ollama model

If `DEFAULT_MODEL` is set to a local model (e.g. `llama3.1:latest`), pull it into the running container first:

```bash
docker exec week_3-ollama-1 ollama pull llama3.1:latest
```

> **Memory requirement:** The model file size ≈ RAM required at inference time. `llama3.1` needs ~5 GB RAM. Docker Desktop's default VM is ~3.8 GiB, which is not enough — increase it or use Gemini instead.

---

## API Reference

### `POST /chat`

Sends a message (and optional CV text) to the LLM.

**Request body**
```json
{
  "message": "Find skill gaps for a data engineer role",
  "pdf_text": "John Doe\nExperience: ...",
  "model": "gemini-2.5-flash-lite"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | User's question or instruction |
| `pdf_text` | string | No | Extracted text from an uploaded PDF |
| `model` | string | No | Model ID (defaults to `DEFAULT_MODEL` env var) |

**Response**
```json
{
  "reply": "**Skill Gaps Identified**\n\n- Apache Kafka\n- dbt\n- Airflow",
  "model": "gemini-2.5-flash-lite"
}
```

**Guard behaviours**
- No PDF + CV-analysis request → asks the user to attach their CV first (no LLM call)
- Non-CV PDF attached → LLM detects and responds that it is out of scope
- Off-topic question → LLM responds with an out-of-scope message

---

### `GET /api/stats`

Returns aggregated counts for the job dashboard charts.

**Response**
```json
{
  "locations": { "Kuala Lumpur": 42, "Selangor": 18 },
  "roles":     { "Data Engineer": 25, "Software Engineer": 20 },
  "top_skills": { "Python": 61, "Sql": 45, "Docker": 30 }
}
```

---

### `GET /api/jobs/search?q=python&field=tech_stack`

Searches jobs in the SQLite database.

| Parameter | Values | Description |
|---|---|---|
| `q` | any string | Search term (empty returns first 50 jobs) |
| `field` | `all`, `title`, `company`, `description`, `tech_stack` | Field to search in |

**Response** — array of job objects:
```json
[
  {
    "source_id": "JS001",
    "job_title": "Data Engineer Job in KL",
    "company": "Acme Sdn Bhd",
    "tech_stack": "Python, Spark, Airflow"
  }
]
```

---

### Frontend → Backend interaction

The frontend Python server injects `BACKEND_URL` into the HTML template at render time. All API calls are made client-side by the browser's JavaScript — the frontend container itself never contacts the backend directly.

```
Browser ──→ localhost:8000  (frontend container serves HTML)
Browser ──→ localhost:8001  (browser JS calls backend API directly)
```

Inside Docker Compose both containers share `app-network`, but this network is only used for the backend's dependency on Ollama — not for frontend-to-backend calls.

---

## Data and Assumptions

### Data flow

```
User types message + (optional) PDF
    │
    ▼
PDF.js extracts text client-side (browser)
    │
    ▼
POST /chat  { message, pdf_text, model }
    │
    ▼
Backend builds prompt → LLM (Ollama or Gemini)
    │
    ▼
LLM returns Markdown text
    │
    ▼
Browser renders via marked.js → chat bubble
```

### Assumptions and constraints

| Constraint | Detail |
|---|---|
| PDF size | Truncated to 8 000 characters of extracted text |
| PDF content | Must be text-based (not scanned images) — PDF.js cannot OCR |
| CV detection | LLM-based; heuristic — may misclassify unusual formats |
| Chat history | In-memory per browser session; not persisted |
| Job data | 98 jobs scraped from Jobstreet (Week 2); static dataset |
| Tech stack tags | Generated by Gemini 2.5 Flash; may have minor inaccuracies |
| Model context | Single-turn prompt; no multi-turn conversation memory |

---

## Testing

### Backend — curl

Test the chat endpoint with no PDF (guard should trigger):

```bash
curl -s -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"summarize my cv","pdf_text":""}' | python3 -m json.tool
```

Test with a non-CV PDF:

```bash
curl -s -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"summarize this","pdf_text":"Invoice #1234\nAmount: RM 5000"}' | python3 -m json.tool
```

Test job search:

```bash
curl "http://localhost:8001/api/jobs/search?q=python&field=tech_stack"
```

Test stats endpoint:

```bash
curl http://localhost:8001/api/stats | python3 -m json.tool
```

### Frontend — manual test cases

| Scenario | Expected result |
|---|---|
| Send message without PDF | Normal chatbot response |
| Ask to "summarize my CV" without PDF | Bot asks to attach CV first |
| Attach an invoice PDF and ask to summarize | Bot refuses — not a CV |
| Attach a real CV and ask for skill gaps | Structured Markdown response |
| Switch to Dashboard tab | Charts render; search bar filters table |
| Search "Python" with Tech Stack filter | Only jobs with Python in tech_stack shown |

---

## Limitations

- **No chat history persistence** — refreshing the page clears all messages
- **No authentication** — anyone with access to the URL can use the app
- **Single-turn memory** — the model sees only the current message and PDF, not prior conversation turns
- **PDF OCR not supported** — scanned image PDFs will produce empty text
- **CV detection is heuristic** — the LLM may not correctly reject all non-CV documents
- **Static job data** — the dataset is a snapshot from Week 2; no live scraping
- **Local model memory constraint** — models larger than ~2.5 GB will OOM in the default Docker Desktop VM
- **Gemini rate limits** — the free tier has strict RPM/RPD limits; heavy use will return 503 errors

---

## Architecture Reflection

### Design choices

The frontend and backend are kept as separate services for a clear reason: the LLM call is slow (1–10 seconds) and belongs on the server, while PDF extraction and chat rendering benefit from running in the browser without a round-trip. Separating them also means the backend can be swapped or scaled independently, and the frontend can be served as a static-like layer.

Docker Compose was chosen over a single-container approach because it gives each service its own network identity and lifecycle. The Ollama service can be commented out entirely when using cloud models, and the backend waits for Ollama's healthcheck before starting — preventing race-condition startup failures.

### Trade-offs

- **Simplicity over scalability** — a single SQLite file is enough for 98 jobs, but would not scale to millions of rows. A real deployment would use PostgreSQL.
- **Cloud model as default** — Gemini is more capable and requires no local RAM, but introduces API cost and a dependency on Google's availability. Local Ollama models remove that dependency at the cost of hardware requirements.
- **Single-turn prompting** — stateless prompts are simpler to implement and debug, but limit the chatbot to analysing only what is in the current message.

### Improvements

- Add multi-turn conversation history so the model remembers earlier messages in the session
- Persist chat sessions in a database so users can return to previous conversations
- Add a vector search layer over the job listings so the chatbot can recommend specific jobs that match the user's CV
- Replace Jinja2 templates with a React or Vue frontend for richer interactivity
- Deploy backend and frontend to a cloud platform (Railway, Render) with environment variables managed as platform secrets
