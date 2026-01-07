import runpod
import os
import io
import torch
import torchaudio
from cryptography.fernet import Fernet
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.vc import ChatterboxVC

# --- BACKEND CONFIGURATION ---
# Force torchaudio to use ffmpeg for broad format support (AAC, MP3, etc.)
try:
    if "ffmpeg" in torchaudio.list_audio_backends():
        torchaudio.set_audio_backend("ffmpeg")
except Exception as e:
    print(f"Warning: Could not set torchaudio backend: {e}")

# --- ENCRYPTION SETUP ---
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable is required")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# --- DEVICE & MODEL INITIALIZATION ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading models on {DEVICE}...")

# Load both models outside the handler for warm-start performance
TTS_MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE)
VC_MODEL = ChatterboxVC.from_pretrained(DEVICE)
print("Chatterbox TTS and VC models loaded successfully.")


def decrypt_data(encrypted_str: str) -> bytes:
    return cipher_suite.decrypt(encrypted_str.encode())


def encrypt_data(raw_bytes: bytes) -> str:
    return cipher_suite.encrypt(raw_bytes).decode()


def load_audio_from_encrypted(encrypted_b64: str, target_sr: int = None):
    """
    Decrypts base64 audio and loads it via torchaudio.
    Handles AAC, MP3, WAV, etc., via FFmpeg backend.
    """
    decrypted_bytes = decrypt_data(encrypted_b64)
    audio_buffer = io.BytesIO(decrypted_bytes)
    
    # torchaudio.load detects  the format (AAC, WAV, etc) automatically
    wav, sr = torchaudio.load(audio_buffer)
    
    if target_sr and sr != target_sr:
        wav = torchaudio.functional.resample(wav, sr, target_sr)
        sr = target_sr
    
    # Use  a file-like object.
    # We provide an in-memory WAV buffer for internal compatibility.
    temp_buffer = io.BytesIO()
    torchaudio.save(temp_buffer, wav, sr, format="wav")
    temp_buffer.seek(0)
    return temp_buffer, sr


def tts_handler(job_input):
    """Handle Multilingual TTS requests with ogg output."""
    encrypted_text = job_input.get("encrypted_text")
    language_id = job_input.get("language_id")
    encrypted_ref_b64 = job_input.get("encrypted_reference_audio_b64")

    if not encrypted_text or not language_id:
        return {"error": "TTS mode requires 'encrypted_text' and 'language_id'"}

    try:
        # Decrypt text but DO NOT log the plaintext for privacy
        text = decrypt_data(encrypted_text).decode("utf-8")
        print(f"TTS: Generating audio (length: {len(text)} chars) in language: {language_id}")
    except Exception as e:
        return {"error": "Failed to decrypt text", "details": str(e)}

    audio_prompt_path = None
    temp_ref = None
    if encrypted_ref_b64:
        try:
            # TTS Prompt usually prefers 24kHz
            temp_ref, _ = load_audio_from_encrypted(encrypted_ref_b64, target_sr=24000)
            audio_prompt_path = temp_ref
        except Exception as e:
            return {"error": "Failed to process reference audio (Check if format is supported)", "details": str(e)}

    try:
        wav = TTS_MODEL.generate(
            text=text,
            language_id=language_id,
            audio_prompt_path=audio_prompt_path,
            exaggeration=0.5,
            cfg_weight=0.5,
            temperature=0.8
        )
        
        # Save output as ogg for bandwidth efficiency
        audio_buffer = io.BytesIO()
        torchaudio.save(audio_buffer, wav, TTS_MODEL.sr, format="ogg")
        encrypted_audio = encrypt_data(audio_buffer.getvalue())
        
        return {"status": "success", "format": "ogg", "encrypted_audio": encrypted_audio}

    except Exception as e:
        return {"error": "TTS generation failed", "details": str(e)}
    finally:
        if temp_ref: temp_ref.close()


def vc_handler(job_input):
    """Handle Voice Conversion requests with ogg output."""
    encrypted_source = job_input.get("encrypted_source_audio")
    encrypted_target = job_input.get("encrypted_target_voice")

    if not encrypted_source or not encrypted_target:
        return {"error": "VC mode requires 'encrypted_source_audio' and 'encrypted_target_voice'"}

    source_buffer = target_buffer = None
    try:
        # Load source (Resample to VC's 16kHz) and target (Identity)
        source_buffer, _ = load_audio_from_encrypted(encrypted_source, target_sr=16000)
        target_buffer, _ = load_audio_from_encrypted(encrypted_target)
        
        print("VC: Performing voice conversion...")
        wav = VC_MODEL.generate(
            audio=source_buffer,
            target_voice_path=target_buffer
        )
        
        # Save output as ogg
        audio_buffer = io.BytesIO()
        torchaudio.save(audio_buffer, wav, VC_MODEL.sr, format="ogg")
        encrypted_audio = encrypt_data(audio_buffer.getvalue())
        
        return {"status": "success", "format": "ogg", "encrypted_audio": encrypted_audio}
        
    except Exception as e:
        return {"error": "Voice conversion failed", "details": str(e)}
    finally:
        if source_buffer: source_buffer.close()
        if target_buffer: target_buffer.close()


def handler(job):
    """Main routing entry point."""
    job_input = job.get("input", {})
    mode = job_input.get("mode", "tts").lower()

    if mode == "tts":
        return tts_handler(job_input)
    elif mode == "vc":
        return vc_handler(job_input)
    else:
        return {
            "error": f"Invalid mode: {mode}",
            "available_modes": ["tts", "vc"]
        }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})

