#!/bin/bash
set -e

# 1. Download models (if not cached)
/app/download_models.sh

# 2. Start the Python Handler
echo "--- 🚀 Starting Serverless Handler ---"
exec python -u rp_handler.py
