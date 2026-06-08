from pathlib import Path

from src.ingestor import ingest_all_mhtml


def main():
    base_dir = Path(__file__).resolve().parent
    ingest_all_mhtml(base_dir / "data/0_source", base_dir / "data/1_bronze")


if __name__ == "__main__":
    main()
