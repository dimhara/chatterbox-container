# AGENTS.md

This file provides context for AI agents working on the Chatterbox Container project.

## ⚠️ Critical Rules for Agent Execution

1.  **Hardware / Device:**
    - When running scripts locally (e.g., `debug_local.py`), **ALWAYS** use `--device cpu`.
    - Do not attempt to use CUDA or MPS locally; the environment is standard CPU Linux/Mac.

2.  **Audio Formats:**
    - When testing in-memory encoding, **ALWAYS** use `--format ogg`.
    - Do NOT use `--format opus` directly. `torchaudio` requires the "ogg" container to hold Opus data in memory buffers.

3.  **Privacy & Security:**
    - The code should log only the *length* of request payload, not the actual content.

## Project Structure & Commands

- **Python Version:** 3.11
- **Dependency Management:** Uses `uv` (faster pip alternative).
    - Install deps: `./setup.sh`
- **Testing:**
    - **TTS Test:** `python debug_local.py --device cpu --format ogg`
    - **VC Test:** `python debug_local.py --device cpu --format ogg --test-vc`
- **Deployment:**
    - The main handler is `rp_handler.py`.
    - It uses Fernet encryption for all inputs/outputs.
    - Docker build: `docker build -t chatterbox .`

## Code Style
- Use `snake_case` for Python.
- When modifying `rp_handler.py`, ensure `torchaudio.set_audio_backend("ffmpeg")` is preserved.

