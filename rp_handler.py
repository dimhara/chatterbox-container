import runpod
import os
import io
import torch
import torchaudio
from cryptography.fernet import Fernet
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

# --- CONFIGURATION ---
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable is required")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# --- MODEL LOADING (ONCE PER CONTAINER) ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading ChatterboxMultilingualTTS on {DEVICE}...")
MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE)
print("Model loaded.")


def decrypt_data(encrypted_str: str) -> bytes:
    return cipher_suite.decrypt(encrypted_str.encode())


def encrypt_data(raw_bytes: bytes) -> str:
    return cipher_suite.encrypt(raw_bytes).decode()


def load_reference_audio(encrypted_ref_b64: str):
    """Decrypt and load reference audio into a temp-free tensor."""
    decrypted_bytes = decrypt_data(encrypted_ref_b64)
    audio_buffer = io.BytesIO(decrypted_bytes)
    wav, sr = torchaudio.load(audio_buffer)
    # Resample to 24kHz if needed (Chatterbox expects 24kHz for reference)
    if sr != 24000:
        wav = torchaudio.functional.resample(wav, sr, 24000)
    # Save to in-memory buffer for file-like path compatibility
    temp_buffer = io.BytesIO()
    torchaudio.save(temp_buffer, wav, 24000, format="wav")
    temp_buffer.seek(0)
    return temp_buffer


def handler(job):
    job_input = job["input"]

    # --- 1. VALIDATE & DECRYPT INPUTS ---
    encrypted_text = job_input.get("encrypted_text")
    language_id = job_input.get("language_id")
    encrypted_ref_b64 = job_input.get("encrypted_reference_audio_b64")  # optional

    if not encrypted_text:
        return {"error": "'encrypted_text' is required"}
    if not language_id:
        return {"error": "'language_id' is required"}

    try:
        text = decrypt_data(encrypted_text).decode("utf-8")
        print(f"Text decrypted. Generating in language: {language_id}")
    except Exception as e:
        return {"error": "Failed to decrypt text", "details": str(e)}

    # --- 2. PREPARE REFERENCE (IF PROVIDED) ---
    audio_prompt_path = None
    temp_ref_file = None
    if encrypted_ref_b64:
        try:
            temp_ref_file = load_reference_audio(encrypted_ref_b64)
            audio_prompt_path = temp_ref_file
        except Exception as e:
            return {"error": "Failed to process reference audio", "details": str(e)}

    # --- 3. GENERATE AUDIO ---
    try:
        if audio_prompt_path:
            wav = MODEL.generate(
                text=text,
                language_id=language_id,
                audio_prompt_path=audio_prompt_path,
                exaggeration=0.5,
                cfg_weight=0.5,
                temperature=0.8
            )
        else:
            # Use built-in default voice for the language
            wav = MODEL.generate(
                text=text,
                language_id=language_id,
                exaggeration=0.5,
                cfg_weight=0.5,
                temperature=0.8
            )
    except Exception as e:
        return {"error": "TTS generation failed", "details": str(e)}
    finally:
        # Ensure no reference buffer leaks
        if temp_ref_file:
            temp_ref_file.close()

    # --- 4. ENCODE & ENCRYPT AUDIO IN-MEMORY ---
    try:
        audio_buffer = io.BytesIO()
        torchaudio.save(audio_buffer, wav, MODEL.sr, format="wav")
        audio_bytes = audio_buffer.getvalue()
        encrypted_audio = encrypt_data(audio_bytes)
    except Exception as e:
        return {"error": "Failed to encode/encrypt output audio", "details": str(e)}

    return {
        "status": "success",
        "encrypted_audio": encrypted_audio  # base64-encoded encrypted bytes
    }


# --- RUNPOD ENTRY POINT ---
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})