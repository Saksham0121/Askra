# ==============================================================================
# Stage 1: Build & Dependencies Stage
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build dependencies required for compiling C/C++ extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies into a user cache directory (lean installation, no heavy PyTorch)
RUN pip install --no-cache-dir --user -r requirements.txt


# ==============================================================================
# Stage 2: Minimal Runtime Stage
# ==============================================================================
FROM python:3.12-slim AS runtime

# Set environment variables for production & memory optimization (fits within 512MB RAM)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:${PATH}" \
    APP_ENV=production \
    UPLOAD_DIR=/app/uploads \
    FAISS_INDEX_DIR=/app/faiss_store \
    MODEL_CACHE_DIR=/app/models_cache \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    ONNXRUNTIME_NUM_THREADS=1

# Install runtime C libraries required by FAISS & PyMuPDF (OpenMP / libgomp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Create storage directories
RUN mkdir -p /app/uploads /app/faiss_store /app/models_cache

# Pre-download lightweight ONNX models into the image during build
# This guarantees 0s download cold-start and zero memory spikes at runtime on Render
RUN python3 -c "\
from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/app/models_cache'); \
from flashrank import Ranker; Ranker(model_name='ms-marco-TinyBERT-L-2-v2', cache_dir='/app/models_cache')"

# Copy application source code and pipeline
COPY app ./app
COPY pipeline ./pipeline

# Expose FastAPI backend port
EXPOSE 8000

# Health check to ensure API responsiveness with dynamic PORT support
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start FastAPI application with single worker & dynamic PORT for free tier hosting (Render/Koyeb)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
