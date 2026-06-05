# ==========================================================
# Stage 1: Build dependencies in a temporary environment
# ==========================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compiler dependencies if needed (e.g. for C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies under the user scheme
RUN pip install --no-cache-dir --user -r requirements.txt

# ==========================================================
# Stage 2: Minimal runtime environment
# ==========================================================
FROM python:3.11-slim AS runner

WORKDIR /app

# InfoSec Best Practice: Create and run container under a non-root user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy installed Python packages from the builder stage
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup app.py .

# Update PATH to prioritize local user binaries
ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

EXPOSE 5000

# Run with Gunicorn for concurrency and reliability
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "4"]
