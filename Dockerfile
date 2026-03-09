FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by faiss-cpu and scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Copy data and pre-trained models (baked into image — no re-training needed)
COPY data/ ./data/
COPY models/ ./models/

# Environment defaults (overridden at runtime via ECS task definition / App Runner env vars)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
