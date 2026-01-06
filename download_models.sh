#!/bin/bash
set -e

echo "--- 📥 Starting Efficient Model Download ---"

# Ensure HF Transfer is enabled for speed
export HF_HUB_ENABLE_HF_TRANSFER=1

# Download specific files to the default cache (~/.cache/huggingface)
# This allows the Python library to find them automatically via from_pretrained()
huggingface-cli download ResembleAI/chatterbox \
    --include \
    "ve.pt" \
    "t3_mtl23ls_v2.safetensors" \
    "s3gen.pt" \
    "grapheme_mtl_merged_expanded_v1.json" \
    "conds.pt" \
    "Cangjie5_TC.json" \
    "s3gen.safetensors" \
    "ve.safetensors" \
    "t3_cfg.safetensors" \
    "tokenizer.json"

echo "--- ✅ Model Download Complete ---"
