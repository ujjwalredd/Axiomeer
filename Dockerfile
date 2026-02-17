FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app/

# Install package with redis support for caching
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[redis]"

# Expose port
EXPOSE 8000

# Run migrations then start server
CMD alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4
