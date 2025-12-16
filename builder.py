import torch
import os
from chatterbox.tts import ChatterboxTTS
from chatterbox.tts_turbo import ChatterboxTurboTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.vc import ChatterboxVC

def download_models():
    print("--- Starting Model Caching for Chatterbox ---")
    
    # We use CPU here just to trigger the download logic. 
    # The weights will be saved to HF_HOME.
    device = "cpu"
    
    print("Downloading Chatterbox TTS (Standard)...")
    try:
        ChatterboxTTS.from_pretrained(device=device)
        print("Standard TTS cached.")
    except Exception as e:
        print(f"Error caching Standard TTS: {e}")

    print("Downloading Chatterbox TTS (Turbo)...")
    try:
        ChatterboxTurboTTS.from_pretrained(device=device)
        print("Turbo TTS cached.")
    except Exception as e:
        print(f"Error caching Turbo TTS: {e}")

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
