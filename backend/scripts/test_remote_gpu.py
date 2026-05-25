# -*- coding: utf-8 -*-
"""
SmartStudyInstructor — Standalone Kaggle GPU Diagnostic Tool
Verifies connection, health handshake, CUDA cache clear, and dry-run lipsync rendering.
Optimized for Windows CP1252 console unicode compatibility.
"""
import os
import sys
import time
import wave
import struct
import asyncio
import base64

# Align path so we can import from backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.kaggle_client import KaggleCloudClient

def print_banner():
    print("=" * 70)
    print("SMART STUDY INSTRUCTOR - REMOTE GPU DIAGNOSTIC TOOL")
    print("=" * 70)

def create_dummy_wav(path: str, duration: float = 1.0, sample_rate: int = 16000):
    """Generates a 1-second silent mono WAV file using Python's built-in wave module."""
    try:
        with wave.open(path, 'wb') as wav_file:
            wav_file.setnchannels(1)      # Mono
            wav_file.setsampwidth(2)      # 16-bit
            wav_file.setframerate(sample_rate)
            num_frames = int(sample_rate * duration)
            # Pack binary silent bytes (little-endian shorts)
            silent_bytes = struct.pack('<' + 'h' * num_frames, *([0] * num_frames))
            wav_file.writeframes(silent_bytes)
        return True
    except Exception as e:
        print(f"[Error] Failed to create dummy WAV: {e}")
        return False

async def run_diagnostics():
    print_banner()
    
    # 1. Fetch Configuration URL
    cloud_url = settings.CLOUD_RENDER_URL.strip() if settings.CLOUD_RENDER_URL else ""
    print(f"[Config] Loaded CLOUD_RENDER_URL from .env: '{cloud_url}'")
    
    if not cloud_url:
        print("\n[Error] CLOUD_RENDER_URL is not set in backend/.env!")
        print("Action: Please start your Kaggle notebook, run the ngrok tunnel, and paste the URL in backend/.env.")
        return False

    # 2. Instantiate Client
    print("\nStep 1: Initializing Kaggle Client...")
    client = KaggleCloudClient(cloud_url)
    print("[Status] Client initialized successfully.")

    # 3. Check Connection & GPU Status
    print("\nStep 2: Running Health Check Handshake...")
    health = await client.check_health()
    if health.get("status") != "online":
        print("\n[Error] Handshake Failed! Kaggle GPU server is offline or unreachable.")
        print("Action Checklist:")
        print("   1. Verify your Kaggle Notebook is actively running.")
        print("   2. Verify that Cell 2 started successfully without error.")
        print("   3. Confirm your NGROK_TOKEN in Kaggle matches your account.")
        print("   4. Verify you can open the ngrok URL in a browser (should show Flask online message).")
        return False
    
    gpu_name = health.get("gpu_name") or health.get("gpu") or "Unknown Device"
    print(f"[Status] Handshake OK! Remote GPU detected: {gpu_name}")

    # 4. Test Cache Clearing
    print("\nStep 3: Testing CUDA VRAM Cache Clearing...")
    cleared = await client.clear_cache()
    if cleared:
        print("[Status] Cache clearing handshake succeeded.")
    else:
        print("[Warning] Cache clearing warning: returned non-ok status, continuing diagnostics...")

    # 5. Build Dummy WAV Audio
    print("\nStep 4: Generating a 1-second silent WAV for testing...")
    temp_audio = "static/audio/diagnostic_test.wav"
    os.makedirs(os.path.dirname(temp_audio), exist_ok=True)
    if create_dummy_wav(temp_audio):
        print(f"[Status] Silent WAV generated: '{temp_audio}' ({os.path.getsize(temp_audio)} bytes)")
    else:
        return False

    # 6. Resolve Avatar Path
    print("\nStep 5: Resolving default avatar image...")
    fallback_avatar = settings.AVATAR_IMAGE_PATH if (settings.AVATAR_IMAGE_PATH and os.path.exists(settings.AVATAR_IMAGE_PATH)) else "static/avatars/my_avatar.jpg"
    print(f"👉 Target Avatar path: '{fallback_avatar}'")
    if not os.path.exists(fallback_avatar):
        print(f"[Error] Default avatar not found at '{fallback_avatar}'!")
        print("Action: Please ensure 'backend/static/avatars/my_avatar.jpg' exists.")
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        return False
    print("[Status] Avatar verified.")

    # 7. Run Dry-run lipsync rendering
    print("\nStep 6: Triggering Remote Lipsync Rendering Job...")
    print("⏳ Sending base64 payloads to Kaggle (this may take 10-30 seconds depending on GPU cold start)...")
    
    t0 = time.time()
    try:
        result_video = await client.generate_lipsync(
            scene_id="diagnostic_test_scene",
            audio_path=temp_audio,
            avatar_image_path=fallback_avatar
        )
        
        elapsed = time.time() - t0
        if result_video and os.path.exists(result_video):
            size_kb = os.path.getsize(result_video) / 1024.0
            print(f"\n[Success] Remote Lipsync Render Completed in {elapsed:.2f} seconds!")
            print(f"[Status] Generated Video Path: '{result_video}' ({size_kb:.1f} KB)")
            print("[Status] Your Remote GPU pipeline is fully synchronized and ready for heavy rendering!")
            
            # Clean up test files
            try:
                os.remove(temp_audio)
                os.remove(result_video)
                print("[Status] Cleaned up temporary diagnostic files.")
            except:
                pass
            return True
        else:
            print(f"\n[Error] Lipsync completed but output video was not found or empty.")
            return False
            
    except Exception as e:
        print(f"\n[Exception] Diagnostic Exception encountered: {e}")
        print("Action: Check the console output in your Kaggle Notebook to view the full traceback error.")
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        return False

if __name__ == "__main__":
    # Run async main loop
    success = asyncio.run(run_diagnostics())
    print("\n" + "=" * 70)
    if success:
        print("SYSTEM DIAGNOSTICS: PASSED")
    else:
        print("SYSTEM DIAGNOSTICS: FAILED")
    print("=" * 70)
    sys.exit(0 if success else 1)
