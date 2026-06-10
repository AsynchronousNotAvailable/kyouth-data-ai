-- Jobs Model
CREATE TABLE IF NOT EXISTS jobs (
    source_id TEXT PRIMARY KEY,
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    description TEXT NOT NULL,
    tech_stack TEXT
);