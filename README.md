# Chatterbox Serverless Container

This repository contains a containerized deployment for [Resemble AI's Chatterbox](https://github.com/resemble-ai/chatterbox), optimized for **RunPod Serverless** and **Interactive GPU Pods**. 

It includes logic for fast model downloading, CPU/GPU compatibility patching, and Fernet-based payload encryption.

## 📂 Directory Structure

*   **`Dockerfile`**: Multi-stage build that patches Chatterbox and prepares the runtime.
*   **`rp_handler.py`**: The serverless entry point handling TTS and Voice Conversion (VC) requests.
*   **`start_serverless.sh`**: The default container command. Downloads models and starts the handler.
*   **`start.sh`**: Entry point for Interactive Pods. Sets up SSH and keeps the pod running.
*   **`setup.sh`**: Script for setting up a local development environment (mirrors Docker logic).
*   **`download_models.sh`**: centralized script using `huggingface-cli` for high-speed model caching.

---

## 1. RunPod Serverless Deployment (Production)

This is the default mode of the container. It is designed to scale to zero and load models quickly upon a cold start.

### Prerequisites
1.  Build and push the Docker image to a registry (GHCR or Docker Hub).
2.  Create a **Serverless Endpoint** on RunPod.

### Configuration
*   **Container Image**: `ghcr.io/dimhara/chatterbox:latest`
*   **Container Start Command**: Leave empty (Defaults to `/app/start_serverless.sh`).
*   **Environment Variables**:
    *   `ENCRYPTION_KEY`: **(Required)** A Fernet 32-byte URL-safe base64-encoded key.
* **MODEL**: Supports the value "ResembleAI/chatterbox" for fast HF caching

### Generating an Encryption Key
The handler requires encrypted payloads. Generate a key using Python:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# Output example: 7-Sn... (Copy this to RunPod env vars)
```

### API Usage
The handler accepts inputs for **TTS** (Text-to-Speech) and **VC** (Voice Conversion).

#### Input Payload Format
```json
{
  "input": {
    "mode": "tts", 
    "encrypted_text": "<encrypted_string>",
    "language_id": "en",
    "encrypted_reference_audio_b64": "<optional_encrypted_audio>"
  }
}
```

---

## 2. RunPod Pod Deployment (Interactive)

Just change the start command to `/start.sh`

---

## 3. Local Development (Testing)

You can replicate the exact environment used inside the Docker container on your local machine (Linux/Mac) without using Docker.

### Setup
The `setup.sh` script handles everything: installing `uv`, creating a virtual environment, patching the Chatterbox source code for CPU compatibility, and downloading models.

```bash
# 1. Make scripts executable
chmod +x setup.sh download_models.sh

# 2. Run setup
./setup.sh
```

### Running Tests
Once setup is complete, activate the environment and run the debug script:

```bash
source .venv/bin/activate
python debug_local.py
```

This will run a full inference test on your local CPU to ensure the model logic and encryption are working correctly before deployment.

