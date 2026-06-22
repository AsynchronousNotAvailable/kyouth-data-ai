# import sqlite3

# def get_db_connection(database_url: str):
#     conn = sqlite3.connect(database_url)
#     conn.row_factory = sqlite3.Row
#     return conn


# def init_db(database_url: str):
#     database_url.parent.mkdir(parents=True, exist_ok=True)
#     conn = get_db_connection(database_url)
#     conn.execute(
#         """
#         CREATE TABLE IF NOT EXISTS jobs (
#             source_id TEXT PRIMARY KEY,
#             job_title TEXT NOT NULL,
#             company TEXT NOT NULL,
#             description TEXT NOT NULL,
#             tech_stack TEXT
#         )
#         """
#     )
#     conn.commit()
#     return conn