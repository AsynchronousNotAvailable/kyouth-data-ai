import sys

from enums.models import Models
from prompt_model import prompt_model


def main():
    if len(sys.argv) < 3:
        print("Usage: python main.py <model> <prompt>")
        print(f"  Local : {', '.join(sorted(Models.LOCAL_MODELS, key=lambda e: e.value))}")
        print(f"  Cloud : {', '.join(sorted(Models.CLOUD_MODELS, key=lambda e: e.value))}")
        sys.exit(1)

    model = sys.argv[1]
    prompt = " ".join(sys.argv[2:])
    result = prompt_model(model, prompt)
    print(result)


if __name__ == "__main__":
    main()
