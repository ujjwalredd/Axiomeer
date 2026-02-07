FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application code first (needed for pip install -e .)
COPY . /app/

# Upgrade pip and install dependencies
RUN pip install --upgrade pip && pip install -e .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4
