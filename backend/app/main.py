"""FastAPI application for Waypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import browse
from app.config import get_settings
from app.db.session import dispose_engine

from app.api.routes import ask, browse

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Close the connection pool on shutdown so the database does not hold
    # sockets open for a process that has gone.
    await dispose_engine()


settings = get_settings()

app = FastAPI(
    title="Waypoint",
    description=(
        "Evidence-based retrieval over the publicly available Immigration New "
        "Zealand Operational Manual. Returns cited source material only. Does "
        "not provide immigration advice."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Vite's dev server. Production origins come from settings, never a wildcard,
# since a wildcard plus credentials is a standing invitation.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(browse.router)
app.include_router(ask.router)

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}