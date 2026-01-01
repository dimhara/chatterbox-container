import runpod
import os
import io
import torch
import torchaudio
from cryptography.fernet import Fernet
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.vc import ChatterboxVC

# --- CONFIGURATION ---
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable is required")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading models on {DEVICE}...")

# Load both models
TTS_MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE)
VC_MODEL = ChatterboxVC.from_pretrained(DEVICE)
print("Both TTS and VC models loaded successfully.")


def decrypt_data(encrypted_str: str) -> bytes:
    return cipher_suite.decrypt(encrypted_str.encode())


def encrypt_data(raw_bytes: bytes) -> str:
    return cipher_suite.encrypt(raw_bytes).decode()


def load_audio_from_encrypted(encrypted_b64: str, target_sr: int = None):
    """Helper: decrypt and load audio into tensor, optionally resample."""
    decrypted_bytes = decrypt_data(encrypted_b64)
    audio_buffer = io.BytesIO(decrypted_bytes)
    wav, sr = torchaudio.load(audio_buffer)
    
    if target_sr and sr != target_sr:
        wav = torchaudio.functional.resample(wav, sr, target_sr)
        sr = target_sr
    
    # Return in-memory file-like object (required by Chatterbox APIs)
    temp_buffer = io.BytesIO()
    torchaudio.save(temp_buffer, wav, sr, format="wav")
    temp_buffer.seek(0)
    return temp_buffer, sr


def tts_handler(job_input):
    """Handle Multilingual TTS requests."""
    encrypted_text = job_input.get("encrypted_text")
    language_id = job_input.get("language_id")
    encrypted_ref_b64 = job_input.get("encrypted_reference_audio_b64")

    if not encrypted_text or not language_id:
        return {"error": "TTS mode requires 'encrypted_text' and 'language_id'"}

    try:
        text = decrypt_data(encrypted_text).decode("utf-8")
        print(f"TTS: Generating '{text[:50]}...' in language: {language_id}")
    except Exception as e:
        return {"error": "Failed to decrypt text", "details": str(e)}

    # Optional reference audio
    audio_prompt_path = None
    temp_ref = None
    if encrypted_ref_b64:
        try:
            temp_ref, _ = load_audio_from_encrypted(encrypted_ref_b64, target_sr=24000)
            audio_prompt_path = temp_ref
        except Exception as e:
            return {"error": "Failed to process reference audio", "details": str(e)}

    # Generate
    try:
        if audio_prompt_path:
            wav = TTS_MODEL.generate(
                text=text,
                language_id=language_id,
                audio_prompt_path=audio_prompt_path,
                exaggeration=0.5,
                cfg_weight=0.5,
                temperature=0.8
            )
        else:
            wav = TTS_MODEL.generate(
                text=text,
                language_id=language_id,
                exaggeration=0.5,
                cfg_weight=0.5,
                temperature=0.8
            )
    except Exception as e:
        if temp_ref: temp_ref.close()
        return {"error": "TTS generation failed", "details": str(e)}
    finally:
        if temp_ref: temp_ref.close()

    # Encrypt result
    audio_buffer = io.BytesIO()
    torchaudio.save(audio_buffer, wav, TTS_MODEL.sr, format="wav")
    encrypted_audio = encrypt_data(audio_buffer.getvalue())
    
    return {"status": "success", "encrypted_audio": encrypted_audio}


def vc_handler(job_input):
    """Handle Voice Conversion requests."""
    encrypted_source = job_input.get("encrypted_source_audio")
    encrypted_target = job_input.get("encrypted_target_voice")

    if not encrypted_source or not encrypted_target:
        return {"error": "VC mode requires 'encrypted_source_audio' and 'encrypted_target_voice'"}

    source_buffer = target_buffer = None
    try:
        # Load source audio (resample to VC model's expected rate: 16kHz)
        source_buffer, _ = load_audio_from_encrypted(encrypted_source, target_sr=16000)
        
        # Load target voice (no resampling needed - VC handles internally)
        target_buffer, _ = load_audio_from_encrypted(encrypted_target)
        
        print("VC: Converting voice...")
        wav = VC_MODEL.generate(
            audio=source_buffer,
            target_voice_path=target_buffer
        )
        
    except Exception as e:
        return {"error": "Voice conversion failed", "details": str(e)}
    finally:
        if source_buffer: source_buffer.close()
        if target_buffer: target_buffer.close()

    # Encrypt result
    audio_buffer = io.BytesIO()
    torchaudio.save(audio_buffer, wav, VC_MODEL.sr, format="wav")
    encrypted_audio = encrypt_data(audio_buffer.getvalue())
    
    return {"status": "success", "encrypted_audio": encrypted_audio}


def handler(job):
    """Unified handler routing based on 'mode' field."""
    job_input = job["input"]
    mode = job_input.get("mode", "tts").lower()  # default to TTS

    if mode == "tts":
        return tts_handler(job_input)
    elif mode == "vc":
        return vc_handler(job_input)
    else:
        return {
            "error": "Invalid mode. Use 'tts' or 'vc'",
            "available_modes": ["tts", "vc"]
        }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
