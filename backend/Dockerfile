# Multi-stage Dockerfile for Mechanical Integrity AI System
# Optimized for safety-critical petroleum industry deployment

# Build stage - Install dependencies and build application
FROM python:3.11-slim-bullseye AS builder

# Set build arguments
ARG BUILD_ENV=production
ARG APP_VERSION=1.0.0

# Set environment variables for build optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# No need for uv when using requirements.txt with pip

# Create application directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt ./

# Install Python dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ .

# Build any necessary assets or run pre-deployment tasks
RUN echo "Build completed for ${BUILD_ENV} environment v${APP_VERSION}"

# Production stage - Create final runtime image
FROM python:3.11-slim-bullseye AS production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    UV_SYSTEM_PYTHON=1

# Set application metadata
LABEL maintainer="Mechanical Integrity AI Team" \
      version="1.0.0" \
      description="Safety-critical API 579 compliance system" \
      industry="petroleum" \
      compliance="API-579-1,API-510,API-570,API-653"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

# No need for uv in production image

# Set working directory
WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder --chown=appuser:appuser /app /app

# Create necessary directories
RUN mkdir -p /app/uploads /app/reports /app/logs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose application port
EXPOSE 8000

# Set default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Development stage - Add development tools and debugging capabilities  
FROM production AS development

# Switch back to root for installing dev tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy development requirements and install
COPY --from=builder /app/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Set development environment
ENV ENVIRONMENT=development \
    DEBUG=true

# Switch back to app user
USER appuser

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Testing stage - Add testing tools and run test suite
FROM development AS testing

USER root

# Install testing dependencies (dev dependencies already in requirements.txt)
RUN pip install --no-cache-dir pytest pytest-cov black ruff mypy

# Copy test files
COPY --chown=appuser:appuser tests/ /app/tests/
COPY --chown=appuser:appuser pytest.ini /app/
COPY --chown=appuser:appuser .coveragerc /app/

USER appuser

# Run tests by default
CMD ["python", "-m", "pytest", "tests/", "--cov=app", "--cov-report=html", "--cov-report=term-missing"]