import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

app = FastAPI(title="Resume Helper Frontend")

_here = Path(__file__).parent
app.mount("/static", StaticFiles(directory=_here / "static"), name="static")
templates = Jinja2Templates(directory=_here / "templates")


@app.get("/")
async def landing(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

# frontend route to serve the app html
@app.get("/app")
async def chat_app(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={"title": "Resume Helper Chatbot", "backend_url": BACKEND_URL},
    )
