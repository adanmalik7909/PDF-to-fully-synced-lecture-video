# -*- coding: utf-8 -*-
"""Text-to-Speech Processor V8
Primary: edge-tts (Microsoft Neural -- male professor voice, lecture pacing)

V8 Upgrades:
- Added `generate_audio_with_timestamps()` to extract WordBoundary events for karaoke subtitles.
- Added `backfill_timestamps()` to inject timing data back into the Blueprint JSON.
"""
import os
import asyncio
import json
from app.utils.logger import log_info, log_error

EDGE_TTS_VOICE = "en-US-GuyNeural"
EDGE_TTS_RATE = "-8%"
EDGE_TTS_PITCH = "+0Hz"


async def _async_generate_audio_with_timestamps(text: str, output_path: str) -> list:
    """Async generator for audio and timestamps using edge-tts stream."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text,
        voice=EDGE_TTS_VOICE,
        rate=EDGE_TTS_RATE,
        pitch=EDGE_TTS_PITCH
    )
    
    word_timestamps = []
    audio_chunks = []

    try:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                audio_chunks.append(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                word_timestamps.append({
                    'word':       chunk['text'],
                    'start_sec':  chunk['offset'] / 10_000_000,  # 100ns → seconds
                    'duration':   chunk['duration'] / 10_000_000
                })
                
        with open(output_path, 'wb') as f:
            for c in audio_chunks:
                f.write(c)
                
        # Fallback: If edge-tts provided audio but 0 timestamps, estimate them
        if not word_timestamps and audio_chunks:
            log_info("[TTS V8] WordBoundary events missing. Estimating timestamps...")
            import librosa
            total_duration = librosa.get_duration(path=output_path)
            words = text.split()
            if words:
                word_dur = total_duration / len(words)
                for i, w in enumerate(words):
                    word_timestamps.append({
                        'word': w,
                        'start_sec': i * word_dur,
                        'duration': word_dur
                    })

        log_info(f"[TTS V8] Generated audio with {len(word_timestamps)} word timestamps.")
        return word_timestamps
    except Exception as e:
        log_error(f"[TTS V8] Error generating audio with timestamps: {e}")
        return []


def generate_audio_with_timestamps(text: str, output_path: str) -> list:
    """Synchronous wrapper for V8 timestamp extraction."""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    mp3_path = output_path if output_path.endswith(".mp3") else os.path.splitext(output_path)[0] + ".mp3"
    
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(_async_generate_audio_with_timestamps(text, mp3_path))).result(timeout=180)
    except RuntimeError:
        return asyncio.run(_async_generate_audio_with_timestamps(text, mp3_path))


def backfill_timestamps(scene: dict, all_timestamps: list) -> dict:
    """
    V9.0 Orchestration: Map conceptual 'time_hints' to precise word timestamps.
    """
    if not all_timestamps:
        return scene
        
    timeline = scene.get("timeline", [])
    for entry in timeline:
        hint = entry.get("time_hint")
        
        # If the hint is a string (trigger word), find its timestamp
        if isinstance(hint, str):
            trigger_word = hint.lower()
            for ts in all_timestamps:
                if trigger_word in ts['word'].lower():
                    entry['time_sec'] = ts['start_sec']
                    break
        else:
            # If it's already a number, just use it
            entry['time_sec'] = float(hint) if hint is not None else 0.0

    # Maintain backward compatibility for legacy animations
    zoom_timestamps = []
    bullets = scene.get("bullets", [])
    for i, bullet in enumerate(bullets):
        trigger_word = bullet.get("trigger_word", "").lower()
        zoom_word = bullet.get("zoom_word", "").lower()
        
        if trigger_word:
            for ts in all_timestamps:
                if trigger_word in ts['word'].lower():
                    bullet['trigger_sec'] = ts['start_sec']
                    # Auto-add to timeline if not present
                    timeline.append({
                        "time_sec": ts['start_sec'],
                        "action": "bullet_reveal",
                        "target": f"bullet_{i}"
                    })
                    break
        
        if zoom_word:
            parts = zoom_word.split()
            first_zoom = parts[0] if parts else zoom_word
            for ts in all_timestamps:
                if first_zoom in ts['word'].lower():
                    zoom_timestamps.append(ts['start_sec'])
                    break
                    
    # 3. Map Diagram Callouts
    callouts = scene.get("diagram_callouts", [])
    for i, callout in enumerate(callouts):
        trigger_word = callout.get("trigger_word", "").lower()
        if trigger_word:
            for ts in all_timestamps:
                if trigger_word in ts['word'].lower():
                    callout['trigger_sec'] = ts['start_sec']
                    timeline.append({
                        "time_sec": ts['start_sec'],
                        "action": "diagram_callout",
                        "target": f"callout_{i}"
                    })
                    break

    scene['zoom_word_timestamps'] = zoom_timestamps
    scene['timeline'] = sorted(timeline, key=lambda x: x.get('time_sec', 0))
    return scene


# =============================================================================
# V7 Backward Compatibility Below
# =============================================================================

def text_to_speech(text: str, output_path: str) -> bool:
    """Convert text to speech audio using high-quality male neural voice. (Legacy V7 wrapper)"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    clean_text = text.strip()
    if not clean_text:
        return False

    try:
        timestamps = generate_audio_with_timestamps(clean_text, output_path)
        if timestamps:
            return True
    except Exception as e:
        log_error(f"[TTS] V8 generator failed ({e}), trying gTTS fallback...")

    # gTTS fallback
    try:
        from gtts import gTTS
        mp3_path = output_path if output_path.endswith(".mp3") else os.path.splitext(output_path)[0] + ".mp3"
        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.save(mp3_path)
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
            log_info(f"[TTS] gTTS generated: {mp3_path}")
            return True
    except Exception as e:
        log_error(f"[TTS] gTTS failed: {e}")

    # pyttsx3 last resort
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        voices = engine.getProperty('voices')
        for v in voices:
            if 'male' in v.name.lower() or 'david' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        wav_path = output_path if output_path.endswith(".wav") else os.path.splitext(output_path)[0] + ".wav"
        engine.save_to_file(clean_text, wav_path)
        engine.runAndWait()
        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
            log_info(f"[TTS] pyttsx3 generated: {wav_path}")
            return True
    except Exception as e:
        log_error(f"[TTS] pyttsx3 failed: {e}")

    return False


def generate_audio_for_text(text: str, output_dir: str, filename: str = "audio.mp3") -> str | None:
    """High-level helper (V7 legacy)."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)
    ok = text_to_speech(text, out_path)
    if ok:
        return out_path
    return None
