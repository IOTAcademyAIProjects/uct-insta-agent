FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow, psycopg2, watchdog
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure DB dir exists
RUN mkdir -p db && mkdir -p logs && mkdir -p config

# Setup DB on build (will also run at runtime)
RUN python db/setup_db.py || true

EXPOSE 8080

# Healthcheck for Docker / K8s
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5).raise_for_status()" || exit 1

# Default: FastAPI + optional worker via env
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
