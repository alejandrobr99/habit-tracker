"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.habits import router as habits_router
from app.schemas import HealthRead

settings = get_settings()
app = FastAPI(
    title="Personal Planner API",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    habits_router,
    prefix=settings.api_prefix,
)


@app.get(
    "/health",
    response_model=HealthRead,
    tags=["health"],
)
def health() -> HealthRead:
    """Return service health."""
    return HealthRead(status="ok")
