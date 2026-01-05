#!/bin/bash
set -e

echo "--- 🛠️  Local Setup Started ---"

# 1. Install uv
pip install uv
UV_CMD=$(which uv) || UV_CMD="$HOME/.local/bin/uv"

# 2. Create venv
echo "--- Creating virtual environment ---"
rm -rf .venv
$UV_CMD venv .venv
VENV_PYTHON=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

# 3. Install PyTorch CPU & HF Tools
echo "--- Installing Dependencies ---"
$UV_CMD pip install --python $VENV_PYTHON \
    --index-url https://download.pytorch.org/whl/cpu \
    torch torchaudio
    
$UV_CMD pip install --python $VENV_PYTHON \
    "huggingface_hub[cli]" hf_transfer runpod cryptography

# 4. Clone & Patch Chatterbox (Matching Dockerfile logic)
echo "--- Cloning and Patching Chatterbox ---"
if [ -d "chatterbox" ]; then rm -rf chatterbox; fi
git clone https://github.com/resemble-ai/chatterbox.git

# Patch 1: Numpy constraint
sed -i 's/numpy>=1.24.0,<1.26.0/numpy>=1.26.0/' chatterbox/pyproject.toml

# Patch 2: CPU Map Location (Note: Local path is chatterbox/src/..., not /app/src/...)
sed -i 's/torch\.load(ckpt_dir \/ "ve\.pt", weights_only=True)/torch.load(ckpt_dir \/ "ve.pt", map_location=device, weights_only=True)/' chatterbox/src/chatterbox/mtl_tts.py
sed -i 's/torch\.load(ckpt_dir \/ "s3gen\.pt", weights_only=True)/torch.load(ckpt_dir \/ "s3gen.pt", map_location=device, weights_only=True)/' chatterbox/src/chatterbox/mtl_tts.py
sed -i 's/torch\.load(ckpt_dir \/ "vc_model\.pt")/torch.load(ckpt_dir \/ "vc_model.pt", map_location=device)/' chatterbox/src/chatterbox/vc.py

# 5. Install Chatterbox
$UV_CMD pip install --python $VENV_PYTHON chatterbox/

# 6. Cache PKUSEG
$VENV_PYTHON -c "import spacy_pkuseg; spacy_pkuseg.pkuseg()"

# 7. Download Models using the shared script
echo "--- Downloading Models ---"
# We need to activate the venv context for the script to find 'huggingface-cli'
source .venv/bin/activate
./download_models.sh

echo "--- ✅ Setup Complete. Run 'source .venv/bin/activate' then 'python debug_local.py' ---"
