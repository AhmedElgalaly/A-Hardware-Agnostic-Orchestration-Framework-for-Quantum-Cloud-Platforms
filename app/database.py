from __future__ import annotations

import sqlite3

from app.config import database_file_path


def get_connection() -> sqlite3.Connection:
    # The API process and the Celery worker run in separate containers that share
    # this database over a Docker volume. WAL mode keeps recent commits in a
    # shared-memory (-wal/-shm) sidecar that does NOT reliably cross the container
    # boundary, so the API would not see the worker's writes until it restarted
    # (jobs appeared stuck at "pending"). Use the default rollback journal, where
    # every new connection reads committed data directly from the main file, and a
    # busy timeout to ride out brief write locks. The explicit DELETE pragma also
    # converts any existing database that was previously left in WAL mode.
    connection = sqlite3.connect(database_file_path(), timeout=30, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=DELETE;")
    connection.execute("PRAGMA busy_timeout=30000;")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT,
                request_body TEXT NOT NULL,
                strategy TEXT NOT NULL,
                status TEXT NOT NULL,
                selected_backends TEXT NOT NULL,
                results TEXT NOT NULL,
                errors TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
