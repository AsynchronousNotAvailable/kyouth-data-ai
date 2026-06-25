from ollama import Options as OllamaOptions
from ollama import chat as ollama_chat

from enums.models import Models
from settings.config import get_settings


def _call_local(model: str, prompt: str) -> str:
    try:
        response = ollama_chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            think=False,
            stream=False,
            options=OllamaOptions(temperature=0, top_p=0),
        )
        return response.message.content
    except Exception as exc:
        msg = str(exc)
        if "connect" in msg.lower() or "connection" in msg.lower():
            raise RuntimeError(
                f"Could not reach the Ollama server for model '{model}'. "
                "Make sure the Ollama service is running and OLLAMA_HOST is set correctly."
            ) from exc
        raise


def _call_gemini(model: str, prompt: str) -> str:
    from google import genai
    from google.genai import types

    api_key = get_settings().gemini_api_key
    if not api_key:
        raise RuntimeError(
            f"No API key provided for cloud model '{model}'. "
            "Set the GEMINI_API_KEY environment variable and restart the service."
        )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0, top_p=0),
        )
        return response.text
    except Exception as exc:
        msg = str(exc)
        if "api" in msg.lower() and ("key" in msg.lower() or "auth" in msg.lower() or "credential" in msg.lower()):
            raise RuntimeError(
                f"Authentication failed for cloud model '{model}'. "
                "Check that GEMINI_API_KEY is valid."
            ) from exc
        raise


def prompt_model(model: str, prompt: str) -> str:
    """Route to a local (Ollama) or cloud (Gemini) LLM and return the response."""
    if model in Models.LOCAL_MODELS:
        return _call_local(model, prompt)
    if model in Models.CLOUD_MODELS:
        return _call_gemini(model, prompt)
    raise ValueError(
        f"Unknown model '{model}'. "
        f"Local models: {', '.join(sorted(Models.LOCAL_MODELS))}. "
        f"Cloud models: {', '.join(sorted(Models.CLOUD_MODELS))}."
    )
