"""FastAPI application entry point."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth import SESSION_COOKIE_NAME
from app.config import Settings, get_settings
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.finance import router as finance_router
from app.routers.gamification import recovery_router
from app.routers.gamification import router as gamification_router
from app.routers.habits import router as habits_router
from app.schemas import HealthRead
from app.security import (
    SECURITY_HEADERS,
    STRICT_TRANSPORT_SECURITY,
    RequestSizeLimitMiddleware,
    configure_security_logging,
    log_security_event,
    resolve_client_ip,
)

ALLOWED_CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_CORS_HEADERS = ["Content-Type"]
CORS_PREFLIGHT_MAX_AGE = 600


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
    configure_security_logging()
    application = FastAPI(
        title="Personal Planner API",
        version="0.1.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    # Middleware runs outermost-last: security headers wrap every response, including
    # the ones produced by host, size, and origin rejections.
    @application.middleware("http")
    async def protect_authenticated_mutations(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Reject cross-origin mutations made with a session cookie."""
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and SESSION_COOKIE_NAME in request.cookies
            and not _has_valid_origin(request, settings)
        ):
            log_security_event(
                "request_origin_rejected",
                method=request.method,
                path=request.url.path,
                client_ip=resolve_client_ip(request, settings),
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Origen de solicitud no permitido."},
            )
        return await call_next(request)

    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=settings.max_request_bytes,
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=ALLOWED_CORS_METHODS,
        allow_headers=ALLOWED_CORS_HEADERS,
        max_age=CORS_PREFLIGHT_MAX_AGE,
    )

    @application.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Add browser security headers to every application response."""
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if is_production:
            response.headers["Strict-Transport-Security"] = STRICT_TRANSPORT_SECURITY
        if request.url.path.startswith(settings.api_prefix):
            response.headers["Cache-Control"] = "no-store"
        return response

    application.include_router(
        auth_router,
        prefix=settings.api_prefix,
    )
    application.include_router(
        admin_router,
        prefix=settings.api_prefix,
    )
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


def _has_valid_origin(request: Request, settings: Settings) -> bool:
    """Return whether a mutating browser request comes from an allowed origin."""
    origin = request.headers.get("origin")
    if not origin:
        return False
    if origin in settings.frontend_origins:
        return True
    parsed_origin = urlsplit(origin)
    return parsed_origin.netloc == request.headers.get("host")


app = create_app()
