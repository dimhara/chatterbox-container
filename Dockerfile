# ==========================================
# STAGE 1: Builder
# ==========================================
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/root/.cache/huggingface"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Clone and remove git history to save space
RUN git clone https://github.com/resemble-ai/chatterbox.git . && \
    rm -rf .git

# Install with pip cache purge to save ~2.5GB of build space
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . && \
    pip cache purge

COPY builder.py .

# Run the builder (CPU-patched)
RUN python builder.py

# ==========================================
# STAGE 2: Runtime
# ==========================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    HF_HOME="/root/.cache/huggingface" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Only runtime libs
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy artifacts from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=builder /app /app

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 7860

CMD ["/app/start.sh"]
