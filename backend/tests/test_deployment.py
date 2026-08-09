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
    """Return valid settings for a protected production instance."""
    return Settings(
        environment="production",
        database_url="sqlite:////data/personal_planner.db",
        frontend_origins=[],
        allowed_hosts=["testserver"],
        require_auth=True,
        access_username="planner",
        access_password="a-long-test-password",
        frontend_dist=frontend_dist,
    )


def test_production_rejects_missing_authentication(tmp_path: Path):
    frontend_dist = build_frontend(tmp_path)

    with pytest.raises(
        ValidationError,
        match="Production requires authentication",
    ):
        Settings(
            environment="production",
            frontend_dist=frontend_dist,
        )


def test_authentication_rejects_missing_credentials():
    with pytest.raises(
        ValidationError,
        match="Access username and password are required",
    ):
        Settings(require_auth=True)


def test_production_rejects_missing_frontend_build():
    with pytest.raises(
        ValidationError,
        match="Production requires a frontend build",
    ):
        Settings(
            environment="production",
            require_auth=True,
            access_username="planner",
            access_password="a-long-test-password",
        )


def test_health_is_public_and_application_is_protected(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))

    with TestClient(application) as client:
        health = client.get("/health")
        unauthorized = client.get("/")
        invalid = client.get(
            "/",
            auth=("planner", "incorrect"),
        )

    assert health.status_code == status.HTTP_200_OK
    assert unauthorized.status_code == status.HTTP_401_UNAUTHORIZED
    assert invalid.status_code == status.HTTP_401_UNAUTHORIZED
    assert unauthorized.headers["www-authenticate"] == ('Basic realm="Pleno", charset="UTF-8"')


def test_production_serves_spa_assets_and_keeps_api_404(tmp_path: Path):
    application = create_app(production_settings(build_frontend(tmp_path)))
    credentials = ("planner", "a-long-test-password")

    with TestClient(application) as client:
        home = client.get(
            "/",
            auth=credentials,
        )
        deep_route = client.get(
            "/habitos",
            auth=credentials,
        )
        asset = client.get(
            "/assets/app.js",
            auth=credentials,
        )
        missing_api = client.get(
            "/api/v1/missing",
            auth=credentials,
        )
        docs = client.get(
            "/docs",
            auth=credentials,
        )

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
