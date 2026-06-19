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
        log_error(f"[TTS V10] WARNING: ffprobe failed for {audio_path}. Using 10s fallback duration.")
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


def parse_narration_markers(text: str) -> List[Dict]:
    """
    Parse markers like [pause: 1.5] or [rhetorical_question] from narration.
    Returns a list of segments:
      - {"type": "text", "content": "..."}
      - {"type": "pause", "duration": float, "marker_type": "pause|rhetorical_question|etc"}
    """
    pattern = r'\[(pause|explanation|comparison|recap|rhetorical_question)(?:\:\s*([0-9.]+))?\]'
    segments = []
    last_idx = 0
    for match in re.finditer(pattern, text):
        start, end = match.span()
        preceding_text = text[last_idx:start].strip()
        if preceding_text:
            segments.append({"type": "text", "content": preceding_text})
        marker_type = match.group(1)
        duration_str = match.group(2)
        if duration_str:
            duration = float(duration_str)
        elif marker_type == "pause":
            duration = 1.2
        elif marker_type == "rhetorical_question":
            duration = 1.0
        else:
            duration = 0.5
        segments.append({
            "type": "pause",
            "duration": duration,
            "marker_type": marker_type
        })
        last_idx = end
    remaining_text = text[last_idx:].strip()
    if remaining_text:
        segments.append({"type": "text", "content": remaining_text})
    return segments


def generate_silence(duration_sec: float, out_path: str) -> bool:
    """Generate a silent audio file matching typical edge-tts mono 24k output."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{duration_sec:.3f}",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        out_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception as e:
        log_error(f"[TTS Silence] FFmpeg silence generation error: {e}")
        return False


def concat_audio_with_ffmpeg(audio_paths: List[str], output_path: str) -> bool:
    """Concatenate multiple audio files into a single output using FFmpeg concat filter."""
    if not audio_paths:
        return False
    if len(audio_paths) == 1:
        import shutil
        shutil.copy(audio_paths[0], output_path)
        return True
        
    cmd = ["ffmpeg", "-y"]
    for path in audio_paths:
        cmd.extend(["-i", path])
    
    # Filter complex to concatenate only audio streams
    filter_str = "".join([f"[{i}:a]" for i in range(len(audio_paths))]) + f"concat=n={len(audio_paths)}:v=0:a=1[aout]"
    cmd.extend([
        "-filter_complex", filter_str,
        "-map", "[aout]",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        output_path
    ])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return res.returncode == 0
    except Exception as e:
        log_error(f"[TTS Concat] FFmpeg concatenation error: {e}")
        return False


async def synthesize_scene(
    text: str,
    scene_type: str,
    zoom_words: List[str],
    output_dir: str,
    scene_id: str
) -> Dict:
    """
    Synthesize one scene's narration via edge-tts.
    Supports script markers for pauses and rhetorical questions by splitting,
    synthesizing, inserting silences, and concatenating with FFmpeg.
    Returns: {audio_path, words, total_duration_ms, srt_path}
    """
    import edge_tts

    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, f"{scene_id}_audio.mp3")
    words_path = os.path.join(output_dir, f"{scene_id}_words.json")
    srt_path   = os.path.join(output_dir, f"{scene_id}.srt")

    clean_text = _strip_ssml(text)
    if not clean_text:
        log_error(f"[TTS V10] Scene {scene_id} has empty narration.")
        return {}

    segments = parse_narration_markers(clean_text)
    segment_audios = []
    word_timestamps = []
    current_time_ms = 0.0

    for seg_idx, seg in enumerate(segments):
        seg_audio_path = os.path.join(output_dir, f"{scene_id}_seg_{seg_idx}.mp3")
        
        if seg["type"] == "text":
            communicate = edge_tts.Communicate(
                seg["content"],
                voice=VOICE,
                rate=GLOBAL_RATE,
                pitch=GLOBAL_PITCH
            )
            
            audio_chunks = []
            seg_word_timestamps = []
            
            try:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_chunks.append(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start_ms = _ms(chunk["offset"])
                        dur_ms   = _ms(chunk["duration"])
                        seg_word_timestamps.append({
                            "word":        chunk["text"],
                            "start_ms":    start_ms,
                            "end_ms":      round(start_ms + dur_ms, 1),
                            "duration_ms": dur_ms,
                        })
            except Exception as e:
                log_error(f"[TTS V10] edge-tts segment stream error: {e}")
                continue
                
            if not audio_chunks:
                continue
                
            with open(seg_audio_path, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)
                    
            duration_ms = _get_audio_duration_ms(seg_audio_path)
            
            if not seg_word_timestamps:
                seg_word_timestamps = _estimate_word_timestamps(seg["content"], duration_ms)
                
            # Offset and accumulate timestamps
            for wt in seg_word_timestamps:
                wt["start_ms"] = round(wt["start_ms"] + current_time_ms, 1)
                wt["end_ms"] = round(wt["end_ms"] + current_time_ms, 1)
                wt["start_sec"] = round(wt["start_ms"] / 1000, 4)
                wt["duration"] = round(wt["duration_ms"] / 1000, 4)
                word_timestamps.append(wt)
                
            segment_audios.append(seg_audio_path)
            current_time_ms += duration_ms
            
        elif seg["type"] == "pause":
            duration_ms = seg["duration"] * 1000
            generate_silence(seg["duration"], seg_audio_path)
            segment_audios.append(seg_audio_path)
            
            # Insert a marker event into the word list
            word_timestamps.append({
                "word": f"[{seg['marker_type']}]",
                "start_ms": round(current_time_ms, 1),
                "end_ms": round(current_time_ms + duration_ms, 1),
                "duration_ms": duration_ms,
                "start_sec": round(current_time_ms / 1000, 4),
                "duration": round(duration_ms / 1000, 4),
                "is_marker": True,
                "marker_type": seg["marker_type"]
            })
            current_time_ms += duration_ms

    # Concat all segments
    if not concat_audio_with_ffmpeg(segment_audios, audio_path):
        log_error(f"[TTS V10] Failed to concatenate audio segments for {scene_id}")
        return {}

    # Cleanup segment audios
    for p in segment_audios:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            log_error(f"[TTS Cleanup] Failed to delete {p}: {e}")

    # Re-verify total duration of the master concatenated file
    total_duration_ms = _get_audio_duration_ms(audio_path)
    if total_duration_ms <= 0:
        log_error(f"[TTS V10] WARNING: Concatenated audio has 0 or negative duration for {scene_id}. Re-estimating.")
        total_duration_ms = current_time_ms if current_time_ms > 0 else 10000.0

    # Save words JSON
    with open(words_path, "w", encoding="utf-8") as f:
        json.dump(word_timestamps, f, ensure_ascii=False, indent=2)

    # Generate ASS subtitles
    ass_path = srt_path.replace('.srt', '.ass')
    # Filter out markers for subtitle display
    sub_words = [w for w in word_timestamps if not w.get("is_marker")]
    if sub_words:
        _write_ass(sub_words, ass_path, zoom_words)
    else:
        ass_path = None

    log_info(f"[TTS V10] Scene {scene_id} completed: {len(word_timestamps)} word/markers, {total_duration_ms:.0f}ms")

    return {
        "scene_id":          scene_id,
        "audio_path":        audio_path,
        "words":             word_timestamps,
        "words_path":        words_path,
        "total_duration_ms": total_duration_ms,
        "srt_path":          ass_path,
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
