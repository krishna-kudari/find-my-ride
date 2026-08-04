# syntax=docker/dockerfile:1
# ============================================================================
# STAGE 1: Builder Stage
# ============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.3 \
    POETRY_NO_ROOT=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_VIRTUALENVS_PATH="/opt/pysetup"

ENV PATH="/opt/pysetup/find-my-ride/bin:$PATH"

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists*

# Install Poetry
RUN pip install --upgrade pip setuptools wheel && \
    pip install poetry==${POETRY_VERSION}

WORKDIR /build

# Copy only dependency files (leverages Docker layer caching)
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
# --no-root: Don't install the package itself, only dependencies
RUN poetry install --no-root --no-interaction --no-ansi --only main

# ============================================================================
# STAGE 2: Development Stage (Optional - for local development)
# ============================================================================
FROM builder AS development

# Copy source code
COPY . /app

WORKDIR /app

# Configure Poetry to use the existing venv
RUN poetry env use /opt/pysetup/find-my-ride/bin/python

# Install dev dependencies (will use existing venv)
RUN poetry install --no-root --no-interaction --no-ansi

# Clean up build directory to reduce image size
RUN rm -rf /build

# create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

WORKDIR /app/src

CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]

# ============================================================================
# STAGE 3: Runtime Stage (Production)
# ============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/pysetup/find-my-ride/bin:$PATH"

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/pysetup/find-my-ride /opt/pysetup/find-my-ride

# Create app directory
WORKDIR /app

# Copy application code
COPY --chown=1000:1000 . .

# Create non-root user
RUN useradd -m -u 1000 appuser

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

CMD ["gunicorn", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--worker-class", "sync", \
    "--timeout", "120", \
    "myapp.wsgi:application"]
