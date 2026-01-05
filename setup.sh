#!/bin/bash

# Exit on error
set -e

# 1. Install uv (assuming pip is available)
echo "--- Installing uv ---"
pip install uv

# Find the installed uv executable.
# It's usually in ~/.local/bin for user installs.
UV_CMD=$(which uv)
if [ -z "$UV_CMD" ]; then
  echo "Could not find 'uv' after installation. Trying a common path."
  UV_CMD="$HOME/.local/bin/uv"
fi

if [ ! -f "$UV_CMD" ]; then
  echo "Failed to locate uv executable. Exiting."
  exit 1
fi
echo "Found uv executable at: $UV_CMD"


# 2. Install system dependencies
echo "--- Installing system dependencies ---"
sudo apt-get update && sudo apt-get install -y \
    git \
    build-essential \
    libsndfile1 \
    ffmpeg

# 3. Create a virtual environment
echo "--- Creating virtual environment ---"
# Ensure the target directory is clean and we have permissions
sudo rm -rf /opt/venv
sudo mkdir -p /opt/venv
sudo chown $USER:$USER /opt/venv
$UV_CMD venv /opt/venv

VENV_PYTHON="/opt/venv/bin/python"

# 4. Install PyTorch CPU
echo "--- Installing PyTorch CPU ---"
$UV_CMD pip install \
    --python $VENV_PYTHON \
    --index-url https://download.pytorch.org/whl/cpu \
    torch \
    torchaudio

# 5. Clone and install Chatterbox
echo "--- Installing Chatterbox ---"
# Clone to a temporary directory
TMP_DIR=$(mktemp -d)
git clone https://github.com/resemble-ai/chatterbox.git $TMP_DIR/chatterbox

# Patch chatterbox's numpy dependency for Python 3.12+
echo "--- Patching Chatterbox for Python 3.12+ compatibility ---"
sed -i 's/numpy>=1.24.0,<1.26.0/numpy>=1.26.0/' $TMP_DIR/chatterbox/pyproject.toml

$UV_CMD pip install \
    --python $VENV_PYTHON \
    $TMP_DIR/chatterbox

# 6. Install other Python dependencies
echo "--- Installing other Python dependencies ---"
$UV_CMD pip install \
    --python $VENV_PYTHON \
    runpod cryptography

# 7. Patch chatterbox after installation
echo "--- Patching Chatterbox for CPU loading ---"
SITE_PACKAGES=$($VENV_PYTHON -c "import site; print(site.getsitepackages()[0])")
TTS_MODEL_PATH="$SITE_PACKAGES/chatterbox/mtl_tts.py"
VC_MODEL_PATH="$SITE_PACKAGES/chatterbox/vc.py"

# Patch for the TTS model
sed -i 's/torch\.load(ckpt_dir \/ "s3gen\.pt", weights_only=True)/torch.load(ckpt_dir \/ "s3gen.pt", map_location=device, weights_only=True)/' $TTS_MODEL_PATH

# Proactive patch for the VC model
sed -i 's/torch\.load(ckpt_dir \/ "vc_model\.pt")/torch.load(ckpt_dir \/ "vc_model.pt", map_location=device)/' $VC_MODEL_PATH

# 8. Clean up
echo "--- Cleaning up ---"
rm -rf $TMP_DIR

echo "--- Setup complete ---"
