# ==========================================
# STAGE 1: Builder (Heavy lifting)
# ==========================================
FROM python:3.11-slim as builder

# Set env to ensure downloads go to the right place
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/root/.cache/huggingface"

WORKDIR /app

# Install build dependencies (git, compilers for python libs, audio libs for caching script)
# We need libsndfile1/ffmpeg here because builder.py imports the library to cache models
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Clone the repository
# We remove the .git directory immediately to save space (it can be large)
RUN git clone https://github.com/resemble-ai/chatterbox.git . && \
    rm -rf .git

# Install dependencies into the virtual environment
# We use standard install (.) instead of editable (-e) for cleaner packaging
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy the builder script (CPU patched version)
COPY builder.py .

# Run the builder to download models into /root/.cache/huggingface
# This uses the CPU-patched logic from builder.py
RUN python builder.py

# ==========================================
# STAGE 2: Runtime (Slim and clean)
# ==========================================
FROM python:3.11-slim

# Runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    HF_HOME="/root/.cache/huggingface" \
    # Add the virtual environment to the path
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install ONLY runtime libraries (libsndfile/ffmpeg). 
# git and build-essential are NOT installed here.
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the cached models from the builder stage
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

# Copy the application code from the builder stage
COPY --from=builder /app /app

# Copy the start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE 7860

# Entrypoint
CMD ["/app/start.sh"]
