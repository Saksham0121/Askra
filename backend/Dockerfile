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

# Install dependencies into a wheels/user cache directory (using CPU index for lean PyTorch install)
RUN pip install --no-cache-dir --user --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt


# ==============================================================================
# Stage 2: Minimal Runtime Stage
# ==============================================================================
FROM python:3.12-slim AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:${PATH}" \
    APP_ENV=production \
    UPLOAD_DIR=/app/uploads \
    FAISS_INDEX_DIR=/app/faiss_store \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1

# Install runtime C libraries required by FAISS & PyMuPDF (e.g. OpenMP / libgomp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application source code and pipeline
COPY app ./app
COPY pipeline ./pipeline

# Create storage directories with permissions
RUN mkdir -p /app/uploads /app/faiss_store

# Expose FastAPI backend port
EXPOSE 8000

# Health check to ensure API responsiveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI application with single worker & dynamic PORT for free tier hosting (Render/Koyeb)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
