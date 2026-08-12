"""Deployment configuration and HTTP boundary tests."""

from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app


def build_frontend(tmp_path: Path) -> Path:
    """Create the minimum files produced by a frontend build."""
    frontend_dist = tmp_path / "frontend"
    assets_directory = frontend_dist / "assets"
    assets_directory.mkdir(parents=True)
    (frontend_dist / "index.html").write_text(
        "<html><body>Pleno</body></html>",
        encoding="utf-8",
    )
    (assets_directory / "app.js").write_text(
        "console.log('Pleno');",
        encoding="utf-8",
    )
    return frontend_dist


def production_settings(frontend_dist: Path) -> Settings:
    """Return valid settings for a production instance."""
    return Settings(
        environment="production",
        database_url="sqlite:////data/personal_planner.db",
        frontend_origins=[],
        allowed_hosts=["testserver"],
        frontend_dist=frontend_dist,
    )


def test_production_accepts_bootstrap_secrets_or_a_configured_database(tmp_path: Path):
    frontend_dist = build_frontend(tmp_path)

    settings = Settings(
        environment="production",
        frontend_dist=frontend_dist,
    )

    assert settings.bootstrap_admin_username is None


def test_bootstrap_rejects_incomplete_credentials():
    with pytest.raises(
        ValidationError,
        match="Bootstrap username and password must be configured together",
    ):
        Settings(bootstrap_admin_username="planner")


def test_production_rejects_missing_frontend_build():
    with pytest.raises(
        ValidationError,
        match="Production requires a frontend build",
    ):
        Settings(
            environment="production",
        )


def test_health_is_public_and_application_is_protected(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        health = client.get("/health")
        frontend = client.get("/")
        unauthorized = client.get("/api/v1/habits")

    assert health.status_code == status.HTTP_200_OK
    assert frontend.status_code == status.HTTP_200_OK
    assert unauthorized.status_code == status.HTTP_401_UNAUTHORIZED


def test_production_serves_spa_assets_and_keeps_api_404(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        home = client.get("/")
        deep_route = client.get("/habitos")
        asset = client.get("/assets/app.js")
        missing_api = client.get("/api/v1/missing")
        docs = client.get("/docs")

    assert home.status_code == status.HTTP_200_OK
    assert "Pleno" in home.text
    assert deep_route.status_code == status.HTTP_200_OK
    assert "Pleno" in deep_route.text
    assert asset.status_code == status.HTTP_200_OK
    assert missing_api.status_code == status.HTTP_404_NOT_FOUND
    assert missing_api.headers["content-type"].startswith("application/json")
    assert docs.status_code == status.HTTP_404_NOT_FOUND


def test_security_headers_are_present(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == ("camera=(), geolocation=(), microphone=()")
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"


def test_content_security_policy_contains_no_unsafe_source(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        policy = client.get("/").headers["content-security-policy"]

    assert "unsafe-inline" not in policy
    assert "unsafe-eval" not in policy
    assert "default-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy
    assert "base-uri 'none'" in policy


def test_security_headers_also_cover_error_responses(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        unauthorized = client.get("/api/v1/habits")
        missing = client.get("/api/v1/missing")

    for response in (unauthorized, missing):
        assert response.headers["content-security-policy"]
        assert response.headers["x-content-type-options"] == "nosniff"
    assert unauthorized.status_code == status.HTTP_401_UNAUTHORIZED
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_transport_security_is_production_only(tmp_path: Path):
    production = create_app(production_settings(build_frontend(tmp_path)))
    development = create_app(Settings(allowed_hosts=["testserver"]))

    with TestClient(production) as client:
        secured = client.get("/health")
    with TestClient(development) as client:
        local = client.get("/health")

    assert secured.headers["strict-transport-security"] == ("max-age=31536000; includeSubDomains")
    assert "strict-transport-security" not in local.headers


def test_api_responses_are_never_stored(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        api = client.get("/api/v1/habits")
        page = client.get("/")

    assert api.headers["cache-control"] == "no-store"
    assert "cache-control" not in page.headers
