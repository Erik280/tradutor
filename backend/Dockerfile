# ─── Build Stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ─── Runtime Stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source
COPY app/ ./app/

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

# Start uvicorn in production mode
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
