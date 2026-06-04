from __future__ import annotations

import json

from app.database import get_connection, init_db
from app.models import JobStatus, JobSummary, StoredJob
from app.services.result_normalizer import utc_now_iso


class JobRepository:
    def __init__(self) -> None:
        init_db()

    def create(
        self,
        job_id: str,
        name: str | None,
        request_body: dict,
        strategy: str,
    ) -> StoredJob:
        now = utc_now_iso()
        stored = StoredJob(
            job_id=job_id,
            name=name,
            request=request_body,
            strategy=strategy,
            status=JobStatus.pending,
            selected_backends=[],
            results=[],
            errors=[],
            created_at=now,
            updated_at=now,
        )
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, name, request_body, strategy, status, selected_backends,
                    results, errors, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.job_id,
                    stored.name,
                    json.dumps(stored.request),
                    stored.strategy,
                    stored.status,
                    json.dumps(stored.selected_backends),
                    json.dumps(stored.results),
                    json.dumps(stored.errors),
                    stored.created_at,
                    stored.updated_at,
                ),
            )
            connection.commit()
        return stored

    def update(
        self,
        job_id: str,
        status: JobStatus,
        selected_backends: list[dict] | None = None,
        results: list[dict] | None = None,
        errors: list[str] | None = None,
    ) -> StoredJob:
        current = self.get(job_id)
        updated = StoredJob(
            job_id=current.job_id,
            name=current.name,
            request=current.request,
            strategy=current.strategy,
            status=status,
            selected_backends=selected_backends if selected_backends is not None else current.selected_backends,
            results=results if results is not None else current.results,
            errors=errors if errors is not None else current.errors,
            created_at=current.created_at,
            updated_at=utc_now_iso(),
        )
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, selected_backends = ?, results = ?, errors = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (
                    updated.status,
                    json.dumps(updated.selected_backends),
                    json.dumps(updated.results),
                    json.dumps(updated.errors),
                    updated.updated_at,
                    job_id,
                ),
            )
            connection.commit()
        return updated

    def get(self, job_id: str) -> StoredJob:
        with get_connection() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return _row_to_stored_job(row)

    def fail_stale(self, max_age_minutes: int) -> int:
        """Mark pending/running jobs older than the threshold as failed.

        ISO-8601 UTC timestamps compare lexicographically in chronological
        order, so a simple string comparison is sufficient here.
        """
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()
        message = json.dumps(
            [
                f"Job did not reach a terminal state within {max_age_minutes} minutes; "
                "its worker may have restarted. Please resubmit."
            ]
        )
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = 'failed', errors = ?, updated_at = ?
                WHERE status IN ('pending', 'running') AND updated_at < ?
                """,
                (message, utc_now_iso(), cutoff),
            )
            connection.commit()
            return cursor.rowcount

    def list(self) -> list[JobSummary]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT job_id, name, strategy, status, created_at, updated_at
                FROM jobs
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [
            JobSummary(
                job_id=row["job_id"],
                name=row["name"],
                strategy=row["strategy"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


def _row_to_stored_job(row) -> StoredJob:
    return StoredJob(
        job_id=row["job_id"],
        name=row["name"],
        request=json.loads(row["request_body"]),
        strategy=row["strategy"],
        status=row["status"],
        selected_backends=json.loads(row["selected_backends"]),
        results=json.loads(row["results"]),
        errors=json.loads(row["errors"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
