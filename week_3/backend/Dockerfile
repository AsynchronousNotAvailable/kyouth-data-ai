FROM python:3.14.4-bookworm 

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV DEFAULT_MODEL=gemini-2.5-flash
ENV DB_PATH=/data/jobs.db

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
