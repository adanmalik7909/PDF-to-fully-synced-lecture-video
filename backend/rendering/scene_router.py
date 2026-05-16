# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V10 — Scene Router
Routes Blueprint scenes to the correct Jinja2 template and renders HTML
with the V10 Timeline Data already embedded as window.TIMELINE_DATA.
"""
import os
import json
import jinja2
from typing import Dict, Optional
from app.utils.logger import log_info, log_error

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

TEMPLATE_MAP = {
    "intro":         "intro.html.j2",
    "concept":       "concept.html.j2",
    "diagram_focus": "concept.html.j2",
    "comparison":    "concept.html.j2",   # reuse concept layout
    "process":       "process.html.j2",   # V12: dedicated step-by-step template
    "summary":       "summary.html.j2",
}

AVATAR_CONFIGS = {
    "intro":         {"size": 280, "ring": "#C9B99A", "visible": True},
    "concept":       {"size": 200, "ring": "#4F8EF7", "visible": True},
    "diagram_focus": {"size": 120, "ring": "#1D9E75", "visible": True},
    "comparison":    {"size": 200, "ring": "#4F8EF7", "visible": True},
    "process":       {"size": 200, "ring": "#4F8EF7", "visible": True},
    "summary":       {"size": 260, "ring": "#C9B99A", "visible": True},
}


class SceneRouter:
    """Routes Blueprint scenes to specific Jinja2 HTML templates."""

    def __init__(self, template_dir: str = None):
        tdir = template_dir or TEMPLATE_DIR
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(tdir),
            autoescape=False  # we handle safety ourselves
        )
        import re
        def wordwrap_spans(text):
            if not text:
                return ""
            # Split by whitespace but keep spaces
            words = text.split()
            out = []
            for w in words:
                out.append(f'<span class="word-span">{w}</span>')
            return " ".join(out)
            
        self.jinja_env.filters["wordwrap_spans"] = wordwrap_spans

    def render_scene_html(self, scene: Dict, timeline_data: Dict = None) -> str:
        """
        Renders the final HTML string for the given scene.
        If timeline_data is provided it is embedded as window.TIMELINE_DATA.
        """
        scene_type    = scene.get("scene_type", "concept")
        template_name = TEMPLATE_MAP.get(scene_type, "concept.html.j2")
        # Allow pipeline to override avatar_config (e.g. to hide static avatar)
        avatar_config = scene.get("avatar_config") or AVATAR_CONFIGS.get(scene_type, AVATAR_CONFIGS["concept"])

        # Build safe timeline_data for Jinja2 serialisation
        tdata = timeline_data or {
            "scene_id": scene.get("scene_id"),
            "total_duration_ms": scene.get("duration_sec", 10) * 1000,
            "events": [],
        }

        try:
            template = self.jinja_env.get_template(template_name)
            html = template.render(
                scene=scene,
                avatar_config=avatar_config,
                timeline_data=tdata,
            )
            return html
        except Exception as e:
            log_error(f"[SceneRouter] Template render failed ({template_name}): {e}")
            return ""
