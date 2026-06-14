import sys

from ollama import chat as ollama_chat

from enums.models import Models
from settings.config import get_settings



def _call_local(model: str, prompt: str) -> str:
    response = ollama_chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        think=False,
        stream=False,
    )
    if response.message.thinking:
        print("Thinking:\n", response.message.thinking)
    return response.message.content


def _call_gemini(model: str, prompt: str) -> str:
    from google import genai

    client = genai.Client(api_key=get_settings().gemini_api_key)
    response = client.models.generate_content(model=model, contents=prompt)
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


def main():
    if len(sys.argv) < 3:
        print("Usage: python prompt_model.py <model> <prompt>")
        print(f"  Local : {', '.join(sorted(Models.LOCAL_MODELS))}")
        print(f"  Cloud : {', '.join(sorted(Models.CLOUD_MODELS))}")
        sys.exit(1)

    model = sys.argv[1]
    prompt = " ".join(sys.argv[2:])
    result = prompt_model(model, prompt)
    print(result)


if __name__ == "__main__":
    main()
