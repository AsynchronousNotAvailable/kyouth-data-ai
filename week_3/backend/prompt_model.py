from ollama import Options as OllamaOptions
from ollama import chat as ollama_chat

from enums.models import Models
from settings.config import get_settings


def _call_local(model: str, prompt: str) -> str:
    response = ollama_chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        stream=False,
        options=OllamaOptions(temperature=0, top_p=0),
    )
    return response.message.content


def _call_gemini(model: str, prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=get_settings().gemini_api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, top_p=0),
    )
    return response.text


def prompt_model(model: str, prompt: str) -> str:
    """Call a local (Ollama) or cloud (Gemini) LLM and return the response."""
    if model in Models.LOCAL_MODELS:
        return _call_local(model, prompt)
    if model in Models.CLOUD_MODELS:
        return _call_gemini(model, prompt)
    raise ValueError(
        f"Unknown model '{model}'.\n"
        f"  Local : {', '.join(sorted(Models.LOCAL_MODELS))}\n"
        f"  Cloud : {', '.join(sorted(Models.CLOUD_MODELS))}"
    )
