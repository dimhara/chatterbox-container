ARG RUNTIME=cpu

# ==========================================
# STAGE 1: Builder
# ==========================================
FROM python:3.11-slim AS builder
ARG RUNTIME

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT="/opt/venv"

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y git build-essential libsndfile1 ffmpeg && rm -rf /var/lib/apt/lists/*
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Torch
RUN if [ "$RUNTIME" = "cpu" ]; then \
        uv pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio; \
    else \
        uv pip install torch torchaudio; \
    fi && uv cache clean

# Install Chatterbox
RUN git clone https://github.com/resemble-ai/chatterbox.git .

# --- PATCHING SECTION ---
RUN sed -i 's/numpy>=1.24.0,<1.26.0/numpy>=1.26.0/' pyproject.toml
RUN sed -i 's/torch\.load(ckpt_dir \/ "ve\.pt", weights_only=True)/torch.load(ckpt_dir \/ "ve.pt", map_location=device, weights_only=True)/' src/chatterbox/mtl_tts.py && \
    sed -i 's/torch\.load(ckpt_dir \/ "s3gen\.pt", weights_only=True)/torch.load(ckpt_dir \/ "s3gen.pt", map_location=device, weights_only=True)/' src/chatterbox/mtl_tts.py && \
    sed -i 's/torch\.load(ckpt_dir \/ "vc_model\.pt")/torch.load(ckpt_dir \/ "vc_model.pt", map_location=device)/' src/chatterbox/vc.py
# Disable Watermarker
RUN sed -i 's/self\.watermarker = perth\.PerthImplicitWatermarker()/self.watermarker = None/' src/chatterbox/mtl_tts.py src/chatterbox/tts.py src/chatterbox/vc.py src/chatterbox/tts_turbo.py
RUN sed -i 's/watermarked_wav = self\.watermarker\.apply_watermark(wav, sample_rate=self\.sr)/watermarked_wav = wav/' src/chatterbox/mtl_tts.py src/chatterbox/tts.py src/chatterbox/vc.py src/chatterbox/tts_turbo.py

RUN uv pip install . && uv cache clean
RUN python -c "import spacy_pkuseg; spacy_pkuseg.pkuseg()"

# ==========================================
# STAGE 2: Runtime
# ==========================================
FROM python:3.11-slim
ARG RUNTIME

ENV PYTHONUNBUFFERED=1 \
    HF_HOME="/root/.cache/huggingface" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    libopus0 \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.pkuseg /root/.pkuseg
COPY --from=builder /app /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
RUN uv pip install runpod cryptography "huggingface_hub[cli]" hf_transfer && uv cache clean

COPY rp_handler.py /app/rp_handler.py
COPY download_models.sh /app/download_models.sh
COPY start_serverless.sh /app/start_serverless.sh
COPY start.sh /start.sh

# --- NEW: Copy the debug script ---
COPY debug_local.py /app/debug_local.py

RUN chmod +x /app/download_models.sh /app/start_serverless.sh /start.sh

CMD ["/app/start_serverless.sh"]
