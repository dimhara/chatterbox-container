#!/bin/bash
set -e

# Configuration
RUNPOD_CACHE_ROOT="/runpod-volume/huggingface-cache"
MODEL_ID="ResembleAI/chatterbox"
# Convert "Org/Repo" to "models--Org--Repo" to match HF/RunPod structure
MODEL_DIR_NAME="models--${MODEL_ID//\//--}"
FULL_MODEL_PATH="${RUNPOD_CACHE_ROOT}/hub/${MODEL_DIR_NAME}"

echo "--- 🚀 Serverless Start ---"

# 1. Check if RunPod Cached Model is available
if [ -d "$FULL_MODEL_PATH" ]; then
    echo "--- ✅ RunPod Cache Detected: Linking to $MODEL_ID ---"
    
    # Point HF_HOME to the RunPod volume.
    # The Chatterbox library (via huggingface_hub) will automatically find the files here.
    export HF_HOME="$RUNPOD_CACHE_ROOT"
    
else
    echo "--- ⚠️  RunPod Cache NOT found at $FULL_MODEL_PATH ---"
    echo "--- 📥 Falling back to internal download logic... ---"
    
    # Run the standard download script (downloads to /root/.cache/huggingface)
    /app/download_models.sh
fi

# 2. Start the Python Handler
echo "--- 🎬 Starting Handler ---"
exec python -u rp_handler.py
