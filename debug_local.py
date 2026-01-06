import argparse
import os
import io
import time
import torch
import torchaudio
from cryptography.fernet import Fernet
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from chatterbox.vc import ChatterboxVC

# --- ARGS SETUP ---
parser = argparse.ArgumentParser(description="Debug Chatterbox in-container")
parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device (cpu/cuda)")
parser.add_argument("--format", type=str, default="wav", help="Output audio format (wav, opus, ogg, mp3)")
parser.add_argument("--text", type=str, default="Hello, this is a test of the in-memory audio encoding.", help="Text to generate")
parser.add_argument("--test-vc", action="store_true", help="Run VC test using the TTS output as source")
args = parser.parse_args()

# --- BACKEND SETUP ---
try:
    if "ffmpeg" in torchaudio.list_audio_backends():
        torchaudio.set_audio_backend("ffmpeg")
        print("✅ Backend set to: ffmpeg")
except Exception as e:
    print(f"⚠️ Warning: {e}")

# --- MOCK ENCRYPTION ---
KEY = Fernet.generate_key()
cipher = Fernet(KEY)

# --- MODEL LOADING ---
print(f"\n--- Loading Models on {args.device} ---")
start_time = time.time()
tts_model = ChatterboxMultilingualTTS.from_pretrained(args.device)
if args.test_vc:
    vc_model = ChatterboxVC.from_pretrained(args.device)
print(f"Models loaded in {time.time() - start_time:.2f}s")

def encode_in_memory(wav_tensor, sample_rate, fmt):
    """Helper to test in-memory encoding"""
    buf = io.BytesIO()
    # torchaudio.save requires a seekable file or bytes buffer
    torchaudio.save(buf, wav_tensor, sample_rate, format=fmt)
    buf.seek(0)
    return buf

def test_tts():
    print(f"\n[1/2] --- Testing TTS ---")
    print(f"Input Text: '{args.text}'")
    
    # 1. Generate
    t0 = time.time()
    wav = tts_model.generate(text=args.text, language_id="en")
    print(f"Generated in {time.time() - t0:.2f}s")

    # 2. Encode
    print(f"Encoding to '{args.format}'...")
    try:
        buf = encode_in_memory(wav, tts_model.sr, args.format)
        print(f"✅ Encoded size: {len(buf.getvalue())} bytes")
        return buf.getvalue()
    except Exception as e:
        print(f"❌ TTS Encoding Failed: {e}")
        return None

def test_vc(source_bytes):
    print(f"\n[2/2] --- Testing VC ---")
    
    try:
        # 1. Simulate receiving encrypted audio (Decode)
        print("Decoding source audio...")
        input_buf = io.BytesIO(source_bytes)
        source_wav, source_sr = torchaudio.load(input_buf)
        
        # 2. Resample for VC (Needs 16kHz for source)
        if source_sr != 16000:
            source_wav = torchaudio.functional.resample(source_wav, source_sr, 16000)
        
        # 3. Prepare buffers (We use the same audio as Target for 'Identity' test)
        source_io = io.BytesIO()
        torchaudio.save(source_io, source_wav, 16000, format="wav")
        source_io.seek(0)

        # For target, we just use the original bytes (Chatterbox handles resampling internally usually)
        target_io = io.BytesIO(source_bytes) 
        
        # 4. Generate VC
        print("Running VC Inference...")
        t0 = time.time()
        out_wav = vc_model.generate(audio=source_io, target_voice_path=target_io)
        print(f"Converted in {time.time() - t0:.2f}s")

        # 5. Encode Result
        print(f"Encoding VC result to '{args.format}'...")
        out_buf = encode_in_memory(out_wav, vc_model.sr, args.format)
        print(f"✅ VC Encoded size: {len(out_buf.getvalue())} bytes")
        
        return out_buf.getvalue()

    except Exception as e:
        print(f"❌ VC Failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Run TTS
    tts_audio = test_tts()
    
    # Run VC if requested and TTS succeeded
    if args.test_vc and tts_audio:
        vc_audio = test_vc(tts_audio)
        
        # Save VC output if available
        if vc_audio:
            fname = f"debug_vc_output.{args.format}"
            with open(fname, "wb") as f:
                f.write(vc_audio)
            print(f"\nSaved VC artifact to {fname}")
    
    elif tts_audio:
        # Save TTS output
        fname = f"debug_tts_output.{args.format}"
        with open(fname, "wb") as f:
            f.write(tts_audio)
        print(f"\nSaved TTS artifact to {fname}")
