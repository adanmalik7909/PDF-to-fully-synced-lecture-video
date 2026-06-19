# Sync Refactor Plan — Audio-Driven Lecture Video Pipeline

This document outlines the design and implementation steps for refactoring the video generation pipeline of **SmartStudyInstructor** to make it entirely audio-driven, pedagogically engaging, and deterministic.

---

## 1. Core Architecture — Audio-First Pipeline

The core timing source of truth is the Text-to-Speech (TTS) audio. We will capture word-level and sentence-level timestamps, construct semantic segment timelines, drive the rendering engine via a global JS clock, and align the video output to the audio track.

### 1.1. Audio Timeline Extraction and Storage
- **Narration Markers**: Refactor `core/tts_engine.py` to parse script markers like `[pause: duration]` or `[rhetorical_question]`. We will split narration by these markers, synthesize the text blocks, generate silent segments (via FFmpeg `anullsrc`), and concatenate them using FFmpeg `concat` to produce a single master audio file.
- **Word Timestamps Offset**: The word timestamps from each synthesized block will be offset chronologically by the cumulative duration of all preceding blocks and pauses.
- **Sentence Timestamps**: Group consecutive word timestamps into sentences using sentence-ending punctuation (`.`, `?`, `!`) to derive sentence-level events.
- **Predictable Timeline JSON Storage**: Save the full timeline containing words, sentences, and animations as a JSON file under `static/timelines/{scene_id}.json`.

### 1.2. Single Playback Clock & State Dispatcher in JS
- **Clock Wrapper (`audio_clock`)**: Wrap audio and expose a unified clock. It will support two modes:
  - **`audio`**: Tied to an `<audio>` element's `currentTime`.
  - **`virtual`**: A synthetic timer that advances deterministically by exactly `33.33ms` per frame for Playwright capture.
- **Virtual Time Mode**: To prevent desync caused by CPU lag, we will override `window.performance.now` and `window.Date.now` to return the virtual clock's time. This guarantees that all GSAP animations update deterministically frame-by-frame.
- **State-Based Dispatcher (`timeline_dispatcher`)**: Replace the one-shot trigger loop with a state-based dispatcher that triggers `onEnter` and `onLeave` hooks when the clock passes through an event's bounds.

---

## 2. Bullet Highlighting (Synchronized Emphasis)

- **Stable Bullet IDs**: Modify Jinja2 scene templates (`concept.html.j2`, `table_scene.html.j2`, etc.) to assign stable IDs: `bullet_{scene_index}_{bullet_index}`, e.g., `bullet_1_3`.
- **Narration to Bullets Mapping**: Update `TimelineBuilder` to construct continuous `bullet_active` events. A bullet remains active from its activation time until the next bullet becomes active, or until the scene ends.
- **Visual Emphasis CSS**: Leverage the premium `.b-active` styles (and alias `.bullet-active`) which add a gold border, scale emphasis, and drop shadow.
- **JS Integration (`effects_bullets`)**: Implement `onEnter` and `onLeave` bullet highlighting. Ensure only one bullet is active per list. During pauses, active highlights fade out.

---

## 3. Diagram Focus & Camera Choreography

- **Structured VLM Output**: Update Gemini Vision calls in `core/animation_brain.py` to extract named regions:
  ```json
  {
    "regions": [
      {
        "region_id": "input_node",
        "label": "Input Layer",
        "bbox": [x, y, width, height],
        "role": "input",
        "trigger_keyword": "input"
      }
    ]
  }
  ```
- **Responsive Camera Path Generation**: Precompute target scale and responsive translation percentages (`x_pct`, `y_pct` relative to viewport dimensions) for each bounding box:
  - `scale = min(3.5, max(1.5, 0.6 / max(w, h)))`
  - `x_pct = (0.5 - cx) * scale`
  - `y_pct = (0.5 - cy) * scale`
  Store this under `payload.transform` in the timeline event.
- **GSAP Camera Effects (`effects_diagrams`)**: Implement `focusOnRegion(regionId, duration)` to animate the diagram container to the precomputed scale and translation. Call this on entering a `diagram_zoom` event.
- **Stepwise Flow**: Direct the VLM to order regions sequentially matching the logical teaching flow.

---

## 4. Playwright & FFmpeg Sync Refinements

- **Browser Context Reuse**: Refactor `rendering/playwright_capture.py` to launch a single browser instance and context per render job. Sequentially open pages in that context, wait for `window.SCENE_FINISHED === true` (signaled by the virtual clock), close the page, and move the generated `.webm` video.
- **Perfect FFmpeg Audio Alignment**: Update `rendering/ffmpeg_pipeline.py` to pad the recorded webm video using the `tpad=stop_mode=clone:stop=-1` filter (clones the last frame). Combined with the `-shortest` flag, the video track is perfectly aligned/trimmed to match the TTS audio duration.

---

## 5. Code Splitting & Modularization

- **Frontend JS**: Split `_timeline_engine.js.j2` into:
  - `audio_clock.js.j2`
  - `timeline_dispatcher.js.j2`
  - `effects_bullets.js.j2`
  - `effects_diagrams.js.j2`
- **Backend Timeline**: Split `core/timeline_builder.py` into:
  - `tts_parser.py` (markers and silences parsing)
  - `segment_grouper.py` (bullets, zooms, and transition grouping)
  - `event_serializer.py` (JSON output formatting)
- **Backend LLM Clients**: Split `app/rag/llm_client.py` into provider clients, prompt templates, and post-processing helper modules.

---

## 6. Verification Plan

1. **Automated Tests**: Run the basic pipeline tests to verify no compilation errors.
2. **Manual Pipeline Run**: Execute the pipeline on a test PDF, checking:
   - Output log for exact audio durations vs. video durations.
   - Master timeline JSON structure inside `static/timelines/`.
   - Verify video output shows bullet highlights and diagram zooms synced perfectly to narration audio.
