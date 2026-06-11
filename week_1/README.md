# Week 1 — Job Listings ETL Pipeline

A local ETL pipeline that scrapes Malaysian tech job listings from Jobstreet, cleans and structures the data, loads it into SQLite, and produces a data quality report — all driven from a single CLI entry point.

---

## What I Built

| Stage | Layer | Input | Output |
|---|---|---|---|
| **Ingest** | Bronze | `.mhtml` saved pages | `.html` files |
| **Process** | Silver | `.html` files | `.json` files |
| **Load** | Gold | `.json` files | SQLite DB |
| **Profile** | Report | SQLite DB | Data quality metrics |

### Bronze — HTML Extraction (`src/ingestor.py`)
Reads raw `.mhtml` files (Jobstreet pages saved from Chrome) and extracts the HTML content into clean `.html` files. Handles quoted-printable encoding and multiple charsets.

### Silver — Data Cleaning & Structuring (`src/processor.py`)
Parses each HTML file with BeautifulSoup and extracts:
- `source_id` — parsed from the `og:url` meta tag (e.g. `https://jobstreet.com/job/12345678` → `12345678`)
- `job_title` — from `og:title` meta tag
- `description` — from `og:description` meta tag
- `company` — from `data-automation="advertiser-name"` span, with two fallback selectors for pages where that tag is empty

Validates that all required fields are present before writing. Outputs one `.json` per listing. Missing-field files are skipped with a warning.

**Result:** 98 of 100 listings successfully extracted (2 source pages had no company name in the HTML).

### Gold — Database Load (`src/loader.py`)
Inserts all Silver `.json` files into a SQLite database (`data/3_gold/jobs.db`). Uses `INSERT OR IGNORE` so re-running the pipeline never creates duplicates — skipped records are reported.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS jobs (
    source_id   TEXT PRIMARY KEY,
    job_title   TEXT NOT NULL,
    company     TEXT NOT NULL,
    description TEXT NOT NULL,
    tech_stack  TEXT           -- populated in Week 2/3 via AI tagging
);
```

### Profile — Data Quality Report (`src/profiler.py`)
Queries the database and prints a report covering:
- Total record count
- Null counts for `job_title`, `company`, and `description`
- Average description length
- Shortest and longest descriptions with their `source_id` and `job_title`

---

## Project Structure

```
week_1/
├── data/
│   ├── 0_source/    # Raw .mhtml files (100 Jobstreet pages)
│   ├── 1_bronze/    # Extracted .html files
│   ├── 2_silver/    # Structured .json files (one per listing)
│   └── 3_gold/      # jobs.db — SQLite database
├── database/
│   └── config.py    # DB path, connection, and table initialisation
├── schema/
│   └── jobs.sql     # Reference DDL
├── src/
│   ├── ingestor.py  # Bronze: .mhtml → .html
│   ├── processor.py # Silver: .html → .json
│   ├── loader.py    # Gold: .json → SQLite
│   └── profiler.py  # Report: data quality metrics
├── main.py          # CLI entry point
└── pyproject.toml
```

---

## Setup

```bash
uv sync          # installs dependencies and activates .venv automatically
```

> Requires Python 3.14+ and [uv](https://github.com/astral-sh/uv).

---

## CLI Usage

```bash
python main.py ingest     # Bronze: extract HTML from .mhtml source files
python main.py process    # Silver: parse HTML into structured JSON
python main.py load       # Gold: insert JSON records into SQLite
python main.py profile    # Report: print data quality metrics
python main.py all        # Run the full pipeline in order
```

Running without arguments prints available commands.

---

## Dependencies

| Package | Purpose |
|---|---|
| `beautifulsoup4` | HTML parsing and field extraction |
| `pydantic` | Data contract enforcement for `JobListing` |

Dev: `ruff` for linting.
