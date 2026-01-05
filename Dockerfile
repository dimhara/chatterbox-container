# ==========================================
# STAGE 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/root/.cache/huggingface" \
    UV_PROJECT_ENVIRONMENT="/opt/venv"

WORKDIR /app

# Install uv and system build deps
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y \
    git build-essential libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment via uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 1. Install PyTorch CPU first (Critical for keeping image size down)
RUN uv pip install \
    --index-url https://download.pytorch.org/whl/cpu \
    torch torchaudio

# 2. Clone and install Chatterbox
RUN git clone https://github.com/resemble-ai/chatterbox.git . && \
    uv pip install .

# 3. Copy and run model downloader
# The builder.py script uses the patched torch.load to ensure CPU safety
COPY builder.py .
RUN python builder.py

# ==========================================
# STAGE 2: Runtime
# ==========================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/root/.cache/huggingface" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install ONLY minimal runtime deps (no git/build-essential)
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the venv and cached models from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=builder /root/.pkuseg /root/.pkuseg
COPY --from=builder /app /app

# Install serverless support into the venv using uv (fast)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
RUN uv pip install runpod cryptography

# Copy scripts
COPY rp_handler.py /app/rp_handler.py
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Fix: Ensure we run the handler, not just sleep forever
# Using -u for unbuffered logs in RunPod
CMD ["python", "-u", "rp_handler.py"]
