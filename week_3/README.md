# KYouth AI — Week 3: Resume Helper

A full-stack AI chatbot for CV analysis and skill gap detection, backed by a Malaysian tech job market dashboard.

- **Frontend** — FastAPI + Jinja2, dark theme UI, chat interface, job dashboard
- **Backend** — FastAPI, supports local (Ollama) and cloud (Gemini) LLMs
- **Ollama** — optional local LLM server (not required when using Gemini)

Docker Hub images:
- `dd3638271007/kyouth-frontend`
- `dd3638271007/kyouth-backend`

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A `docker.env` file in this directory (see setup below)

---

## Configuration — `docker.env`

Create a `docker.env` file in `week_3/`:

```env
# LLM — choose a local Ollama model or a Gemini cloud model
DEFAULT_MODEL=gemini-2.5-flash-lite

# Required when using a Gemini model
GEMINI_API_KEY=your_gemini_api_key_here

# Ollama server address (only needed for local models)
OLLAMA_HOST=http://ollama:11434

# Path to the jobs database inside the container (do not change)
DB_PATH=/data/jobs.db

# Backend URL as seen by the browser
BACKEND_URL=http://localhost:8001
```

> `docker.env` is gitignored — never commit API keys.

---

## Option 1 — Run with Docker Compose (recommended)

Pulls pre-built images from Docker Hub and starts all services.

```bash
cd week_3

# First run — pull images and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Services started:

| Service | URL |
|---|---|
| Frontend | http://localhost:8000 |
| Backend API | http://localhost:8001 |
| Ollama (local LLM) | http://localhost:11434 |

> If you are using Gemini only and want to skip the Ollama container, comment out the `ollama` service and its `depends_on` block in `docker-compose.yml`.

---

## Option 2 — Pull images and run manually

Pull the images:

```bash
docker pull dd3638271007/kyouth-backend:latest
docker pull dd3638271007/kyouth-frontend:latest
```

Run the backend:

```bash
docker run -d \
  --name kyouth-backend \
  -p 8001:8001 \
  --env-file docker.env \
  -v $(pwd)/../week_2/data/jobs.db:/data/jobs.db:ro \
  dd3638271007/kyouth-backend:latest
```

Run the frontend:

```bash
docker run -d \
  --name kyouth-frontend \
  -p 8000:8000 \
  --env-file docker.env \
  dd3638271007/kyouth-frontend:latest
```

> When running without Docker Compose, the backend and frontend are on separate networks. Set `BACKEND_URL=http://localhost:8001` in `docker.env` so the browser can reach the backend via the exposed host port.

---

## Option 3 — Build images locally and push to Docker Hub

Build both images:

```bash
cd week_3

docker build -t <your-dockerhub-username>/kyouth-backend ./backend
docker build -t <your-dockerhub-username>/kyouth-frontend ./frontend
```

Push to Docker Hub:

```bash
docker login

docker push <your-dockerhub-username>/kyouth-backend
docker push <your-dockerhub-username>/kyouth-frontend
```

Update `docker-compose.yml` to use your own images:

```yaml
backend:
  image: <your-dockerhub-username>/kyouth-backend:latest

frontend:
  image: <your-dockerhub-username>/kyouth-frontend:latest
```

---

## Local model setup (optional)

If you want to use a local Ollama model instead of Gemini:

1. Set `DEFAULT_MODEL=phi3:latest` (or any model) in `docker.env`
2. Make sure Ollama has enough RAM — model file size ≈ RAM required at runtime
3. Pull the model into the running Ollama container:

```bash
docker exec week_3-ollama-1 ollama pull phi3:latest
```

4. Restart the backend:

```bash
docker compose restart backend
```

> Docker Desktop default VM memory is ~3.8 GiB. Models larger than ~2.5 GiB will likely cause an out-of-memory kill. Increase memory under Docker Desktop → Settings → Resources → Memory if needed.
