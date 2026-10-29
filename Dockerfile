# ==============================================================================
# OmniBlog Production Multi-Stage Dockerfile
# Optimized for Google Cloud Run and Vertex AI Agent Engine
# ==============================================================================

# Stage 1: Build virtualenv and install dependencies
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reliable package compilation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY requirements.txt pyproject.toml ./
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install -r requirements.txt

# Stage 2: Final minimal production runtime image
FROM python:3.12-slim-bookworm AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    HOST=0.0.0.0 \
    APP_HOME=/app

# Create unprivileged application user
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g appuser -s /bin/bash -m appuser

WORKDIR $APP_HOME

# Copy compiled virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code
COPY --chown=appuser:appuser . $APP_HOME

# Install project package into venv
RUN /opt/venv/bin/pip install --no-deps -e .

# Create directory for artifacts & database with appropriate ownership
RUN mkdir -p $APP_HOME/.adk $APP_HOME/artifacts && \
    chown -R appuser:appuser $APP_HOME

USER appuser

# Health check probe for Cloud Run / Container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

EXPOSE 8000

# Default entrypoint runs the FastAPI service with Uvicorn
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
