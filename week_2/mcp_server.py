"""FastMCP server — exposes jobs DB operations as tools."""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP

_DB_URL = Path(__file__).parent / "data" / "jobs.db"

mcp = FastMCP("jobs-db")


def _conn() -> sqlite3.Connection:
    if not _DB_URL.exists():
        raise FileNotFoundError(f"Database not found: {_DB_URL}")
    conn = sqlite3.connect(_DB_URL)
    conn.row_factory = sqlite3.Row
    return conn


@mcp.tool()
def get_untagged_jobs() -> str:
    """Return JSON list of {source_id, description} for jobs without tech_stack."""
    conn = _conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, description FROM jobs "
            "WHERE tech_stack IS NULL OR tech_stack = ''"
        )
        return json.dumps([dict(r) for r in cursor.fetchall()])
    finally:
        conn.close()


@mcp.tool()
def batch_update_tech_stacks(updates_json: str) -> str:
    """Accept JSON list of {source_id, tech_stack} and write all in one transaction."""
    conn = _conn()
    try:
        items: list[dict] = json.loads(updates_json)
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE jobs SET tech_stack = ? WHERE source_id = ?",
            [(item["tech_stack"], item["source_id"]) for item in items],
        )
        conn.commit()
        return "ok"
    except Exception as e:
        return f"error: {e}"
    finally:
        conn.close()


@mcp.tool()
def get_all_tech_stacks() -> str:
    """Return JSON list of {source_id, tech_stack} for all jobs (for quality report)."""
    conn = _conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT source_id, tech_stack FROM jobs")
        return json.dumps([dict(r) for r in cursor.fetchall()])
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()
