# -*- coding: utf-8 -*-
"""
SmartStudyInstructor V13 — Pedagogical Intelligence Engine
3-Agent LLM Pipeline: Content Analyst → Pedagogical Planner → Scene Director

Uses Groq (LLaMA 3.3 70B) for fast, free inference.
Each agent has a focused ~1500-token prompt instead of one monolithic 4000-token prompt.
"""
import json
from typing import Dict, List, Optional
from app.utils.logger import log_info, log_error


class PedagogicalEngine:
    """
    Splits the blueprint generation into 3 focused LLM passes:
    1. Content Analysis — understand structure, concepts, difficulty
    2. Pedagogy Planning — decide teaching strategy per concept
    3. Scene Direction — generate the final Blueprint V5 JSON
    """

    def __init__(self, llm_client):
        """
        Args:
            llm_client: Any LLMClient instance (GroqClient or GeminiClient)
                        that has a _chat(system, user, max_tokens) method.
        """
        self._llm = llm_client

    # ──────────────────────────────────────────────────────────────────────
    # Agent 1: Content Analyst
    # ──────────────────────────────────────────────────────────────────────

    def analyze_content(self, document_text: str, vlm_pages: List[Dict] = None) -> Dict:
        """
        Analyzes raw document text and returns a structured content map.
        """
        vlm_context = ""
        if vlm_pages:
            summaries = []
            for p in vlm_pages:
                summaries.append(f"[Page {p.get('page_num')} | {p.get('page_type')}] {p.get('vlm_description', '')}")
            vlm_context = "\n=== VISUAL ANALYSIS ===\n" + "\n".join(summaries)

        system = """You are a Content Analyst for educational material. Analyze the provided lecture PDF text and return ONLY a JSON object. Do not write any explanation outside the JSON. Your JSON must contain: course_title (string), main_topics (array of strings), concept_dependency_graph (array of objects where each has "concept" and "depends_on" as an array), difficulty_progression (array of "beginner"/"intermediate"/"advanced" per topic), diagram_page_numbers (array of integers), prerequisite_gaps (string describing what prior knowledge students need), and total_estimated_scenes (integer, one scene per major concept, max 45 seconds each)."""

        user = f"{vlm_context}\n\nDOCUMENT:\n{document_text[:8000]}"
        raw = self._llm._chat(system, user, max_tokens=2048)

        try:
            result = self._extract_json(raw)
            log_info(f"[V13 Agent 1] Content Analysis: {result.get('total_concepts', '?')} concepts found")
            return result
        except Exception as e:
            log_error(f"[V13 Agent 1] Parse error: {e}")
            return {"concept_hierarchy": [], "total_concepts": 0, "suggested_scene_count": 5,
                    "title": "Unknown", "core_narrative": "", "document_type": "textbook"}

    # ──────────────────────────────────────────────────────────────────────
    # Agent 2: Pedagogical Planner
    # ──────────────────────────────────────────────────────────────────────

    def plan_pedagogy(self, content_analysis: Dict, document_text: str) -> Dict:
        """
        Given the content analysis, decides HOW to teach each concept.
        """
        system = """You are a Pedagogical Planner trained in Cognitive Load Theory and Mayer's Multimedia Learning principles. You receive a content analysis JSON and must return a teaching strategy JSON. For each concept in the input, decide: explanation_strategy (one of: "analogy_first", "example_first", "problem_first", "visual_first", "definition_then_example"), expected_confusion_point (the specific thing students will misunderstand), aha_moment_trigger (the exact type of example or analogy that will create understanding), pacing_note ("fast"/"normal"/"slow" with reason), and animation_priority ("diagram"/"bullets"/"both"). Also return global_pacing_notes string and total_video_duration_estimate_minutes float. Return ONLY JSON, no explanation."""

        concepts_summary = json.dumps(content_analysis, indent=2)
        user = f"CONTENT ANALYSIS:\n{concepts_summary}\n\nDOCUMENT EXCERPT:\n{document_text[:4000]}"
        raw = self._llm._chat(system, user, max_tokens=2048)

        try:
            result = self._extract_json(raw)
            strategies = result.get("teaching_strategies", [])
            log_info(f"[V13 Agent 2] Pedagogy Plan: {len(strategies)} strategies, arc={result.get('narrative_arc', '?')}")
            return result
        except Exception as e:
            log_error(f"[V13 Agent 2] Parse error: {e}")
            return {"teaching_strategies": [], "scene_flow": [], "narrative_arc": "building_blocks"}

    # ──────────────────────────────────────────────────────────────────────
    # Agent 3: Scene Director (produces the final Blueprint V5)
    # ──────────────────────────────────────────────────────────────────────

    def direct_scenes(
        self,
        pedagogy_plan: Dict,
        content_analysis: Dict,
        document_text: str,
        extracted_images: List[str] = None,
        diagram_spatial_data: Dict = None,
    ) -> Dict:
        """
        Generates the final Blueprint V5 JSON using pedagogy + content analysis.
        This is the Scene Director — it choreographs the visual experience with 
        high-end pedagogical rules.
        """
        # Build image context
        images_context = ""
        if extracted_images:
            img_list = ""
            for img in extracted_images:
                img_list += f"  - {img}\n"
                if diagram_spatial_data and img in diagram_spatial_data:
                    vlm_res = diagram_spatial_data[img]
                    visual = vlm_res.get("visual", {})
                    components = visual.get("components", [])
                    if components:
                        img_list += f"    Spatial Components:\n"
                        for comp in components:
                            label = comp.get("label", "Unknown")
                            bbox = comp.get("bbox", [])
                            desc = comp.get("description", "")
                            img_list += f"      * {label}: {bbox} ({desc})\n"
            images_context = (
                f"\n=== EXTRACTED DIAGRAMS ({len(extracted_images)} images) ===\n"
                f"You MUST reference them in diagram_refs using EXACT paths:\n"
                f"{img_list}\n"
            )

        strategies_json = json.dumps(pedagogy_plan.get("teaching_strategies", []), indent=2)

        system = """You are an expert Educational Video Director and a Master University Professor.
Your goal is to transform dry document text into a highly detailed, extremely efficient, and deeply engaging lecture video script.

═══ NARRATION RULES (MASTER TEACHER CADENCE) ═══
- DEEP YET EFFICIENT EXPLANATION: You must explain the core mechanics of the topic in detail. Break down complex ideas step-by-step so a beginner can fully understand them without wasting a single word.
- THE "WHY": Always explain *why* something works or *why* it matters, not just what it is.
- ANALOGY: Every scene MUST include one brilliant, relatable real-world analogy that perfectly maps to the technical concept ("Think of this like a...").
- PASSIONATE HOOK: First sentence MUST be a surprising fact, a paradox, or a thought-provoking hook question (never "Today we will learn about X").
- DIRECT ENGAGEMENT: Speak directly to the student like a passionate mentor. Use phrases like "Now, here is the secret..." or "Pay close attention to this next part, because it changes everything."
- CADENCE & EMPHASIS: Build suspense before key terms: "...and this elegant solution, THIS is what we call — [key term]."
- TEASER: End every scene by planting a seed of curiosity for the next concept.
- LENGTH: Narration should be richly detailed, around 180-280 words per scene.

═══ OUTPUT FORMAT ═══
Return a JSON object with a "scenes" array. Each scene MUST have:
- scene_id: "scene_01" etc.
- heading_left: A hook question or engaging title.
- gold_word: One key word from heading_left to highlight.
- heading_right: The formal academic name of the concept.
- narration: The full spoken script (no SSML).
- takeaway: A one-sentence memorable summary.
- bullets: Array of 3-4 objects: {"text": "Concise point", "zoom_word": "term", "num": "01"}.
- has_diagram: Boolean.
- diagram_refs: Array with EXACT path of an image if relevant.
- diagram_trigger_word: Word in narration that triggers the image.

Return ONLY JSON."""

        user = (
            f"PEDAGOGICAL PLAN:\n{strategies_json}\n\n"
            f"{images_context}\n\n"
            f"DOCUMENT CONTENT:\n{document_text[:10000]}"
        )
        raw = self._llm._chat(system, user, max_tokens=8192)

        try:
            result = self._extract_json(raw)
            raw_scenes = result.get("scenes", [])
            mapped_scenes = []
            
            for i, rs in enumerate(raw_scenes):
                # Ensure all required UI fields are present
                mapped = {
                    "scene_id": rs.get("scene_id", f"scene_{i+1:02d}"),
                    "scene_type": "diagram_focus" if (rs.get("has_diagram") or rs.get("diagram_refs")) else "concept",
                    "heading_left": rs.get("heading_left", rs.get("concept_title", "Topic")),
                    "gold_word": rs.get("gold_word", ""),
                    "heading_right": rs.get("heading_right", rs.get("concept_title", "")),
                    "narration": rs.get("narration", rs.get("narration_script", "")),
                    "takeaway": rs.get("takeaway", ""),
                    "diagram_refs": rs.get("diagram_refs", []),
                    "diagram_trigger_word": rs.get("diagram_trigger_word", "show"),
                    "zoom_words": rs.get("zoom_keywords", []),
                }

                # Fix bullets format
                bullets = []
                for j, b in enumerate(rs.get("bullets", [])):
                    if isinstance(b, dict):
                        bullets.append({
                            "text": b.get("text", ""),
                            "num": b.get("num", f"{j+1:02d}"),
                            "zoom_word": b.get("zoom_word", "")
                        })
                    else:
                        bullets.append({
                            "text": str(b),
                            "num": f"{j+1:02d}",
                            "zoom_word": ""
                        })
                mapped["bullets"] = bullets

                # Auto-assign diagram if needed
                if mapped["scene_type"] == "diagram_focus" and not mapped["diagram_refs"] and extracted_images:
                    mapped["diagram_refs"] = [extracted_images[i % len(extracted_images)]]

                mapped_scenes.append(mapped)
                
            log_info(f"[V13 Agent 3] Scene Direction: {len(mapped_scenes)} scenes choreographed with advanced pedagogy")
            return {"scenes": mapped_scenes}
        except Exception as e:
            log_error(f"[V13 Agent 3] Parse error: {e}")
            return {"scenes": []}
        except Exception as e:
            log_error(f"[V13 Agent 3] Parse error: {e}")
            return {"scenes": []}

    # ──────────────────────────────────────────────────────────────────────
    # Full 3-Agent Pipeline
    # ──────────────────────────────────────────────────────────────────────

    def generate_blueprint_v5(
        self,
        document_text: str,
        extracted_images: List[str] = None,
        vlm_pages: List[Dict] = None,
        diagram_spatial_data: Dict = None,
    ) -> Dict:
        """
        Runs the full 3-agent pipeline:
        Agent 1 (Content Analyst) → Agent 2 (Pedagogical Planner) → Agent 3 (Scene Director)
        """
        log_info("=" * 60)
        log_info("[V13] Pedagogical Engine — 3-Agent Pipeline Starting")
        log_info("=" * 60)

        # Agent 1: Analyze content
        log_info("[V13] Agent 1/3: Content Analyst...")
        content_analysis = self.analyze_content(document_text, vlm_pages)

        # Guard: fall back if result is completely empty (any non-empty dict is fine)
        if not content_analysis or not any(content_analysis.values()):
            log_error("[V13] Agent 1 returned empty analysis — falling back to single-prompt")
            return None  # Caller will fall back to legacy prompt

        # Agent 2: Plan pedagogy
        log_info("[V13] Agent 2/3: Pedagogical Planner...")
        pedagogy_plan = self.plan_pedagogy(content_analysis, document_text)

        # Guard: fall back if result is completely empty
        if not pedagogy_plan or not any(pedagogy_plan.values()):
            log_error("[V13] Agent 2 returned empty plan — falling back to single-prompt")
            return None

        # Agent 3: Direct scenes
        log_info("[V13] Agent 3/3: Scene Director...")
        blueprint = self.direct_scenes(
            pedagogy_plan=pedagogy_plan,
            content_analysis=content_analysis,
            document_text=document_text,
            extracted_images=extracted_images,
            diagram_spatial_data=diagram_spatial_data,
        )

        if not blueprint.get("scenes"):
            log_error("[V13] Agent 3 returned no scenes — falling back to single-prompt")
            return None

        # Enrich blueprint with pedagogical metadata
        for scene in blueprint.get("scenes", []):
            scene["_pedagogical_engine"] = "v13_3agent"

        log_info(f"[V13] 3-Agent Pipeline Complete: {len(blueprint.get('scenes', []))} scenes")
        return blueprint

    # ──────────────────────────────────────────────────────────────────────
    # Utils
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(raw: str) -> Dict:
        """Robust JSON extraction with balanced bracket search."""
        if raw.startswith("ERROR:"):
            raise ValueError(f"LLM API Error: {raw}")
            
        start_idx = raw.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")

        bracket_count = 0
        end_idx = -1
        for i in range(start_idx, len(raw)):
            if raw[i] == '{':
                bracket_count += 1
            elif raw[i] == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

        if end_idx == -1:
            raise ValueError("Incomplete JSON — LLM truncated response")

        return json.loads(raw[start_idx:end_idx])
