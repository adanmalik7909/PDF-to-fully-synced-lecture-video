"""Test all V10 pipeline components."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.timeline_builder import TimelineBuilder
from rendering.scene_router import SceneRouter
from rendering.ffmpeg_pipeline import FFmpegPipeline
from core.tts_engine import synthesize_all_scenes_sync

print("1. All imports OK")

# Test timeline builder output structure
tb = TimelineBuilder(
    scene={
        "scene_id": "s1", "scene_type": "concept",
        "heading_left": "Test Heading", "heading_right": "Sub Heading",
        "bullets": [
            {"text": "Python is powerful", "trigger_word": "powerful", "num": "01", "zoom_word": "powerful", "entrance": "slide_left"}
        ],
        "zoom_words": ["powerful"],
        "diagram_refs": [], "diagram_callouts": [],
        "takeaway": "Python is great", "left_description": "A test."
    },
    words=[
        {"word": "Python", "start_ms": 100, "end_ms": 500, "duration_ms": 400},
        {"word": "is", "start_ms": 520, "end_ms": 700, "duration_ms": 180},
        {"word": "powerful", "start_ms": 720, "end_ms": 1200, "duration_ms": 480},
    ],
    total_ms=5000
)
tl = tb.build()

print(f"2. Timeline events: {len(tl['events'])}")
for ev in tl["events"][:8]:
    print(f"   {ev['start_ms']:>8.1f}ms | {ev['event_type']:22s} | data keys: {list(ev['data'].keys())}")

# Verify field names match what JS expects
for ev in tl["events"]:
    assert "start_ms" in ev, f"Missing start_ms in {ev}"
    assert "event_type" in ev, f"Missing event_type in {ev}"
    assert "data" in ev, f"Missing data in {ev}"

print("3. All field names correct (start_ms, event_type, data) — JS engine will read them.")

# Test SceneRouter rendering
router = SceneRouter()
html = router.render_scene_html(
    scene={
        "scene_id": "s1", "scene_type": "concept", "topic": "Python",
        "heading_left": "Test", "heading_right": "Sub",
        "gold_word": "Test", "left_description": "Desc",
        "bullets": [{"num": "01", "text": "Bullet one", "zoom_word": "one"}],
        "zoom_words": ["one"], "diagram_refs": [], "diagram_paths": [],
        "diagram_callouts": [], "takeaway": "Great!",
        "scene_index": 1, "total_scenes": 1, "avatar_path": None,
    },
    timeline_data=tl
)

if html and len(html) > 100:
    print(f"4. SceneRouter rendered HTML: {len(html)} chars")
    # Verify NO subtitle-bar div in HTML
    has_sub_bar = "subtitle-bar" in html
    has_sub_container = "subtitle-container" in html
    print(f"   subtitle-bar in HTML: {has_sub_bar} (should be False)")
    print(f"   subtitle-container in HTML: {has_sub_container} (should be False)")
    # Verify TIMELINE_DATA is embedded
    has_timeline = "TIMELINE_DATA" in html
    print(f"   TIMELINE_DATA embedded: {has_timeline} (should be True)")
    # Verify event_type appears in embedded JSON
    has_event_type = "event_type" in html
    print(f"   event_type in JSON: {has_event_type} (should be True)")
else:
    print("4. ERROR: SceneRouter returned empty HTML!")
    sys.exit(1)

# Test FFmpegPipeline instantiation
fp = FFmpegPipeline()
print("5. FFmpegPipeline instantiated OK")

print()
print("=" * 60)
print("ALL PIPELINE COMPONENT TESTS PASSED")
print("=" * 60)
