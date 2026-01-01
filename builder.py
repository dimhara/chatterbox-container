import torch
import os

# --- MONKEYPATCH ---
# Force all torch.load calls to use CPU mapping.
# This prevents the "Attempting to deserialize object on a CUDA device" error
# during the GitHub Action build process.
original_load = torch.load

def patched_load(*args, **kwargs):
    kwargs['map_location'] = torch.device('cpu')
    return original_load(*args, **kwargs)

torch.load = patched_load
# -------------------

from chatterbox.tts import ChatterboxTTS
# Turbo import removed to avoid token error
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.vc import ChatterboxVC

def download_models():
    print("--- Starting Model Caching for Chatterbox ---")
    
    device = "cpu"
    
    print("Downloading Chatterbox TTS (Standard)...")
    try:
        ChatterboxTTS.from_pretrained(device=device)
        print("Standard TTS cached.")
    except Exception as e:
        print(f"Error caching Standard TTS: {e}")

    # Turbo removed as requested

    print("Downloading Chatterbox TTS (Multilingual)...")
    try:
        ChatterboxMultilingualTTS.from_pretrained(device=device)
        print("Multilingual TTS cached.")
    except Exception as e:
        print(f"Error caching Multilingual TTS: {e}")

    print("Downloading Chatterbox VC...")
    try:
        ChatterboxVC.from_pretrained(device=device)
        print("Voice Conversion cached.")
    except Exception as e:
        print(f"Error caching VC: {e}")
        
    print("--- Model Caching Complete ---")

if __name__ == "__main__":
    download_models()
