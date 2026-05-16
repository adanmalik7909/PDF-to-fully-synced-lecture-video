#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V12 Type Safety Test — verifies the pipeline handles string bullets
and generates timeline events without crashing.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

from core.timeline_builder import TimelineBuilder

# Test 1: String bullets (LLM hallucination format)
print("=" * 60)
print("TEST 1: String bullets (crash test)")
print("=" * 60)
scene = {
    "scene_id": "test_1",
    "scene_type": "concept",
    "heading_left": "What is Machine Learning?",
    "heading_right": "Machine Learning",
    "bullets": ["Supervised learning uses labeled data", "Unsupervised finds patterns", "Reinforcement learns from rewards"],
    "zoom_words": ["supervised", "unsupervised"],
    "diagram_refs": [],
    "takeaway": "ML has three main types",
}
words = [{"word": w, "start_ms": i*400, "end_ms": i*400+350, "duration_ms": 350} 
         for i, w in enumerate("What is machine learning and how does supervised and unsupervised work".split())]

try:
    builder = TimelineBuilder(scene=scene, words=words, total_ms=5000)
    timeline = builder.build()
    print(f"  OK: {len(timeline['events'])} events generated")
    for ev in timeline['events'][:5]:
        print(f"    [{ev['start_ms']:.0f}ms] {ev['event_type']}")
    print("  PASSED\n")
except Exception as e:
    print(f"  FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 2: Dict bullets (correct format)
print("=" * 60)
print("TEST 2: Dict bullets (normal format)")
print("=" * 60)
scene2 = {
    "scene_id": "test_2",
    "scene_type": "diagram_focus",
    "heading_left": "Neural Network Architecture",
    "heading_right": "Neural Networks",
    "bullets": [
        {"num": "01", "text": "Input layer receives data", "zoom_word": "Input", "trigger_word": "input", "entrance": "slide_left"},
        {"num": "02", "text": "Hidden layer processes", "zoom_word": "Hidden", "trigger_word": "hidden", "entrance": "slide_left"},
    ],
    "zoom_words": ["backpropagation"],
    "diagram_refs": ["static/uploads/diagrams/test.png"],
    "diagram_trigger_word": "show",
    "visual_events": [
        {"action": "overview", "trigger_word": "show", "target_coords": [0, 0, 1000, 1000], "label": "Full Diagram"},
        {"action": "highlight_and_zoom", "trigger_word": "input", "target_coords": [50, 100, 200, 300], "label": "Input Layer"},
        {"action": "highlight_and_zoom", "trigger_word": "hidden", "target_coords": [300, 100, 500, 300], "label": "Hidden Layer"},
        {"action": "zoom_out", "trigger_word": "picture", "target_coords": [0, 0, 1000, 1000], "label": "Full View"},
    ],
    "heading_actions": [
        {"action_type": "heading_zoom", "trigger_word": "Neural", "target": "heading_right", "zoom_level": 1.12, "duration_ms": 1500},
    ],
    "attention_hooks": [
        {"trigger_word": "remember", "hook_type": "did_you_know", "text": "Neural networks learn like brains!", "position": "top-right"},
    ],
    "takeaway": "Neural networks have layers",
}
words2 = [{"word": w, "start_ms": i*350, "end_ms": i*350+300, "duration_ms": 300} 
          for i, w in enumerate("Let me show you the Neural network with input layer and hidden layer now look at the whole picture remember this".split())]

try:
    builder2 = TimelineBuilder(scene=scene2, words=words2, total_ms=7000)
    timeline2 = builder2.build()
    print(f"  OK: {len(timeline2['events'])} events generated")
    
    # Check for V12 events
    event_types = set(ev['event_type'] for ev in timeline2['events'])
    v12_events = ['diagram_pan_zoom', 'diagram_label_popup', 'diagram_overview', 'diagram_zoom_out_smooth']
    for v12e in v12_events:
        status = "FOUND" if v12e in event_types else "MISSING"
        print(f"    {v12e}: {status}")
    
    print(f"\n  All event types: {sorted(event_types)}")
    print("  PASSED\n")
except Exception as e:
    print(f"  FAILED: {e}\n")
    import traceback
    traceback.print_exc()

# Test 3: No heading_actions (auto-generation test)
print("=" * 60)
print("TEST 3: Auto heading generation")
print("=" * 60)
scene3 = {
    "scene_id": "test_3",
    "scene_type": "concept",
    "heading_left": "What is AI?",
    "heading_right": "Artificial Intelligence",
    "bullets": [{"num": "01", "text": "AI mimics human intelligence", "zoom_word": "AI", "trigger_word": "artificial", "entrance": "slide_left"}],
    "zoom_words": [],
    "diagram_refs": [],
    "takeaway": "AI is everywhere",
    # No heading_actions — should auto-generate
}
words3 = [{"word": w, "start_ms": i*400, "end_ms": i*400+350, "duration_ms": 350} 
          for i, w in enumerate("What is Artificial intelligence and how does it work in real life".split())]

try:
    builder3 = TimelineBuilder(scene=scene3, words=words3, total_ms=5000)
    timeline3 = builder3.build()
    heading_events = [ev for ev in timeline3['events'] if ev['event_type'] == 'heading_action']
    print(f"  Auto-generated {len(heading_events)} heading events")
    for he in heading_events:
        print(f"    [{he['start_ms']:.0f}ms] {he['data'].get('action_type')}")
    print("  PASSED\n")
except Exception as e:
    print(f"  FAILED: {e}\n")
    import traceback
    traceback.print_exc()

print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
