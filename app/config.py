from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded only from environment variables or .env.

    Provider credentials belong in backend configuration. They are never stored
    in SQLite and must never be included in API responses.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./quantum_jobs.db"
    app_secret_key: str = ""

    host: str = "127.0.0.1"
    port: int = 8000
    app_name: str = "A Hardware-Agnostic Orchestration Framework for Quantum Cloud Platforms"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    enable_ibm: bool = False
    ibm_quantum_token: str = Field(default="", repr=False)
    ibm_instance: str = ""
    ibm_channel: str = "ibm_quantum_platform"

    enable_aws_braket: bool = False
    aws_access_key_id: str = Field(default="", repr=False)
    aws_secret_access_key: str = Field(default="", repr=False)
    aws_region: str = "us-east-1"
    aws_braket_s3_bucket: str = ""
    aws_braket_s3_prefix: str = "quantum-orchestrator"

    enable_azure_quantum: bool = False
    azure_subscription_id: str = ""
    azure_resource_group: str = ""
    azure_workspace_name: str = ""
    azure_location: str = ""
    azure_tenant_id: str = Field(default="", repr=False)
    azure_client_id: str = Field(default="", repr=False)
    azure_client_secret: str = Field(default="", repr=False)

    # Async execution. For a local run without a broker, set
    # CELERY_TASK_ALWAYS_EAGER=true and jobs execute synchronously in-process.
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    worker_metrics_port: int = 9100

    # A job left in pending/running longer than this (minutes) is treated as
    # orphaned (e.g. its worker restarted) and marked failed at startup so the
    # UI does not show jobs stuck forever. Raise this if you run long real-QPU
    # jobs that legitimately queue for a long time.
    stale_job_minutes: int = 45

    # Background result storage directory (local filesystem, replaces MinIO/S3
    # for the local-first deployment). Raw counts are also kept in the DB.
    results_dir: str = "./job_results"

    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]
        if self.app_env.lower() == "production":
            origins = [origin for origin in origins if origin != "*"]
        return origins


settings = Settings()


def database_file_path() -> str:
    """Return the local SQLite file path from DATABASE_URL.

    This prototype intentionally supports SQLite only. Keeping DATABASE_URL in
    the config makes future migration to PostgreSQL or another DB explicit.
    """

    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// DATABASE_URL values are supported by this prototype.")

    raw_path = settings.database_url.removeprefix(prefix)
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return str(path.resolve())
