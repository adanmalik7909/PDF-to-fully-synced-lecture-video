# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V14 — Playwright Capture (Windows-Safe)

KEY FIX: On Windows, Uvicorn uses WindowsSelectorEventLoopPolicy which
cannot spawn subprocesses. Playwright needs WindowsProactorEventLoopPolicy.

The ONLY correct solution is to run Playwright in a dedicated thread
that creates its OWN asyncio loop via asyncio.run(), completely
independent from Uvicorn's event loop.
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


def record_scene_video(
    html_content: str,
    timeline_data: Dict,
    total_duration_ms: float,
    output_dir: str,
    scene_id: str,
) -> Optional[str]:
    """
    Records a scene as a .webm video.

    ARCHITECTURE: Runs Playwright in a dedicated thread with its own
    ProactorEventLoop (required on Windows for subprocess support).
    This is called with `await asyncio.get_event_loop().run_in_executor()`
    from the async pipeline, making it non-blocking.
    """
    result_container = [None]
    error_container = [None]

    def _run_in_thread():
        """This function runs in a fresh thread with its own event loop."""
        if sys.platform == 'win32':
            # Set policy BEFORE creating the loop in THIS thread
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _capture():
            from playwright.async_api import async_playwright

            temp_video_dir = os.path.join(output_dir, f"pw_{uuid.uuid4().hex[:6]}")
            os.makedirs(temp_video_dir, exist_ok=True)

            temp_html = os.path.join(temp_video_dir, "scene.html")
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            duration_sec = total_duration_ms / 1000.0
            log_info(f"[Playwright] Recording {scene_id} ({duration_sec:.1f}s)...")

            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--disable-web-security",
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                        ]
                    )
                    context = await browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        record_video_dir=temp_video_dir,
                        record_video_size={"width": 1920, "height": 1080},
                    )
                    page = await context.new_page()

                    # Inject timeline data BEFORE the page loads
                    await page.add_init_script(
                        f"window.TIMELINE_DATA = {json.dumps(timeline_data)};"
                    )

                    abs_html = os.path.abspath(temp_html).replace("\\", "/")
                    await page.goto(
                        f"file:///{abs_html}",
                        wait_until="networkidle",
                        timeout=20000
                    )

                    # Wait for fonts
                    try:
                        await page.wait_for_function(
                            "document.fonts.check('700 18px Playfair Display')",
                            timeout=5000
                        )
                    except Exception:
                        await page.wait_for_timeout(1500)

                    # Let the full scene play out
                    await page.wait_for_timeout(int(total_duration_ms) + 800)

                    await context.close()
                    await browser.close()

            except Exception as e:
                error_container[0] = e
                shutil.rmtree(temp_video_dir, ignore_errors=True)
                return None

            # Find and move the recorded .webm
            webm_files = [f for f in os.listdir(temp_video_dir) if f.endswith(".webm")]
            if not webm_files:
                error_container[0] = Exception(f"No .webm produced for {scene_id}")
                shutil.rmtree(temp_video_dir, ignore_errors=True)
                return None

            src = os.path.join(temp_video_dir, webm_files[0])
            dst = os.path.join(output_dir, f"{scene_id}_raw.webm")
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
            shutil.rmtree(temp_video_dir, ignore_errors=True)
            log_info(f"[Playwright] Scene {scene_id} recorded: {dst}")
            return dst

        # asyncio.run() creates a BRAND NEW event loop in this thread
        result_container[0] = asyncio.run(_capture())

    # Run in a daemon thread so it doesn't block the main Uvicorn process
    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()  # Wait for Playwright to finish

    if error_container[0]:
        log_error(f"[Playwright] Failed for {scene_id}: {error_container[0]}")
        return None

    return result_container[0]

def render_all_scenes(scenes: list, output_dir: str) -> list:
    """
    UPGRADE C: PARALLEL SCENE RENDERING
    Renders multiple scenes concurrently using asyncio.gather and a semaphore (max 3 instances)
    to achieve up to 6x speedup while avoiding GPU memory overload.
    
    The existing function signature render_all_scenes(scenes: list, output_dir: str) is maintained.
    Each scene dict must contain: 'html_content', 'timeline_data', 'total_duration_ms', 'scene_id', 'title'
    """
    result_container = [None]

    def _run_in_thread():
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _capture_all():
            from playwright.async_api import async_playwright
            sem = asyncio.Semaphore(3)

            async def _render_single(idx: int, scene: Dict):
                start_time = time.time()
                scene_id = scene.get("scene_id", f"scene_{idx}")
                title = scene.get("title", scene_id)
                html_content = scene.get("html_content", "")
                timeline_data = scene.get("timeline_data", {})
                total_duration_ms = scene.get("total_duration_ms", 10000)

                async with sem:
                    try:
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(
                                headless=True,
                                args=[
                                    "--disable-web-security",
                                    "--no-sandbox",
                                    "--disable-setuid-sandbox",
                                    "--disable-dev-shm-usage",
                                ]
                            )
                            temp_video_dir = os.path.join(output_dir, f"pw_{uuid.uuid4().hex[:6]}")
                            os.makedirs(temp_video_dir, exist_ok=True)

                            temp_html = os.path.join(temp_video_dir, "scene.html")
                            with open(temp_html, "w", encoding="utf-8") as f:
                                f.write(html_content)

                            context = await browser.new_context(
                                viewport={"width": 1920, "height": 1080},
                                record_video_dir=temp_video_dir,
                                record_video_size={"width": 1920, "height": 1080},
                            )
                            page = await context.new_page()

                            await page.add_init_script(
                                f"window.TIMELINE_DATA = {json.dumps(timeline_data)};"
                            )

                            abs_html = os.path.abspath(temp_html).replace("\\", "/")
                            await page.goto(
                                f"file:///{abs_html}",
                                wait_until="networkidle",
                                timeout=20000
                            )

                            # Wait for duration + 500ms buffer as requested
                            await page.wait_for_timeout(int(total_duration_ms) + 500)

                            await context.close()
                            await browser.close()

                            webm_files = [f for f in os.listdir(temp_video_dir) if f.endswith(".webm")]
                            if not webm_files:
                                raise Exception(f"No .webm produced for {scene_id}")

                            src = os.path.join(temp_video_dir, webm_files[0])
                            dst = os.path.join(output_dir, f"{scene_id}_raw.webm")
                            if os.path.exists(dst):
                                os.remove(dst)
                            shutil.move(src, dst)
                            shutil.rmtree(temp_video_dir, ignore_errors=True)

                            elapsed = time.time() - start_time
                            # Progress log
                            print(f"[ParallelRender] Scene {idx} | {title} | Elapsed: {elapsed:.2f}s")
                            return dst

                    except Exception as e:
                        log_error(f"[ParallelRender] Error rendering {scene_id}: {e}")
                        return None

            tasks = []
            for i, scene in enumerate(scenes):
                tasks.append(asyncio.create_task(_render_single(i, scene)))

            # gather preserves the order of the tasks (and thus the input list)
            return await asyncio.gather(*tasks, return_exceptions=False)

        result_container[0] = asyncio.run(_capture_all())

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()

    return result_container[0]
