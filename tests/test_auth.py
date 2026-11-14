import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import create_app


def secure_client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://test:test@localhost/test?sslmode=require"
    )
    monkeypatch.setenv("APP_USERNAME", "owner")
    monkeypatch.setenv(
        "APP_PASSWORD_HASH", PasswordHash.recommended().hash("correct horse battery")
    )
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key-that-is-long-enough")
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'auth.sqlite3').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app(database_engine=engine)

    def override_get_db():
        with session_local() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    return app, engine


def test_production_api_requires_login_and_session_cookie(tmp_path, monkeypatch):
    app, engine = secure_client(tmp_path, monkeypatch)
    try:
        with TestClient(app, base_url="https://testserver") as client:
            assert client.get("/api/auth/status").json() == {
                "auth_enabled": True,
                "authenticated": False,
            }
            assert client.get("/api/transactions").status_code == 401

            failed = client.post(
                "/api/auth/login",
                json={"username": "owner", "password": "wrong password"},
                headers={"Origin": "https://testserver"},
            )
            successful = client.post(
                "/api/auth/login",
                json={"username": "owner", "password": "correct horse battery"},
                headers={"Origin": "https://testserver"},
            )

            assert failed.status_code == 401
            assert successful.status_code == 200
            cookie = successful.headers["set-cookie"].lower()
            assert "httponly" in cookie
            assert "secure" in cookie
            assert "samesite=strict" in cookie
            assert client.get("/api/transactions").status_code == 200
            assert client.get("/docs").status_code == 404

            logged_out = client.post(
                "/api/auth/logout", headers={"Origin": "https://testserver"}
            )
            assert logged_out.status_code == 200
            assert client.get("/api/transactions").status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_production_rejects_cross_origin_mutation(tmp_path, monkeypatch):
    app, engine = secure_client(tmp_path, monkeypatch)
    try:
        with TestClient(app, base_url="https://testserver") as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "owner", "password": "correct horse battery"},
                headers={"Origin": "https://attacker.example"},
            )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_production_fails_closed_without_auth_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.delenv("APP_USERNAME", raising=False)
    monkeypatch.delenv("APP_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="required"):
        create_app()


def test_login_rate_limits_repeated_failures(tmp_path, monkeypatch):
    app, engine = secure_client(tmp_path, monkeypatch)
    try:
        with TestClient(app, base_url="https://testserver") as client:
            responses = [
                client.post(
                    "/api/auth/login",
                    json={"username": "owner", "password": "wrong"},
                    headers={"Origin": "https://testserver"},
                )
                for _ in range(6)
            ]
        assert [response.status_code for response in responses] == [
            401, 401, 401, 401, 401, 429
        ]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
