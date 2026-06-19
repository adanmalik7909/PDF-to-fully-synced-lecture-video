# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V15 — Playwright Capture (Windows-Safe, Browser-Reusing)

Reuses a single browser and context per render job.
Utilizes Virtual Time Mode by checking window.SCENE_FINISHED flag.
"""
import os
import sys
import time
import json
import uuid
import shutil
import asyncio
import threading
from typing import Dict, Optional
from app.utils.logger import log_info, log_error


class PlaywrightRenderer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.temp_video_dir = os.path.join(output_dir, f"pw_job_{uuid.uuid4().hex[:6]}")
        os.makedirs(self.temp_video_dir, exist_ok=True)
        self.playwright = None
        self.browser = None
        self.context = None

    async def start(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-web-security",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=self.temp_video_dir,
            record_video_size={"width": 1920, "height": 1080},
        )
        log_info("[PlaywrightRenderer] Shared browser context started.")

    async def record_scene(self, html_content: str, timeline_data: Dict, scene_id: str) -> Optional[str]:
        temp_html = os.path.join(self.temp_video_dir, f"{scene_id}.html")
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        page = await self.context.new_page()
        try:
            await page.add_init_script(f"window.TIMELINE_DATA = {json.dumps(timeline_data)};")
            await page.add_init_script("window.IS_CAPTURING = true;")

            abs_html = os.path.abspath(temp_html).replace("\\", "/")
            await page.goto(f"file:///{abs_html}", wait_until="networkidle", timeout=20000)

            # Wait for fonts
            try:
                await page.wait_for_function("document.fonts.check('700 18px Playfair Display')", timeout=5000)
            except Exception:
                pass

            # Wait for window.SCENE_FINISHED to be true
            total_duration_ms = timeline_data.get("total_duration_ms", 10000)
            timeout_ms = total_duration_ms + 10000

            log_info(f"[PlaywrightRenderer] Recording {scene_id} in Virtual Time Mode...")
            try:
                await page.wait_for_function("window.SCENE_FINISHED === true", timeout=timeout_ms)
                log_info(f"[PlaywrightRenderer] Scene {scene_id} finished naturally.")
            except Exception as e:
                log_error(f"[PlaywrightRenderer] Scene {scene_id} timed out waiting for finished flag: {e}")

            # Get video path and close page to save file
            video_path = await page.video.path()
            await page.close()

            # Wait briefly for file write completion
            for _ in range(30):
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    break
                await asyncio.sleep(0.1)

            # Move video to destination with retries for Windows file lock (WinError 32)
            dst = os.path.join(self.output_dir, f"{scene_id}_raw.webm")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass

            moved = False
            for attempt in range(50):  # Try for 5 seconds
                try:
                    shutil.move(video_path, dst)
                    moved = True
                    break
                except (PermissionError, OSError) as e:
                    # Check for WinError 32 or PermissionError
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log_error(f"[PlaywrightRenderer] Error moving video (attempt {attempt}): {e}")
                    await asyncio.sleep(0.1)

            if not moved:
                log_info("[PlaywrightRenderer] shutil.move failed (file locked). Trying shutil.copy fallback...")
                for attempt in range(50):
                    try:
                        shutil.copy(video_path, dst)
                        moved = True
                        break
                    except (PermissionError, OSError):
                        await asyncio.sleep(0.1)

                if moved:
                    for _ in range(20):
                        try:
                            os.remove(video_path)
                            break
                        except Exception:
                            await asyncio.sleep(0.1)
                else:
                    raise Exception(f"Failed to copy/move video file from {video_path} to {dst} after retries (WinError 32).")

            log_info(f"[PlaywrightRenderer] Scene {scene_id} recorded and saved to: {dst}")
            return dst

        except Exception as e:
            log_error(f"[PlaywrightRenderer] Failed recording {scene_id}: {e}")
            try:
                await page.close()
            except Exception:
                pass
            return None

    async def close(self):
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            log_error(f"[PlaywrightRenderer] Error during shutdown: {e}")
        shutil.rmtree(self.temp_video_dir, ignore_errors=True)


class PlaywrightRenderManager:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.loop = None
        self.thread = None
        self.renderer = None
        self._started = False
        self._lock = None

    def start(self):
        self._started_event = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._started_event.wait()

    def _run_loop(self):
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def _init():
            self.renderer = PlaywrightRenderer(self.output_dir)
            await self.renderer.start()
            self._lock = asyncio.Lock()
            self._started = True
            self._started_event.set()

        self.loop.run_until_complete(_init())
        self.loop.run_forever()

    async def _record_scene_internal(self, html_content: str, timeline_data: Dict, scene_id: str) -> Optional[str]:
        async with self._lock:
            return await self.renderer.record_scene(html_content, timeline_data, scene_id)

    async def record_scene_async(self, html_content: str, timeline_data: Dict, scene_id: str) -> Optional[str]:
        future = asyncio.run_coroutine_threadsafe(
            self._record_scene_internal(html_content, timeline_data, scene_id),
            self.loop
        )
        return await asyncio.wrap_future(future)

    def shutdown(self):
        if self.loop:
            async def _cleanup():
                await self.renderer.close()
                self.loop.stop()
            asyncio.run_coroutine_threadsafe(_cleanup(), self.loop)
            self.thread.join(timeout=5)


# ─────────────────────────────────────────────────────────────────────
# Backward compatibility standalones (launches a fresh browser context)
# ─────────────────────────────────────────────────────────────────────

def record_scene_video(
    html_content: str,
    timeline_data: Dict,
    total_duration_ms: float,
    output_dir: str,
    scene_id: str,
) -> Optional[str]:
    """
    Legacy fallback: launches browser on every call.
    """
    result_container = [None]
    error_container = [None]

    def _run_in_thread():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _capture():
            from playwright.async_api import async_playwright
            temp_video_dir = os.path.join(output_dir, f"pw_{uuid.uuid4().hex[:6]}")
            os.makedirs(temp_video_dir, exist_ok=True)
            temp_html = os.path.join(temp_video_dir, "scene.html")
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--disable-web-security", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                    )
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        record_video_dir=temp_video_dir,
                        record_video_size={"width": 1920, "height": 1080},
                    )
                    page = await context.new_page()
                    await page.add_init_script(f"window.TIMELINE_DATA = {json.dumps(timeline_data)};")
                    await page.add_init_script("window.IS_CAPTURING = true;")

                    abs_html = os.path.abspath(temp_html).replace("\\", "/")
                    await page.goto(f"file:///{abs_html}", wait_until="networkidle", timeout=20000)

                    try:
                        await page.wait_for_function("document.fonts.check('700 18px Playfair Display')", timeout=5000)
                    except Exception:
                        pass

                    # Wait for finished flag
                    try:
                        await page.wait_for_function("window.SCENE_FINISHED === true", timeout=total_duration_ms + 10000)
                    except Exception:
                        await page.wait_for_timeout(int(total_duration_ms) + 1000)

                    await context.close()
                    await browser.close()
            except Exception as e:
                error_container[0] = e
                shutil.rmtree(temp_video_dir, ignore_errors=True)
                return None

            # Wait for Chromium to flush the WebM file (Windows file handle release delay)
            time.sleep(0.3)

            # Wait up to 5s for the .webm file to appear and have content
            webm_files = []
            for _ in range(50):
                webm_files = [f for f in os.listdir(temp_video_dir) if f.endswith(".webm")]
                if webm_files:
                    src_candidate = os.path.join(temp_video_dir, webm_files[0])
                    if os.path.getsize(src_candidate) > 0:
                        break
                time.sleep(0.1)

            if not webm_files:
                error_container[0] = Exception(f"No .webm produced for {scene_id}")
                shutil.rmtree(temp_video_dir, ignore_errors=True)
                return None

            src = os.path.join(temp_video_dir, webm_files[0])
            dst = os.path.join(output_dir, f"{scene_id}_raw.webm")
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except Exception:
                    pass

            # Retry move with copy fallback for Windows file locks (WinError 32)
            moved = False
            for attempt in range(50):
                try:
                    shutil.move(src, dst)
                    moved = True
                    break
                except (PermissionError, OSError):
                    time.sleep(0.1)

            if not moved:
                # Fallback: copy instead of move
                for attempt in range(50):
                    try:
                        shutil.copy2(src, dst)
                        moved = True
                        break
                    except (PermissionError, OSError):
                        time.sleep(0.1)

            if not moved:
                error_container[0] = Exception(f"Failed to move/copy WebM for {scene_id} (WinError 32)")
                return None

            shutil.rmtree(temp_video_dir, ignore_errors=True)
            return dst

        result_container[0] = asyncio.run(_capture())

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()

    if error_container[0]:
        log_error(f"[Playwright legacy] Failed for {scene_id}: {error_container[0]}")
        return None
    return result_container[0]


def render_all_scenes(scenes: list, output_dir: str) -> list:
    """
    Legacy fallback for parallel scene render.
    """
    result_container = [None]

    def _run_in_thread():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _capture_all():
            manager = PlaywrightRenderManager(output_dir)
            manager.start()
            
            async def _render_single(idx: int, scene: Dict):
                html_content = scene.get("html_content", "")
                timeline_data = scene.get("timeline_data", {})
                scene_id = scene.get("scene_id", f"scene_{idx}")
                return await manager.record_scene_async(html_content, timeline_data, scene_id)

            tasks = []
            for i, scene in enumerate(scenes):
                tasks.append(asyncio.create_task(_render_single(i, scene)))

            res = await asyncio.gather(*tasks, return_exceptions=False)
            manager.shutdown()
            return res

        result_container[0] = asyncio.run(_capture_all())

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()
    return result_container[0]
