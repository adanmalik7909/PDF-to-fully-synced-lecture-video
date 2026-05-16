# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V10 — Timeline Builder
The brain of the sync system. Takes TTS word timestamps + Blueprint scene
and produces a Master Timeline JSON where every visual event has an exact start_ms.
"""
import re
from typing import List, Dict, Optional


class TimelineBuilder:
    """
    Builds the Master Timeline JSON for one scene.

    Usage:
        builder = TimelineBuilder(scene=scene_dict, words=word_list, total_ms=14200)
        timeline = builder.build()  # → list of event dicts sorted by start_ms
    """

    def __init__(self, scene: Dict, words: List[Dict], total_ms: float):
        self.scene    = scene
        self.words    = words
        self.total_ms = total_ms
        self._used_indices: set = set()  # prevent reusing the same word occurrence

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def build(self) -> Dict:
        """Return the full Master Timeline JSON for this scene."""
        events = []

        events += self._scene_start()
        events += self._heading_focus()
        events += self._ken_burns()
        events += self._bullets()
        events += self._subtitles()
        events += self._zoom_words()
        events += self._diagram()
        events += self._takeaway()
        events += self._scene_end()
        events += self._spatial_actions()
        events += self._heading_actions()
        events += self._attention_hooks()
        events += self._teacher_draw_events()
        events += self._diagram_flow_events()
        events += self._component_highlight_events()
        events += self._diagram_teaching_sequence()
        events += self._shot_plan_events()

        # V13: Cognitive Load Optimization (resolve conflicts, add breathe moments)
        events = self._optimize_cognitive_load(events)

        # Sort by start_ms
        events.sort(key=lambda e: e["start_ms"])

        return {
            "scene_id":          self.scene.get("scene_id"),
            "total_duration_ms": self.total_ms,
            "audio_path":        self.scene.get("_audio_path", ""),
            "events":            events,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Event builders
    # ──────────────────────────────────────────────────────────────────────

    def _scene_start(self) -> List[Dict]:
        return [self._ev(0, 400, "scene_start", {})]

    def _heading_focus(self) -> List[Dict]:
        return [self._ev(200, 3200, "heading_focus", {
            "heading_left":  self.scene.get("heading_left", ""),
            "heading_right": self.scene.get("heading_right", ""),
        })]

    def _ken_burns(self) -> List[Dict]:
        scene_type = self.scene.get("scene_type", "concept")
        kb_map = {
            "intro":         "zoom_in_center",
            "concept":       "pan_right",
            "diagram_focus": "zoom_toward_region",
            "comparison":    "pan_left",
            "process":       "pan_right",
            "summary":       "zoom_out",
        }
        direction = kb_map.get(scene_type, "pan_right")
        return [self._ev(0, self.total_ms, "ken_burns", {"direction": direction})]

    def _bullets(self) -> List[Dict]:
        events = []
        bullets = self.scene.get("bullets", [])
        prev_enter_ms = None

        for i, bullet in enumerate(bullets):
            # Handle legacy string array hallucinations from LLM
            if isinstance(bullet, str):
                bullet = {"text": bullet, "trigger_word": "", "entrance": "slide_left"}
            elif not isinstance(bullet, dict):
                continue
                
            trigger_word = bullet.get("trigger_word", "")
            found_ms = self._find_word_ms(trigger_word) if trigger_word else None

            if found_ms is None:
                # Proportional fallback
                fraction = (i + 1) / max(len(bullets) + 1, 2)
                found_ms = self.total_ms * fraction

            enter_ms  = max(0, found_ms - 100)
            active_ms = enter_ms + 100
            done_ms   = None  # filled when next bullet enters

            # Mark previous bullet as done when this one enters
            if prev_enter_ms is not None and i > 0:
                events.append(self._ev(enter_ms, enter_ms + 200, "bullet_done",
                                       {"index": i - 1}))

            events.append(self._ev(enter_ms, enter_ms + 600, "bullet_enter", {
                "index":    i,
                "entrance": bullet.get("entrance", "slide_left"),
                "text":     bullet.get("text", "")
            }))
            events.append(self._ev(active_ms, active_ms + 400, "bullet_active",
                                   {"index": i}))

            prev_enter_ms = enter_ms

        return events

    def _subtitles(self) -> List[Dict]:
        """Group words into subtitle chunks of 6 + per-word karaoke highlight."""
        events = []
        group_size = 6
        groups = [self.words[i:i+group_size]
                  for i in range(0, len(self.words), group_size)]

        subtitle_idx = 0
        for group in groups:
            if not group:
                continue
            start_ms = group[0]["start_ms"]
            end_ms   = group[-1]["end_ms"]

            events.append(self._ev(start_ms, end_ms, "subtitle_show", {
                "words": [{"word": w["word"],
                           "start_ms": w["start_ms"],
                           "end_ms":   w["end_ms"]} for w in group],
            }))

            for wi, word in enumerate(group):
                events.append(self._ev(
                    word["start_ms"], word["end_ms"],
                    "subtitle_word_hl",
                    {"word": word["word"], "index": wi, "group_idx": subtitle_idx}
                ))

            subtitle_idx += 1

        return events

    def _zoom_words(self) -> List[Dict]:
        events = []
        zoom_words = self.scene.get("zoom_words", [])
        # Also pick up zoom_word from each bullet
        for b in self.scene.get("bullets", []):
            if isinstance(b, dict):
                zw = b.get("zoom_word", "")
                if zw and zw not in zoom_words:
                    zoom_words.append(zw)

        for i, zw in enumerate(zoom_words):
            found_ms = self._find_word_ms(zw)
            if found_ms is None:
                continue
            dur_ms = self._word_duration_ms(zw) or 400
            events.append(self._ev(found_ms, found_ms + dur_ms + 200, "zoom_word_glow", {
                "word":       zw,
                "element_id": f"zw_{i}",
            }))

        return events

    def _diagram(self) -> List[Dict]:
        events = []
        scene_type = self.scene.get("scene_type", "concept")

        # Diagram float-in (trigger word or proportional)
        diag_refs = self.scene.get("diagram_refs", []) or (
            [self.scene["diagram_ref"]] if self.scene.get("diagram_ref") else []
        )
        if diag_refs:
            diag_trigger = self.scene.get("diagram_trigger_word", "")
            found_ms = self._find_word_ms(diag_trigger) if diag_trigger else None
            if found_ms is None:
                found_ms = self.total_ms * 0.30  # show diagram after ~30%
            events.append(self._ev(found_ms, found_ms + 600, "diagram_enter", {}))

            # UPGRADE 2: Diagram Zoom and Annotation System
            zoom_in_ms = found_ms + 200
            events.append(self._ev(zoom_in_ms, zoom_in_ms + 1100, "diagram_zoom_in", {}))

            # Find next bullet
            next_bullet_ms = None
            bullets = self.scene.get("bullets", [])
            for b in bullets:
                if isinstance(b, dict):
                    tw = b.get("trigger_word", "")
                    b_ms = self._find_word_ms(tw) if tw else None
                    if b_ms is not None and b_ms > zoom_in_ms:
                        if next_bullet_ms is None or b_ms < next_bullet_ms:
                            next_bullet_ms = b_ms

            if next_bullet_ms is not None and next_bullet_ms > zoom_in_ms + 500:
                zoom_out_ms = next_bullet_ms - 500
            else:
                zoom_out_ms = zoom_in_ms + 4500

            events.append(self._ev(zoom_out_ms, zoom_out_ms + 1000, "diagram_zoom_out", {}))

            # ── V12: Diagram Walkthrough Chain ──────────────────────
            # Process visual_events as a choreographed sequence
            visual_events = self.scene.get("visual_events", [])
            valid_visuals = [v for v in visual_events if isinstance(v, dict)]

            if valid_visuals:
                # Step through each visual event with proper timing
                last_event_end = found_ms + 800  # start after diagram entrance

                for vi, vevent in enumerate(valid_visuals):
                    tw = vevent.get("trigger_word", "")
                    cms = self._find_word_ms(tw) if tw else None
                    if cms is None:
                        cms = last_event_end + 300  # 300ms gap between events

                    action = vevent.get("action", "highlight_and_zoom")
                    coords = vevent.get("target_coords", [0, 0, 1000, 1000])
                    label = vevent.get("label", "")

                    if action == "overview":
                        # Zoom out to show full diagram
                        events.append(self._ev(cms, cms + 2000, "diagram_overview", {
                            "label": label,
                        }))
                        last_event_end = cms + 2000

                    elif action == "highlight_and_zoom":
                        # Pan + Zoom to component
                        duration = 3500
                        events.append(self._ev(cms, cms + duration, "diagram_pan_zoom", {
                            "coords": coords,
                            "label": label,
                            "event_index": vi,
                        }))
                        # Label popup appears 400ms after zoom starts
                        if label:
                            events.append(self._ev(cms + 400, cms + duration - 200, "diagram_label_popup", {
                                "coords": coords,
                                "label": label,
                                "event_index": vi,
                            }))
                        last_event_end = cms + duration

                    elif action == "draw_arrow":
                        from_coords = vevent.get("from_coords", [0, 0, 0, 0])
                        to_coords = vevent.get("to_coords", coords)
                        events.append(self._ev(cms, cms + 2000, "diagram_draw_arrow", {
                            "from_coords": from_coords,
                            "to_coords": to_coords,
                            "label": label,
                        }))
                        last_event_end = cms + 2000

                    elif action == "zoom_out":
                        events.append(self._ev(cms, cms + 1500, "diagram_zoom_out_smooth", {
                            "label": label,
                        }))
                        last_event_end = cms + 1500

                    else:
                        # Generic highlight_and_zoom fallback
                        events.append(self._ev(cms, cms + 3500, "highlight_and_zoom", {
                            "coords": coords,
                            "label": label,
                            "event_index": vi,
                        }))
                        last_event_end = cms + 3500

            elif scene_type == "diagram_focus":
                # Fallback: simple zoom for diagram_focus scenes without visual_events
                zoom_ms = found_ms + 800
                events.append(self._ev(zoom_ms, zoom_ms + 3000, "diagram_zoom", {}))

            # Diagram callout pointers (legacy)
            for ci, callout in enumerate(self.scene.get("diagram_callouts", [])):
                if not isinstance(callout, dict):
                    continue
                tw = callout.get("trigger_word", "")
                cms = self._find_word_ms(tw) if tw else None
                if cms is None:
                    order = callout.get("explanation_order", ci + 1)
                    cms = found_ms + (order * 1500)
                events.append(self._ev(cms, cms + 2500, "diagram_pointer", {
                    "bbox":    callout.get("bbox", [0, 0, 0.2, 0.2]),
                    "label":   callout.get("label", ""),
                    "callout_index": ci,
                }))

        # Analogy overlay
        analogy_trigger = self.scene.get("analogy_trigger_word", "")
        analogy_img_kw  = self.scene.get("analogy_image_keyword", "")
        if analogy_trigger and analogy_img_kw:
            found_ms = self._find_word_ms(analogy_trigger)
            if found_ms is not None:
                events.append(self._ev(found_ms, found_ms + 3000, "analogy_overlay", {
                    "image_url": f"/api/assets/broll?q={analogy_img_kw.replace(' ', '+')}",
                }))

        return events

    def _takeaway(self) -> List[Dict]:
        show_ms = self.total_ms * 0.80
        return [self._ev(show_ms, self.total_ms, "takeaway_show", {
            "text": self.scene.get("takeaway", ""),
        })]

    def _scene_end(self) -> List[Dict]:
        end_ms = max(0, self.total_ms - 500)
        return [self._ev(end_ms, self.total_ms, "scene_end", {})]

    def _spatial_actions(self) -> List[Dict]:
        events = []
        spatial_actions = self.scene.get("spatial_actions", [])
        if not isinstance(spatial_actions, list):
            return events
        for action in spatial_actions:
            if not isinstance(action, dict):
                continue
            trigger = action.get("trigger_word", "")
            occurrence = action.get("trigger_word_occurrence", 1)
            found_ms = self._find_word_ms(trigger, occurrence=occurrence)
            
            if found_ms is not None:
                start_ms = max(0, found_ms - 50)
            else:
                start_ms = self.total_ms * 0.5  # fallback
                
            duration_ms = action.get("duration_ms", 2000)
            events.append(self._ev(start_ms, start_ms + duration_ms, f"spatial_{action.get('action_type', 'zoom_to_component')}", {
                "bbox": action.get("bbox"),
                "zoom_level": action.get("zoom_level", 1.5),
                "target_component_id": action.get("target_component_id"),
                "highlight_color": action.get("highlight_color", "#4F8EF7"),
                "label": action.get("label", ""),
                "duration_ms": duration_ms,
                "from_bbox": action.get("from_bbox"), # for draw_arrow
                "to_bbox": action.get("to_bbox"),     # for draw_arrow
                "row_index": action.get("row_index")  # for table_row_highlight
            }))
        return events

    def _heading_actions(self) -> List[Dict]:
        events = []
        heading_actions = self.scene.get("heading_actions", [])
        if not isinstance(heading_actions, list):
            heading_actions = []

        # Process explicit heading actions from LLM
        for ha in heading_actions:
            if not isinstance(ha, dict):
                continue
            found_ms = self._find_word_ms(ha.get("trigger_word", ""))
            start_ms = found_ms if found_ms is not None else 500
            duration_ms = ha.get("duration_ms", 1500)
            events.append(self._ev(start_ms, start_ms + duration_ms, "heading_action", {
                "action_type": ha.get("action_type", "heading_zoom"),
                "target": ha.get("target", "heading_right"),
                "zoom_level": ha.get("zoom_level", 1.12)
            }))

        # ── V12: Auto-generate heading events if LLM didn't provide any ──
        if not heading_actions:
            heading_right = self.scene.get("heading_right", "")
            if heading_right:
                # Try to find when the heading concept is first mentioned
                first_word = heading_right.split()[0] if heading_right.split() else ""
                found_ms = self._find_word_ms(first_word) if first_word else None
                if found_ms is not None:
                    # Auto heading zoom when first mentioned
                    events.append(self._ev(found_ms, found_ms + 1500, "heading_action", {
                        "action_type": "heading_zoom",
                        "target": "heading_right",
                        "zoom_level": 1.12,
                    }))
                    # Auto heading underline at 60% of scene
                    underline_ms = self.total_ms * 0.6
                    events.append(self._ev(underline_ms, underline_ms + 1200, "heading_action", {
                        "action_type": "heading_underline",
                        "target": "heading_right",
                    }))

        return events

    def _attention_hooks(self) -> List[Dict]:
        events = []
        hooks = self.scene.get("attention_hooks", [])
        if not isinstance(hooks, list):
            return events
        for hook in hooks:
            if not isinstance(hook, dict):
                continue
            found_ms = self._find_word_ms(hook.get("trigger_word", ""))
            start_ms = found_ms if found_ms is not None else self.total_ms * 0.6
            events.append(self._ev(start_ms, start_ms + 3500, "attention_hook", {
                "hook_type": hook.get("hook_type", "did_you_know"),
                "text": hook.get("text", ""),
                "position": hook.get("position", "top-right")
            }))
        return events

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _ev(self, start_ms: float, end_ms: float,
            event_type: str, data: Dict) -> Dict:
        return {
            "start_ms":   round(start_ms, 1),
            "end_ms":     round(end_ms, 1),
            "event_type": event_type,
            "data":       data,
        }

    def _normalize(self, word: str) -> str:
        return re.sub(r"[^\w]", "", word).lower()

    def _find_word_ms(self, trigger: str, occurrence: int = 1) -> Optional[float]:
        """Find the exact occurrence of trigger in self.words. Case-insensitive."""
        if not trigger or not self.words:
            return None
        normalized = self._normalize(trigger)
        first_word = normalized.split()[0] if normalized.split() else normalized
        
        matches = []
        for i, w in enumerate(self.words):
            if first_word in self._normalize(w["word"]):
                matches.append((i, w["start_ms"]))
                
        if not matches:
            return None
            
        target_idx = min(max(occurrence - 1, 0), len(matches) - 1)
        match_i, match_ms = matches[target_idx]
        self._used_indices.add(match_i)
        return match_ms

    def _word_duration_ms(self, trigger: str) -> Optional[float]:
        """Return duration of first matching word."""
        if not trigger or not self.words:
            return None
        normalized = self._normalize(trigger)
        for w in self.words:
            if normalized in self._normalize(w["word"]):
                return w.get("duration_ms", 400)
        return None

    # ──────────────────────────────────────────────────────────────────────
    # V12.5 — Teacher Draw Events
    # ──────────────────────────────────────────────────────────────────────

    def _teacher_draw_events(self) -> List[Dict]:
        """Convert teacher_draw_actions from blueprint into timeline events."""
        events = []
        draw_actions = self.scene.get("teacher_draw_actions", [])
        if not isinstance(draw_actions, list):
            return events
        for action in draw_actions:
            if not isinstance(action, dict):
                continue
            trigger = action.get("trigger_word", "")
            found_ms = self._find_word_ms(trigger) if trigger else None
            start_ms = found_ms if found_ms is not None else self.total_ms * 0.5
            duration_ms = action.get("duration_ms", 2000)
            action_type = action.get("action_type", "underline")
            events.append(self._ev(start_ms, start_ms + duration_ms,
                f"teacher_{action_type}", {
                    "target_selector": action.get("target_selector", ""),
                    "color": action.get("color", "#C9B99A"),
                    "draw_duration_sec": action.get("draw_duration_sec", 0.6),
                    "bbox": action.get("bbox"),
                    "text": action.get("text", ""),
                    "position_x": action.get("position_x", 0.6),
                    "position_y": action.get("position_y", 0.3),
                    "duration_ms": duration_ms,
                    "from_bbox": action.get("from_bbox"),
                    "to_bbox": action.get("to_bbox"),
                }))
        return events

    def _diagram_flow_events(self) -> List[Dict]:
        """Convert diagram_flow_actions into animated particle events."""
        events = []
        flow_actions = self.scene.get("diagram_flow_actions", [])
        if not isinstance(flow_actions, list):
            return events
        for flow in flow_actions:
            if not isinstance(flow, dict):
                continue
            trigger = flow.get("trigger_word", "")
            found_ms = self._find_word_ms(trigger) if trigger else None
            start_ms = found_ms if found_ms is not None else self.total_ms * 0.4
            duration_ms = flow.get("duration_ms", 1500)
            events.append(self._ev(start_ms, start_ms + duration_ms,
                "diagram_flow_animate", {
                    "from_component": flow.get("from", ""),
                    "to_component": flow.get("to", ""),
                    "path_id": f"flow_{flow.get('from', '')}_{flow.get('to', '')}",
                    "duration_ms": duration_ms,
                    "loop": flow.get("loop", False),
                    "particle_color": flow.get("color", "#4F8EF7"),
                }))
        return events

    def _component_highlight_events(self) -> List[Dict]:
        """Auto-highlight diagram components in teaching sequence."""
        events = []
        components = self.scene.get("diagram_components", [])
        if not isinstance(components, list):
            return events
        sorted_comps = sorted(
            [c for c in components if isinstance(c, dict)],
            key=lambda c: c.get("explanation_order", 99)
        )
        for comp in sorted_comps:
            trigger = comp.get("trigger_keyword", "")
            found_ms = self._find_word_ms(trigger) if trigger else None
            start_ms = found_ms if found_ms is not None else self.total_ms * 0.5
            bbox = comp.get("bbox")
            if not bbox:
                continue
            events.append(self._ev(start_ms, start_ms + 2500,
                "diagram_component_highlight", {
                    "component_id": comp.get("id", ""),
                    "bbox": bbox,
                    "label": comp.get("label", ""),
                    "color": comp.get("highlight_color_hex", "#C9B99A"),
                }))
            # Pointer after highlight
            events.append(self._ev(start_ms + 200, start_ms + 2200,
                "spatial_pointer_to", {
                    "bbox": bbox,
                    "label": comp.get("label", ""),
                }))
        return events

    # ──────────────────────────────────────────────────────────────────────
    # V13 — Diagram 5-Step Teaching Sequence
    # ──────────────────────────────────────────────────────────────────────

    def _diagram_teaching_sequence(self) -> List[Dict]:
        """Convert diagram_teaching_sequence from Blueprint V5 into timed events."""
        events = []
        sequence = self.scene.get("diagram_teaching_sequence", [])
        if not isinstance(sequence, list) or not sequence:
            return events

        # Calculate start time — after diagram enters (~35% into scene)
        base_ms = self.total_ms * 0.35
        cursor_ms = base_ms

        for step in sequence:
            if not isinstance(step, dict):
                continue

            step_type = step.get("step", "")
            duration_sec = step.get("duration_sec", 2.5)
            duration_ms = duration_sec * 1000
            narration_cue = step.get("narration_cue", "")

            # Try to sync with narration using first 2 words of cue
            cue_words = narration_cue.split()[:2]
            synced_ms = None
            for word in cue_words:
                synced_ms = self._find_word_ms(word)
                if synced_ms is not None:
                    break
            start_ms = synced_ms if synced_ms is not None else cursor_ms

            if step_type == "overview":
                # Full diagram zoom-out view
                events.append(self._ev(start_ms, start_ms + duration_ms,
                    "diagram_zoom_reset", {"smooth": True}))

            elif step_type == "entry_point":
                comp_id = step.get("component_id", "")
                events.append(self._ev(start_ms, start_ms + duration_ms,
                    "diagram_component_highlight", {
                        "component_id": comp_id,
                        "bbox": step.get("bbox", [0.1, 0.1, 0.3, 0.3]),
                        "label": comp_id.replace("_", " ").title(),
                        "color": "#FFD700",
                    }))
                events.append(self._ev(start_ms + 200, start_ms + duration_ms - 200,
                    "teacher_circle", {
                        "bbox": step.get("bbox", [0.1, 0.1, 0.3, 0.3]),
                        "color": "#FFD700", "duration_ms": duration_ms,
                    }))

            elif step_type == "flow":
                from_comp = step.get("from", "")
                to_comp = step.get("to", "")
                events.append(self._ev(start_ms, start_ms + duration_ms,
                    "diagram_flow_animate", {
                        "from_component": from_comp,
                        "to_component": to_comp,
                        "path_id": f"flow_{from_comp}_{to_comp}",
                        "duration_ms": duration_ms,
                        "loop": False,
                        "particle_color": "#4F8EF7",
                    }))

            elif step_type == "key_insight":
                comp_id = step.get("component_id", "")
                events.append(self._ev(start_ms, start_ms + duration_ms,
                    "diagram_component_highlight", {
                        "component_id": comp_id,
                        "bbox": step.get("bbox", [0.3, 0.3, 0.4, 0.3]),
                        "label": comp_id.replace("_", " ").title(),
                        "color": "#FF6B35",
                    }))
                events.append(self._ev(start_ms + 300, start_ms + duration_ms,
                    "teacher_laser", {
                        "position_x": 0.5, "position_y": 0.4,
                        "duration_ms": duration_ms - 300,
                    }))

            elif step_type == "synthesis":
                events.append(self._ev(start_ms, start_ms + duration_ms,
                    "diagram_zoom_reset", {"smooth": True}))
                events.append(self._ev(start_ms + 500, start_ms + duration_ms,
                    "teacher_erase", {"duration_ms": 500}))

            cursor_ms = start_ms + duration_ms + 200  # 200ms gap between steps

        return events

    # ──────────────────────────────────────────────────────────────────────
    # V13 — ViMax Shot Planning (Layout Shifts)
    # ──────────────────────────────────────────────────────────────────────

    def _shot_plan_events(self) -> List[Dict]:
        """Convert shot_plan from Blueprint V5 into layout_shift events."""
        events = []
        shot_plan = self.scene.get("shot_plan", [])
        if not isinstance(shot_plan, list):
            return events

        for shot in shot_plan:
            if not isinstance(shot, dict):
                continue
            start_pct = shot.get("start_pct", 0)
            layout = shot.get("layout", "balanced")
            start_ms = self.total_ms * start_pct
            end_ms = self.total_ms * shot.get("end_pct", 1.0)

            events.append(self._ev(start_ms, end_ms, "layout_shift", {
                "layout": layout,
                "shot_name": shot.get("shot", "establish"),
            }))

        return events

    # ──────────────────────────────────────────────────────────────────────
    # V13 — Cognitive Load Optimizer
    # ──────────────────────────────────────────────────────────────────────

    _MAJOR_EVENTS = {
        "bullet_enter", "bullet_active", "diagram_pan_zoom",
        "teacher_write", "teacher_circle", "teacher_underline",
        "attention_hook", "diagram_component_highlight",
        "layout_shift",
    }

    def _optimize_cognitive_load(self, events: List[Dict]) -> List[Dict]:
        """
        Post-process events to enforce cognitive load rules:
        1. No two major animations within 400ms of each other
        2. 800ms breathe moment after each bullet_active
        3. Auto-insert subtitle_dim during zoom_word_glow
        """
        if not events:
            return events

        # Sort first to process in order
        events.sort(key=lambda e: e["start_ms"])

        # Rule 1: Deconflict major events (delay second one by 400ms)
        major_events = [e for e in events if e["event_type"] in self._MAJOR_EVENTS]
        for i in range(1, len(major_events)):
            prev = major_events[i - 1]
            curr = major_events[i]
            gap = curr["start_ms"] - prev["start_ms"]
            if 0 < gap < 400:
                delay = 400 - gap
                curr["start_ms"] += delay
                curr["end_ms"] += delay

        # Rule 2: Breathe moments after bullet_active (push later events)
        bullet_actives = [e for e in events if e["event_type"] == "bullet_active"]
        for ba in bullet_actives:
            ba_end = ba["start_ms"] + 800
            for e in events:
                if e is ba:
                    continue
                if e["event_type"] in self._MAJOR_EVENTS and ba["start_ms"] < e["start_ms"] < ba_end:
                    shift = ba_end - e["start_ms"]
                    e["start_ms"] += shift
                    e["end_ms"] += shift

        # Rule 3: Auto-insert subtitle_dim during zoom_word_glow
        new_events = []
        for e in events:
            if e["event_type"] == "zoom_word_glow":
                new_events.append(self._ev(
                    e["start_ms"], e["end_ms"],
                    "subtitle_dim", {"opacity": 0.3}
                ))
        events.extend(new_events)

        return events
