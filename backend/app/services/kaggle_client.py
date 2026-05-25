import os
import time
import base64
import httpx
from app.utils.logger import log_info, log_error

class KaggleCloudClient:
    """
    Handles communication with the Kaggle MuseTalk Cloud Engine via Ngrok.
    Implements base64 encoding, queuing logic, and robust error handling.
    """
    
    def __init__(self, ngrok_url: str):
        self.base_url = ngrok_url.strip().rstrip('/')
        self.timeout = 300.0  # 5 minutes for heavy lipsync processing
        self.max_retries = 3
        log_info(f"[Kaggle Client] Initialized with Base URL: '{self.base_url}'")

    async def check_health(self) -> dict:
        """Ping the Kaggle notebook to ensure it is awake."""
        url = f"{self.base_url}/health"
        log_info(f"[Kaggle Client] Pinging health endpoint: {url}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
                gpu = data.get('gpu') or data.get('gpu_name') or "Unknown"
                log_info(f"[Kaggle Client] Health Check OK: GPU={gpu}")
                return data
        except Exception as e:
            log_error(f"[Kaggle Client] Health Check Failed: {e}")
            return {"status": "offline", "error": str(e)}

    async def clear_cache(self) -> bool:
        """Clear CUDA VRAM on Kaggle if OOM errors occur."""
        url = f"{self.base_url}/clear_cache"
        log_info(f"[Kaggle Client] Requesting remote VRAM clearing: {url}")
        try:
            async with httpx.AsyncClient() as client:
                await client.get(url, timeout=15.0)
                log_info("[Kaggle Client] Cleared GPU Cache successfully")
                return True
        except Exception as e:
            log_error(f"[Kaggle Client] Failed to clear cache: {e}")
            return False

    async def generate_lipsync(
        self, 
        scene_id: str, 
        audio_path: str, 
        avatar_image_path: str = None
    ) -> str:
        """
        Send audio (+ optional avatar image) to Kaggle for MuseTalk lipsync.
        Returns the path to the downloaded MP4 video.
        """
        url = f"{self.base_url}/generate_lipsync"
        log_info(f"[Kaggle Client] Starting lipsync task for scene: {scene_id}")
        log_info(f"[Kaggle Client] Raw input audio: {audio_path}")
        
        # 1. Encode Audio — Convert MP3→WAV first (Wav2Lip requires WAV)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        wav_path = audio_path.replace(".mp3", ".wav")
        if audio_path.endswith(".mp3") and not os.path.exists(wav_path):
            log_info(f"[Kaggle Client] Converting MP3 to WAV (16000Hz, mono) via FFmpeg...")
            import subprocess
            res = subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
                capture_output=True, timeout=60
            )
            if res.returncode != 0:
                log_error(f"[Kaggle Client] FFmpeg conversion failed: {res.stderr.decode('utf-8', errors='ignore')}")
            else:
                log_info(f"[Kaggle Client] WAV conversion complete: {wav_path}")
        
        final_audio_path = wav_path if os.path.exists(wav_path) else audio_path
        log_info(f"[Kaggle Client] Reading audio file for Base64 encoding: {final_audio_path}")
            
        with open(final_audio_path, "rb") as f:
            audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            log_info(f"[Kaggle Client] Audio encoded (size: {len(audio_data)} bytes, base64 size: {len(audio_b64)} chars)")
            
        # 2. Encode Image (use default avatar if none provided — Kaggle MUST have an image)
        from app.config import settings
        fallback_avatar = settings.AVATAR_IMAGE_PATH if (settings.AVATAR_IMAGE_PATH and os.path.exists(settings.AVATAR_IMAGE_PATH)) else "static/avatars/my_avatar.jpg"
        resolved_avatar = avatar_image_path if (avatar_image_path and os.path.exists(avatar_image_path)) else fallback_avatar
        log_info(f"[Kaggle Client] Resolving avatar path: {resolved_avatar}")
        
        avatar_b64 = None
        if os.path.exists(resolved_avatar):
            try:
                from PIL import Image
                with Image.open(resolved_avatar) as img:
                    log_info(f"[Kaggle Client] Avatar verified: {resolved_avatar} (size: {img.width}x{img.height}, format={img.format})")
            except Exception as e:
                log_error(f"[Kaggle Client] Image check warning: {e}")
                
            with open(resolved_avatar, "rb") as f:
                img_data = f.read()
                avatar_b64 = base64.b64encode(img_data).decode('utf-8')
                log_info(f"[Kaggle Client] Avatar encoded (size: {len(img_data)} bytes, base64 size: {len(avatar_b64)} chars)")
        else:
            log_error(f"[Kaggle Client] Resolved avatar not found at path: {resolved_avatar}")
        
        if not avatar_b64:
            log_error("[Kaggle Client] No avatar image found — lipsync will be skipped.")
            return None
                
        payload = {
            "scene_id": scene_id,
            "audio_base64": audio_b64,
            "avatar_image_base64": avatar_b64
        }
        
        # 3. Request with Retries
        for attempt in range(self.max_retries):
            try:
                log_info(f"[Kaggle Client] Requesting lipsync for {scene_id} (Attempt {attempt+1}/{self.max_retries})...")
                log_info(f"[Kaggle Client] Target URL: {url} | Timeout: {self.timeout}s")
                
                start_time = time.time()
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, timeout=self.timeout)
                    
                    elapsed = time.time() - start_time
                    log_info(f"[Kaggle Client] Remote rendering finished in {elapsed:.2f}s | HTTP Status: {resp.status_code}")
                    
                    # Handle Errors with Body Traceback
                    if resp.status_code != 200:
                        error_body = resp.text[:1000]
                        log_error(f"[Kaggle Client] Server Error {resp.status_code}: {error_body}")
                        
                        if "CUDA out of memory" in error_body:
                            log_error(f"[Kaggle Client] Kaggle OOM! Clearing cache and retrying...")
                            await self.clear_cache()
                            time.sleep(5)
                            continue
                        
                        resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("status") != "success":
                        raise Exception(data.get("error_message", "Unknown Kaggle error"))
                        
                    # Decode Video
                    video_b64 = data.get("lipsync_video_base64")
                    output_path = audio_path.replace("_audio.mp3", "_lipsync.mp4")
                    
                    log_info(f"[Kaggle Client] Writing lipsync video payload to: {output_path}")
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(video_b64))
                        
                    log_info(f"[Kaggle Client] Successfully generated lipsync: {output_path} (size: {os.path.getsize(output_path)} bytes)")
                    return output_path
                    
            except httpx.RequestError as e:
                log_error(f"[Kaggle Client] Network error on {scene_id}: {e}")
                if attempt < self.max_retries - 1:
                    log_info("[Kaggle Client] Waiting 15 seconds to retry...")
                    time.sleep(15) # Wait for ngrok/Kaggle to recover
                else:
                    raise Exception("Kaggle offline — scene queued for later.")
            except Exception as e:
                log_error(f"[Kaggle Client] Error processing {scene_id}: {e}")
                raise
                
        return None
