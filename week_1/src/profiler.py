from pathlib import Path

from database.config import DB_PATH, get_db_connection


def run_data_profile():
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE job_title IS NULL")
    null_title = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE company IS NULL")
    null_company = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE description IS NULL")
    null_desc = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(LENGTH(description)) FROM jobs")
    avg_len = cursor.fetchone()[0]

    cursor.execute(
        "SELECT source_id, job_title, LENGTH(description) FROM jobs ORDER BY LENGTH(description) ASC LIMIT 1"
    )
    shortest = cursor.fetchone()

    cursor.execute(
        "SELECT source_id, job_title, LENGTH(description) FROM jobs ORDER BY LENGTH(description) DESC LIMIT 1"
    )
    longest = cursor.fetchone()

    conn.close()

    print("--- 🔍 DATA QUALITY REPORT ---")
    print(f"📈 Total Records: {total}")
    print(
        f"❓ Missing Values -> job_title: {null_title}, company: {null_company}, description: {null_desc}"
    )
    print(f"📝 Avg Description Length: {round(avg_len)} chars")
    print(f"⚠️ Shortest Description: {shortest[2]} chars")
    print(f"   ↳ source_id: {shortest[0]} | job_title: {shortest[1]}")
    print(f"🚨 Longest Description: {longest[2]} chars")
    print(f"   ↳ source_id: {longest[0]} | job_title: {longest[1]}")
