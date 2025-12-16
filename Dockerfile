# Use Python 3.11 as recommended in the README
FROM python:3.11-slim

# Set environment variables
# GRADIO_SERVER_NAME allows external access
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME="0.0.0.0" \
    GRADIO_SERVER_PORT=7860 \
    HF_HOME="/root/.cache/huggingface"

# Install system dependencies
# libsndfile1 is required for librosa
# ffmpeg is required for general audio processing
# git is required to clone the repo
# build-essential for compiling C extensions if needed
RUN apt-get update && apt-get install -y \
    git \
    libsndfile1 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Clone the repository
RUN git clone https://github.com/resemble-ai/chatterbox.git .

# Install Python dependencies
# We install in editable mode as suggested, though standard install works too.
# The pyproject.toml specifies torch==2.6.0
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy the builder script to pre-download models
COPY builder.py /app/builder.py

# Run the builder script to cache models into the Docker image layer
# This prevents downloading 2GB+ of models every time the pod starts
RUN python builder.py

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose the Gradio port
EXPOSE 7860

# Entrypoint
CMD ["/app/start.sh"]
