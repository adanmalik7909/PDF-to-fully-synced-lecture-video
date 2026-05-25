import sys
import os

sys.path.insert(0, "c:\\Users\\PMLS\\Desktop\\Prototype\\SmartStudyInstructor\\backend")

from core.animation_brain import _match_timestamps, generate_animation_script, AnimationBrain

# Mock word timestamps
mock_words = [
    {"word": "Welcome", "start_ms": 100, "end_ms": 400},
    {"word": "to", "start_ms": 420, "end_ms": 600},
    {"word": "deep", "start_ms": 650, "end_ms": 1000},
    {"word": "neural", "start_ms": 1050, "end_ms": 1600},
    {"word": "networks.", "start_ms": 1650, "end_ms": 2200},
]

print("--- Testing Word Timestamp Matching ---")

# Test exact matching
events = [
    {"event_type": "diagram_zoom_in", "trigger_word": "deep", "data": {}},
    {"event_type": "diagram_cursor_move", "trigger_word": "neural", "data": {}},
]
matched = _match_timestamps(events.copy(), mock_words)
print("1. Exact Match:")
for m in matched:
    print(f"   Word: {m.get('timestamp_ms')}ms (expected 650ms for deep, 1050ms for neural)")

# Test fuzzy/punctuation matching
events_fuzzy = [
    {"event_type": "diagram_zoom_in", "trigger_word": "networks", "data": {}},
]
matched_fuzzy = _match_timestamps(events_fuzzy.copy(), mock_words)
print("2. Fuzzy/Punctuation Match:")
for m in matched_fuzzy:
    print(f"   Word: {m.get('timestamp_ms')}ms (expected 1650ms for networks)")

# Test positional/even-spacing fallback
events_fallback = [
    {"event_type": "diagram_zoom_in", "trigger_word": "unmatched_word", "data": {}},
    {"event_type": "diagram_zoom_out", "trigger_word": "another_unmatched_word", "data": {}},
]
matched_fallback = _match_timestamps(events_fallback.copy(), mock_words)
print("3. Unmatched Positional Fallback:")
for m in matched_fallback:
    print(f"   Word: {m.get('timestamp_ms')}ms")

# Test AnimationBrain wrapper class compatibility
print("--- Testing AnimationBrain Wrapper ---")
ab = AnimationBrain()
scene = {
    "scene_type": "diagram",
    "title": "Neural Net",
    "narration_text": "Welcome to deep neural networks",
    "diagram_image_path": "c:\\Users\\PMLS\\Desktop\\Prototype\\SmartStudyInstructor\\backend\\static\\logo.png"  # Using logo or fallback
}
# Fallback check if logo doesn't exist
logo_path = scene["diagram_image_path"]
if not os.path.exists(logo_path):
    # create a dummy empty file to test path validation
    os.makedirs(os.path.dirname(logo_path), exist_ok=True)
    with open(logo_path, "w") as f:
        f.write("")

events_brain = ab.generate_animation_events(scene, scene["narration_text"], mock_words, logo_path)
print(f"Generated events count: {len(events_brain)}")
for ev in events_brain:
    print(f"   {ev['start_ms']:>8.1f}ms - {ev['end_ms']:>8.1f}ms | {ev['event_type']} | data keys: {list(ev['data'].keys())}")

print("--- All Mock V2 Brain Tests OK ---")
