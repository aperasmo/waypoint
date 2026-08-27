# syntax=docker/dockerfile:1

# Build the locked Python environment separately so uv and build tooling do
# not need to exist in the final runtime image.
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app/backend

# Install locked runtime dependencies before application source so this layer
# remains cacheable when only Waypoint source code changes.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project


# The final image contains only Python, runtime dependencies, application code,
# deployment bootstrap scripts, and the corpus required by Waypoint.
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app/backend

# The public API does not require root privileges.
RUN groupadd --system --gid 10001 waypoint && \
    useradd --system --uid 10001 --gid waypoint --no-create-home waypoint

COPY --from=builder /app/backend/.venv /app/backend/.venv

COPY --chown=waypoint:waypoint backend/app ./app
COPY --chown=waypoint:waypoint backend/scripts/init_db.py ./scripts/init_db.py
COPY --chown=waypoint:waypoint backend/scripts/ingest.py ./scripts/ingest.py
COPY --chown=waypoint:waypoint data /app/data

USER waypoint

EXPOSE 8100

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
