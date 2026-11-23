FROM python:3.11-slim

WORKDIR /app

# Install minimal OS utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Start script: seed initial data, ingest knowledge base, and launch FastAPI
CMD ["sh", "-c", "python scripts/seed.py && python scripts/ingest.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
