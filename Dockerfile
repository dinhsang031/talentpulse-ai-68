# ==============================================================================
# TALENTPULSE AI — DOCKERFILE FOR GOOGLE CLOUD RUN
# ==============================================================================
FROM python:3.11-slim

# Prevent Python from writing pyc files to disc & buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install system dependencies (build-essential, libmagic for file processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and static assets
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Expose default Cloud Run port
EXPOSE 8080

# Run FastAPI app with Uvicorn
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
