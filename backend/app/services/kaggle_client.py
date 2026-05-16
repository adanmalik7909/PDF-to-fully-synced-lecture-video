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
        self.base_url = ngrok_url.rstrip('/')
        self.timeout = 300.0  # 5 minutes for heavy lipsync processing
        self.max_retries = 3

    async def check_health(self) -> dict:
        """Ping the Kaggle notebook to ensure it is awake."""
        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()
                # Flexibly check for gpu or gpu_name
                gpu = data.get('gpu') or data.get('gpu_name') or "Unknown"
                log_info(f"[Kaggle Client] Health Check OK: GPU={gpu}")
                return data
        except Exception as e:
            log_error(f"[Kaggle Client] Health Check Failed: {e}")
            return {"status": "offline", "error": str(e)}

    async def clear_cache(self) -> bool:
        """Clear CUDA VRAM on Kaggle if OOM errors occur."""
        url = f"{self.base_url}/clear_cache"
        try:
            async with httpx.AsyncClient() as client:
                await client.get(url, timeout=15.0)
                log_info("[Kaggle Client] Cleared GPU Cache")
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
        
        # 1. Encode Audio — Convert MP3→WAV first (Wav2Lip requires WAV)
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        wav_path = audio_path.replace(".mp3", ".wav")
        if audio_path.endswith(".mp3") and not os.path.exists(wav_path):
            import subprocess
            subprocess.run(
                ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
                capture_output=True, timeout=60
            )
        
        final_audio_path = wav_path if os.path.exists(wav_path) else audio_path
            
        with open(final_audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode('utf-8')
            
        # 2. Encode Image (use default avatar if none provided — Kaggle MUST have an image)
        DEFAULT_AVATAR_PATH = "static/avatars/my_avatar.jpg"
        avatar_b64 = None
        resolved_avatar = avatar_image_path if (avatar_image_path and os.path.exists(avatar_image_path)) else DEFAULT_AVATAR_PATH
        if os.path.exists(resolved_avatar):
            with open(resolved_avatar, "rb") as f:
                avatar_b64 = base64.b64encode(f.read()).decode('utf-8')
        
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
                
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, timeout=self.timeout)
                    
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
                    
                    with open(output_path, "wb") as f:
                        f.write(base64.b64decode(video_b64))
                        
                    log_info(f"[Kaggle Client] Successfully generated lipsync: {output_path}")
                    return output_path
                    
            except httpx.RequestError as e:
                log_error(f"[Kaggle Client] Network error on {scene_id}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(30) # Wait for ngrok/Kaggle to recover
                else:
                    raise Exception("Kaggle offline — scene queued for later.")
            except Exception as e:
                log_error(f"[Kaggle Client] Error processing {scene_id}: {e}")
                raise
                
        return None
