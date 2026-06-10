import json
from pathlib import Path

from database.config import init_db


def load_all_jsons(input_dir):
    conn = init_db()
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    failed = 0
    source_dir = Path(input_dir)

    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Input directory is not a directory: {source_dir}")

    print("🥇 Gold:")

    for json_file in sorted(source_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict):
                print(f"⚠️ Invalid format: {json_file.name}")
                failed += 1
                continue

            cursor.execute(
                """
                INSERT OR IGNORE INTO jobs (source_id, job_title, company, description)
                VALUES (?, ?, ?, ?)
                """,
                (data.get("source_id"), data.get("job_title"), data.get("company"), data.get("description")),
            )
            conn.commit()

            if cursor.rowcount == 0:
                print(f"⏭️ Skipped (duplicate): {json_file.name}")
                skipped += 1
            else:
                print(f"✅ Inserted: {json_file.name}")
                inserted += 1

        except Exception as error:
            print(f"❌ Failed: {json_file.name} ({error})")
            failed += 1

    conn.close()

    print()
    print("📊 Gold Summary:")
    print(f"Total: {inserted + skipped + failed} | Inserted: {inserted} | Skipped: {skipped}")
