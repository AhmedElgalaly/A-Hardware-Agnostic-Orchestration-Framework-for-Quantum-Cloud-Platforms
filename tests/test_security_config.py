from fastapi.testclient import TestClient

from app.config import Settings, database_file_path, settings
from app.main import app


def test_app_runs_without_env_file():
    local_settings = Settings(_env_file=None)

    assert local_settings.app_env == "development"
    assert local_settings.database_url.startswith("sqlite:///")
    assert local_settings.enable_ibm is False


def test_database_url_defaults_to_sqlite_file():
    assert database_file_path().endswith(".db")


def test_frontend_origins_default_to_local_vite_hosts():
    local_settings = Settings(_env_file=None)

    assert local_settings.cors_origins() == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_wildcard_cors_origin_is_not_allowed_in_production():
    production_settings = Settings(app_env="production", frontend_origins="*,http://localhost:5173", _env_file=None)

    assert production_settings.cors_origins() == ["http://localhost:5173"]


def test_backends_response_does_not_expose_provider_secrets(monkeypatch):
    monkeypatch.setattr(settings, "ibm_quantum_token", "super-secret-token")
    client = TestClient(app)

    response = client.get("/backends")

    assert response.status_code == 200
    payload = response.text
    assert "super-secret-token" not in payload
    assert "IBM_QUANTUM_TOKEN" not in payload
    assert "APP_SECRET_KEY" not in payload
