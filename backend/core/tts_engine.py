# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V10 — TTS Engine
Generates audio + per-word millisecond timestamps + SRT subtitles from edge-tts.
All scenes run in parallel via asyncio.gather().

Windows Fix: If edge-tts WordBoundary events are missing (0 events),
             falls back to ffprobe duration + proportional word timestamp estimation.
"""
import os
import json
import asyncio
import re
import subprocess
from typing import List, Dict, Optional
from app.utils.logger import log_info, log_error

# Settings for "Complete System Build"
VOICE = "en-US-AndrewMultilingualNeural" # More natural, teacher-like
GLOBAL_RATE = "-2%"                      # Slightly slower for better clarity
GLOBAL_PITCH = "+0Hz"                    # Corrected pitch format

# V10 Legacy Moods (for compatibility)
SCENE_MOODS = {
    "intro": "energetic",
    "concept": "calm",
    "diagram_focus": "focused",
    "process": "analytical",
    "summary": "warm"
}
DEFAULT_MOOD = "neutral"


def _strip_ssml(text: str) -> str:
    """Remove any SSML/HTML tags from narration text."""
    return re.sub(r'<[^>]+>', '', text).strip()


def _ms(raw_100ns: int) -> float:
    """Convert edge-tts 100-nanosecond offset to milliseconds."""
    return round(raw_100ns / 10_000, 1)


def _get_audio_duration_ms(audio_path: str) -> float:
    """Use ffprobe to get audio duration in milliseconds."""
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=10
        )
        return float(res.stdout.strip()) * 1000
    except Exception:
        return 10000.0  # 10 second fallback


def _estimate_word_timestamps(text: str, total_duration_ms: float) -> List[Dict]:
    """
    Estimate per-word timestamps proportionally.
    Used when edge-tts WordBoundary events are unavailable (Windows issue).
    Average speaking rate: ~130 words/min → ~460ms per word.
    """
    words = text.split()
    if not words:
        return []

    # Distribute evenly across the audio duration, leaving 200ms at end
    usable_ms = max(total_duration_ms - 200, total_duration_ms * 0.9)
    word_dur = usable_ms / len(words)

    timestamps = []
    for i, word in enumerate(words):
        start = round(i * word_dur, 1)
        dur   = round(word_dur * 0.85, 1)  # 85% duty cycle (gap between words)
        timestamps.append({
            "word":        word,
            "start_ms":    start,
            "end_ms":      round(start + dur, 1),
            "duration_ms": dur,
            "start_sec":   round(start / 1000, 4),
            "duration":    round(dur / 1000, 4),
        })

    log_info(f"[TTS V10] Estimated {len(timestamps)} word timestamps from audio duration")
    return timestamps


async def synthesize_scene(
    text: str,
    scene_type: str,
    zoom_words: List[str],
    output_dir: str,
    scene_id: str
) -> Dict:
    """
    Synthesize one scene's narration via edge-tts.
    Returns: {audio_path, words, total_duration_ms, srt_path}
    """
    import edge_tts

    os.makedirs(output_dir, exist_ok=True)
    mood       = SCENE_MOODS.get(scene_type, DEFAULT_MOOD)
    audio_path = os.path.join(output_dir, f"{scene_id}_audio.mp3")
    words_path = os.path.join(output_dir, f"{scene_id}_words.json")
    srt_path   = os.path.join(output_dir, f"{scene_id}.srt")

    clean_text = _strip_ssml(text)
    if not clean_text:
        log_error(f"[TTS V10] Scene {scene_id} has empty narration.")
        return {}

    communicate = edge_tts.Communicate(
        clean_text,
        voice=VOICE,
        rate=GLOBAL_RATE,
        pitch=GLOBAL_PITCH
    )

    word_timestamps = []
    audio_chunks = []

    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_ms = _ms(chunk["offset"])
                dur_ms   = _ms(chunk["duration"])
                word_timestamps.append({
                    "word":        chunk["text"],
                    "start_ms":    start_ms,
                    "end_ms":      round(start_ms + dur_ms, 1),
                    "duration_ms": dur_ms,
                    "start_sec":   round(start_ms / 1000, 4),
                    "duration":    round(dur_ms / 1000, 4),
                })
    except Exception as e:
        log_error(f"[TTS V10] edge-tts stream error for {scene_id}: {e}")
        return {}

    if not audio_chunks:
        log_error(f"[TTS V10] No audio generated for {scene_id}")
        return {}

    # Write audio file
    with open(audio_path, "wb") as f:
        for chunk in audio_chunks:
            f.write(chunk)

    # Get total duration (always from ffprobe — most accurate)
    total_duration_ms = _get_audio_duration_ms(audio_path)

    # ── WINDOWS FIX: if WordBoundary events missing, estimate from audio ──
    if not word_timestamps:
        log_info(f"[TTS V10] No WordBoundary events for {scene_id} — estimating from audio duration")
        word_timestamps = _estimate_word_timestamps(clean_text, total_duration_ms)

    # Save words JSON
    with open(words_path, "w", encoding="utf-8") as f:
        json.dump(word_timestamps, f, ensure_ascii=False, indent=2)

    # Generate ASS only if we have word timestamps
    ass_path = srt_path.replace('.srt', '.ass')
    if word_timestamps:
        _write_ass(word_timestamps, ass_path, zoom_words)
    else:
        ass_path = None  # Signal to pipeline: no ASS available

    log_info(f"[TTS V10] Scene {scene_id}: {len(word_timestamps)} words, {total_duration_ms:.0f}ms")

    return {
        "scene_id":          scene_id,
        "audio_path":        audio_path,
        "words":             word_timestamps,
        "words_path":        words_path,
        "total_duration_ms": total_duration_ms,
        "srt_path":          ass_path,  # Kept as srt_path for backward compatibility in pipeline
    }


def _write_ass(words: List[Dict], ass_path: str, zoom_words: List[str], group_size: int = 6):
    """Write ASS subtitle file with sliding window and amber keyword glow."""
    def ms_to_ass_ts(ms: float) -> str:
        ms = int(ms)
        h = ms // 3_600_000
        ms %= 3_600_000
        m = ms // 60_000
        ms %= 60_000
        s = ms // 1000
        ms %= 1000
        cs = ms // 10 # ASS uses centiseconds
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    if not words:
        return

    # Clean zoom words
    zw_clean = [w.strip().lower() for w in zoom_words if w.strip()]

    # ASS Header
    ass_content = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "WrapStyle: 1",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Inter,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,60,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for i in range(0, len(words), group_size):
        group = words[i:i + group_size]
        start_ts = ms_to_ass_ts(group[0]["start_ms"])
        end_ts = ms_to_ass_ts(group[-1]["end_ms"])
        
        formatted_words = []
        has_zoom = any(any(zw in w["word"].lower() for zw in zw_clean) for w in group)
        
        for w in group:
            word_text = w["word"]
            is_zoom = any(zw in word_text.lower() for zw in zw_clean)
            
            if is_zoom:
                # Amber Glow + Scale
                formatted_words.append(f"{{\\c&H00A8FF&\\fscx105\\fscy105}}{word_text}{{\\c&HFFFFFF&\\fscx100\\fscy100}}")
            else:
                if has_zoom:
                    # Dim to 70% opacity (4D alpha) if there's a zoom word in the group
                    formatted_words.append(f"{{\\alpha&H4D&}}{word_text}{{\\alpha&H00&}}")
                else:
                    formatted_words.append(word_text)
                    
        line_text = " ".join(formatted_words)
        ass_content.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{line_text}")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_content))


async def synthesize_all_scenes(scenes: List[Dict], output_dir: str) -> List[Dict]:
    """Synthesize ALL scenes in parallel via asyncio.gather()."""
    tasks = []
    for scene in scenes:
        scene_id   = str(scene.get("scene_id", f"scene_{len(tasks)+1}"))
        scene_type = scene.get("scene_type", "concept")
        narration  = (scene.get("narration") or scene.get("ssml_narration")
                      or scene.get("dialogue", ""))
        zoom_words = scene.get("zoom_words", [])
        tasks.append(synthesize_scene(narration, scene_type, zoom_words, output_dir, scene_id))

    results = await asyncio.gather(*tasks)
    log_info(f"[TTS V10] All {len(results)} scenes synthesized.")
    return list(results)


def synthesize_all_scenes_sync(scenes: List[Dict], output_dir: str) -> List[Dict]:
    """Synchronous wrapper for synthesize_all_scenes."""
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                lambda: asyncio.run(synthesize_all_scenes(scenes, output_dir))
            ).result(timeout=300)
    except RuntimeError:
        return asyncio.run(synthesize_all_scenes(scenes, output_dir))
