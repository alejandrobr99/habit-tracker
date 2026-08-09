"""FastAPI application entry point."""

import base64
import binascii
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings, get_settings
from app.routers.finance import router as finance_router
from app.routers.gamification import recovery_router
from app.routers.gamification import router as gamification_router
from app.routers.habits import router as habits_router
from app.schemas import HealthRead


def _has_valid_credentials(request: Request, settings: Settings) -> bool:
    """Return whether a request contains the configured Basic credentials."""
    authorization = request.headers.get("Authorization", "")
    scheme, separator, encoded = authorization.partition(" ")
    if scheme.lower() != "basic" or not separator or not encoded:
        return False
    try:
        decoded = base64.b64decode(
            encoded,
            validate=True,
        ).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, separator, password = decoded.partition(":")
    if not separator or settings.access_password is None or settings.access_username is None:
        return False
    return secrets.compare_digest(
        username.encode(),
        settings.access_username.encode(),
    ) and secrets.compare_digest(
        password.encode(),
        settings.access_password.get_secret_value().encode(),
    )


def _add_frontend_routes(
    application: FastAPI,
    frontend_dist: Path,
    api_prefix: str,
) -> None:
    """Serve built frontend files without swallowing unknown API routes."""
    assets_directory = frontend_dist / "assets"
    if assets_directory.is_dir():
        application.mount(
            "/assets",
            StaticFiles(directory=assets_directory),
            name="assets",
        )
    resolved_dist = frontend_dist.resolve()
    normalized_api_prefix = api_prefix.strip("/")
    reserved_paths = {
        "docs",
        "openapi.json",
        "redoc",
    }

    @application.get(
        "/{full_path:path}",
        include_in_schema=False,
    )
    def serve_frontend(full_path: str) -> FileResponse:
        """Return a static file or the SPA entry point."""
        if (
            full_path in reserved_paths
            or full_path == normalized_api_prefix
            or full_path.startswith(
                f"{normalized_api_prefix}/",
            )
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        requested_file = (resolved_dist / full_path).resolve()
        if requested_file.is_relative_to(resolved_dist) and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(resolved_dist / "index.html")


def create_app(runtime_settings: Settings | None = None) -> FastAPI:
    """Create the application for the configured runtime."""
    settings = runtime_settings or get_settings()
    is_production = settings.environment == "production"
    application = FastAPI(
        title="Personal Planner API",
        version="0.1.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    @application.middleware("http")
    async def require_access(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Protect all data and frontend routes when access control is enabled."""
        if (
            settings.require_auth
            and request.url.path != "/health"
            and not _has_valid_credentials(
                request,
                settings,
            )
        ):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Se requiere una credencial válida."},
                headers={"WWW-Authenticate": 'Basic realm="Pleno", charset="UTF-8"'},
            )
        return await call_next(request)

    @application.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add browser security headers to every application response."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
        return response

    application.include_router(
        habits_router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        finance_router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        gamification_router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        recovery_router,
        prefix=settings.api_prefix,
    )

    @application.get(
        "/health",
        response_model=HealthRead,
        tags=["health"],
    )
    def health() -> HealthRead:
        """Return service health."""
        return HealthRead(status="ok")

    if settings.frontend_dist is not None:
        _add_frontend_routes(
            application,
            settings.frontend_dist,
            settings.api_prefix,
        )
    return application


app = create_app()
