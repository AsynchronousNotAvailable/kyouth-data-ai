import sys
from pathlib import Path

from src.ingestor import ingest_all_mhtml
from src.loader import load_all_jsons
from src.processor import process_all_html


def main():
    base_dir = Path(__file__).resolve().parent
    command = sys.argv[1] if len(sys.argv) > 1 else None

    if command == "ingest":
        ingest_all_mhtml(base_dir / "data/0_source", base_dir / "data/1_bronze")
    elif command == "process":
        process_all_html(base_dir / "data/1_bronze", base_dir / "data/2_silver")
    elif command == "load":
        load_all_jsons(base_dir / "data/2_silver")
    else:
        print("Usage: python main.py [ingest|process|load]")


if __name__ == "__main__":
    main()
