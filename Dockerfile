# ==========================================
# STAGE 1: Builder (Download Models + spaCy assets)
# ==========================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/root/.cache/huggingface" \
    PKUSEG_CACHE="/root/.pkuseg" \
    SPACY_MODELS="/root/.cache/spacy"

WORKDIR /app

# Install build deps + git + wget (for spaCy models)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libsndfile1 \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create and activate venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Clone Chatterbox source
RUN git clone https://github.com/resemble-ai/chatterbox.git . && \
    rm -rf .git

# Install package + deps (from source)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . && \
    pip cache purge

# Pre-download spaCy Chinese tokenizer assets
# This prevents runtime downloads of spacy_ontonotes.zip
RUN mkdir -p ${PKUSEG_CACHE} && \
    wget -O ${PKUSEG_CACHE}/spacy_ontonotes.zip https://github.com/explosion/spacy-pkuseg/releases/download/v0.0.26/spacy_ontonotes.zip

# Copy and run model downloader (CPU-patched)
COPY builder.py .
RUN python builder.py


# ==========================================
# STAGE 2: Runtime (Minimal + Serverless)
# ==========================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/root/.cache/huggingface" \
    PKUSEG_CACHE="/root/.pkuseg" \
    SPACY_MODELS="/root/.cache/spacy" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install ONLY runtime deps
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps for serverless handler
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir runpod cryptography

# Copy from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=builder /root/.pkuseg /root/.pkuseg
COPY --from=builder /app /app

# Copy serverless handler
COPY rp_handler.py /app/rp_handler.py

EXPOSE 22

# Default command (for pod mode — serverless ignores CMD) and just runs rp_handler..py
CMD ["/app/start.sh"]
