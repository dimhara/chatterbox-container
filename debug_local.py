import os
import torch
import torchaudio
import io
from cryptography.fernet import Fernet
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.vc import ChatterboxVC

# --- SETUP ---
# Generate a temporary key for local debugging
KEY = Fernet.generate_key()
cipher = Fernet(KEY)
DEVICE = "cpu"

def encrypt(data: bytes): return cipher.encrypt(data).decode()
def decrypt(data: str): return cipher.decrypt(data.encode())

print(f"Initializing models on {DEVICE}...")
tts_model = ChatterboxMultilingualTTS.from_pretrained(DEVICE)
vc_model = ChatterboxVC.from_pretrained(DEVICE)

def test_tts():
    print("\n--- Testing TTS ---")
    text = "Hello world, this is a test of the chatterbox system."
    lang = "en"
    
    # Generate
    wav = tts_model.generate(text=text, language_id=lang)
    
    # Save to buffer
    buf = io.BytesIO()
    torchaudio.save(buf, wav, tts_model.sr, format="wav")
    encrypted_audio = encrypt(buf.getvalue())
    print(f"TTS Success. Encrypted payload length: {len(encrypted_audio)}")
    return encrypted_audio

def test_vc(encrypted_source_audio):
    print("\n--- Testing VC ---")
    # Decrypt the source we just made
    raw_audio = decrypt(encrypted_source_audio)
    source_buf = io.BytesIO(raw_audio)
    
    # For VC, we need a 'target' voice. We will use the same audio for debugging purposes
    # as the 'target_voice_path' argument.
    wav = vc_model.generate(
        audio=source_buf,
        target_voice_path=source_buf
    )
    
    output_path = "debug_output_vc.wav"
    torchaudio.save(output_path, wav, vc_model.sr)
    print(f"VC Success. Saved result to {output_path}")

if __name__ == "__main__":
    try:
        enc_tts = test_tts()
        test_vc(enc_tts)
        print("\nAll systems functional on CPU.")
    except Exception as e:
        print(f"\nDebug failed: {e}")
        import traceback
        traceback.print_exc()
