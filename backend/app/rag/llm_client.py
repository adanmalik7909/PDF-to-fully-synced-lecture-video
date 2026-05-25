"""LLM Client - Abstraction layer for different LLM providers"""
import os
from typing import Optional, List, Dict
from abc import ABC, abstractmethod
import json
from app.utils.logger import log_info, log_error, log_debug

class LLMClient(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_answer(self, question: str, context: str) -> str:
        """Generate an answer based on question and context"""
        pass
    
    @abstractmethod
    async def generate_lecture_script(
        self,
        content_title: str,
        content_summary: str,
        objectives: List[str]
    ) -> Dict:
        """Generate structured lecture script"""
        pass
    
    @abstractmethod
    async def generate_quiz(
        self,
        content_summary: str,
        difficulty: str,
        num_questions: int
    ) -> Dict:
        """Generate quiz questions"""
        pass
    
    @abstractmethod
    async def generate_summary(self, content: str) -> str:
        """Generate a summary of content"""
        pass

    @abstractmethod
    async def generate_video_script(
        self, 
        context_text: str, 
        duration_minutes: int, 
        target_audience: str = "students"
    ) -> str:
        """Generate a spoken video script based on context"""
        pass
    @abstractmethod
    def _chat(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Internal chat helper (sync)"""
        pass

    async def generate_video_blueprint(
        self,
        document_text: str,
        extracted_images: List[str] = None,
        vlm_pages: List[Dict] = None,
        diagram_spatial_data: Dict = None
    ) -> Dict:
        """
        V10/V11: Generate a Timeline-Driven Director's Blueprint JSON.
        Every field feeds directly into TTS Engine, TimelineBuilder, and Jinja2 templates.
        
        Post-processing: auto-injects extracted PDF images into scenes that
        have empty diagram_refs, so diagrams ALWAYS appear in the video.
        """
        vlm_context = ""
        if vlm_pages:
            page_summaries = []
            for p in vlm_pages:
                entry = f"[Page {p.get('page_num')} | {p.get('page_type')}] {p.get('vlm_description', '')}"
                page_summaries.append(entry)
            vlm_context = "\n=== VLM ANALYSIS ===\n" + "\n".join(page_summaries)

        # Build explicit image list for the LLM with spatial coordinates
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
                f"These diagram/figure images were extracted from the PDF.\n"
                f"You MUST reference them in diagram_refs using their EXACT paths:\n"
                f"{img_list}\n"
                f"Distribute them across your concept and diagram_focus scenes.\n"
            )

        system = """You are an expert educational video director and university professor (think Richard Feynman meets Khan Academy).
Create a Director's Blueprint JSON for a lecture video. Generate 4-6 scenes covering the topic thoroughly.

═══ NARRATION RULES (CRITICAL — TEACHING CADENCE) ═══
- First sentence = a surprising fact or question (NEVER start with the topic title)
- Speak like a passionate, energetic professor actively pointing to a whiteboard — NOT a bullet reader. Speak directly to the listener ("Let's look at this...", "Notice how...", "Now, let's trace..."). Use expressions like "Look at this center box highlighted right here..." or "Let's circle this term..." to guide the student's eyes.
- TEACHING CADENCE: Before every zoom_word, build suspense:
  "...and this, THIS is what we call — backpropagation. Remember this term."
- DIAGRAM TRANSITIONS & SPATIAL GUIDE: Before showing diagram say "Let me show you exactly how this works."
  Before each component say "Now look at this part right here..." or "Pay attention to..." and describe their visual spatial location ("upper right", "middle column", "lower branch") step-by-step as you explain the diagram.
  After last component say "So when you step back and look at the whole picture..."
- Include one real-world analogy per scene: "Think of it like a factory assembly line..."
- End every scene with a teaser: "Now that we understand X, let us see what drives it..."
- narration must be 120-200 words per scene
- Do NOT include SSML tags — write plain spoken English only

═══ BULLET FORMAT (STRICT — NEVER DEVIATE) ═══
bullets MUST ALWAYS be an array of OBJECTS. NEVER output bullets as plain strings.
CORRECT:   "bullets": [{"num": "01", "text": "The concept explained", "zoom_word": "key term", "trigger_word": "word", "entrance": "slide_left"}]
INCORRECT: "bullets": ["The concept explained", "Another point"]

═══ DIAGRAM CHOREOGRAPHY RULES (CRITICAL) ═══
- If extracted diagram images are listed, you MUST populate diagram_refs with their EXACT file paths
- Assign at least one diagram to a "diagram_focus" scene type
- Distribute remaining diagrams across "concept" scenes
- For EVERY diagram scene, generate visual_events as a WALKTHROUGH CHAIN:
  1. First event: action "overview" — show full diagram (trigger_word: "show you")
  2. For each component the teacher explains: action "highlight_and_zoom" with EXACT coordinates
  3. Between connected components: action "draw_arrow" with from/to coordinates
  4. Last event: action "zoom_out" — return to full view (trigger_word: "whole picture")
- The narration MUST mention each component by name so trigger_words work
- If NO images are available, leave diagram_refs as empty []

═══ HEADING INTELLIGENCE ═══
- Generate at least 2 heading_actions per scene:
  1. "heading_zoom" when the topic name (heading_right) is FIRST spoken in narration
  2. "heading_underline" when the heading concept is referenced later

═══ OUTPUT FORMAT ═══
A SINGLE JSON object. NO markdown. NO text before or after. NO explanation.

Schema (output EXACTLY this structure):
{
  "scenes": [
    {
      "scene_id": "scene_1",
      "scene_type": "intro",
      "topic": "Topic Name",
      "heading_left": "Question or hook headline",
      "gold_word": "ONE key word from heading_left to italicize gold",
      "left_description": "2-3 sentences giving the bigger picture context.",
      "heading_right": "The Core Concept Name",
      "narration": "120-200 words of natural spoken professor narration. No lists. No SSML.",
      "bullets": [
        {
          "num": "01",
          "text": "Clear, concise bullet point explaining one idea",
          "zoom_word": "key technical term",
          "trigger_word": "single word from narration that triggers this bullet",
          "entrance": "slide_left"
        }
      ],
      "zoom_words": ["term1", "term2"],
      "diagram_refs": ["static/uploads/diagrams/diagram_abc123.png"],
      "diagram_trigger_word": "word in narration that triggers diagram appearance",
      "visual_events": [
        {
          "action": "overview",
          "trigger_word": "show",
          "target_coords": [0, 0, 1000, 1000],
          "label": "Full Diagram Overview"
        },
        {
          "action": "highlight_and_zoom",
          "trigger_word": "input",
          "target_coords": [50, 100, 200, 150],
          "label": "Input Layer"
        },
        {
          "action": "zoom_out",
          "trigger_word": "picture",
          "target_coords": [0, 0, 1000, 1000],
          "label": "Full View"
        }
      ],
      "heading_actions": [
        {
          "action_type": "heading_zoom",
          "trigger_word": "word that triggers heading emphasis",
          "target": "heading_right",
          "zoom_level": 1.12,
          "duration_ms": 1500
        },
        {
          "action_type": "heading_underline",
          "trigger_word": "second mention of the concept",
          "target": "heading_right",
          "duration_ms": 1200
        }
      ],
      "attention_hooks": [
        {
          "trigger_word": "remember",
          "hook_type": "callout_bubble|did_you_know|quick_recap|warning_box",
          "text": "Key point: activation function = decision maker",
          "position": "top-right|bottom-center|floating"
        }
      ],
      "teacher_draw_actions": [
        {
          "action_type": "underline",
          "trigger_word": "word from narration",
          "target_selector": ".zoom-word-inline",
          "color": "#C9B99A",
          "draw_duration_sec": 0.6,
          "duration_ms": 2000
        },
        {
          "action_type": "circle",
          "trigger_word": "word from narration",
          "bbox": [0.1, 0.2, 0.3, 0.2],
          "color": "#FFD700",
          "duration_ms": 3000
        },
        {
          "action_type": "write",
          "trigger_word": "word from narration",
          "text": "KEY TERM",
          "position_x": 0.6,
          "position_y": 0.3,
          "duration_ms": 2500
        },
        {
          "action_type": "laser",
          "trigger_word": "look",
          "position_x": 0.5,
          "position_y": 0.4,
          "duration_ms": 1500
        }
      ],
      "diagram_flow_actions": [
        {
          "trigger_word": "flows",
          "from": "comp_1",
          "to": "comp_2",
          "duration_ms": 1500,
          "color": "#4F8EF7"
        }
      ],
      "analogy": "One sentence real-world analogy",
      "analogy_image_keyword": "short Pexels search term",
      "analogy_trigger_word": "word in narration that triggers analogy image",
      "teaser_line": "Bridge sentence leading to next scene.",
      "takeaway": "Key Takeaway: one memorable sentence",
      "scene_mood": "intro",
      "background_keyword": "pexels search term for background"
    }
  ]
}

═══ TEACHER DRAW RULES (V12.5) ═══
- Every zoom_word SHOULD get a teacher_draw "underline" action
- For diagram scenes: first mention → "laser" to center, then "circle" each component
- After all components explained → "erase" action (action_type: "erase")
- Key equations or formulas → "write" action near the diagram
- All trigger_words MUST appear verbatim in the narration
- teacher_draw_actions is OPTIONAL — generate it when diagrams are present

scene_type options: intro, concept, diagram_focus, comparison, process, summary
scene_mood options: intro, concept, diagram_focus, comparison, process, summary"""

        # ═══ V13: Try 3-Agent Pedagogical Pipeline first ═══
        try:
            from core.pedagogical_engine import PedagogicalEngine
            ped_engine = PedagogicalEngine(llm_client=self)
            v13_result = ped_engine.generate_blueprint_v5(
                document_text=document_text,
                extracted_images=extracted_images,
                vlm_pages=vlm_pages,
                diagram_spatial_data=diagram_spatial_data,
            )
            if v13_result and v13_result.get("scenes"):
                # Post-process: auto-inject diagrams
                scenes = v13_result.get("scenes", [])
                if extracted_images and scenes:
                    self._auto_inject_diagrams(scenes, extracted_images)
                log_info(f"[V13] 3-Agent Blueprint: {len(scenes)} scenes (Pedagogical Engine)")
                return v13_result
            else:
                log_info("[V13] Pedagogical Engine returned empty — falling back to V12 single-prompt")
        except Exception as e:
            log_error(f"[V13] Pedagogical Engine failed: {e} — falling back to V12 single-prompt")

        # ═══ V12 Fallback: Single-prompt path ═══
        user = f"{vlm_context}\n{images_context}\n\nDOCUMENT CONTENT:\n{document_text[:12000]}"
        raw = self._chat(system, user, max_tokens=8192)

        try:
            # ROBUST JSON EXTRACTION: balanced bracket search
            import json as _json
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
                raise ValueError("Incomplete JSON — LLM truncated the response")

            json_str = raw[start_idx:end_idx]
            result = _json.loads(json_str)

            # ── POST-PROCESSING: Auto-inject diagrams into scenes ────────
            scenes = result.get("scenes", [])
            if extracted_images and scenes:
                self._auto_inject_diagrams(scenes, extracted_images)

            log_info(f"[LLM V10] Blueprint parsed: {len(scenes)} scenes")
            return result
        except Exception as e:
            log_error(f"Blueprint parse error: {e}. Raw (start): {raw[:300]}")
            return {"scenes": []}

    def _auto_inject_diagrams(self, scenes: List[Dict], extracted_images: List[str]):
        """
        Post-LLM: ensure extracted images actually appear in scenes.
        If the LLM left diagram_refs empty, distribute images round-robin
        across concept/diagram_focus/process scenes.
        """
        import os

        # Check which scenes already have diagrams from LLM
        scenes_with_diags = sum(1 for s in scenes if s.get("diagram_refs"))
        if scenes_with_diags >= len(extracted_images):
            log_info(f"[LLM V10] LLM assigned {scenes_with_diags} diagram refs — no injection needed")
            return

        # Filter to only real image files that exist
        valid_images = [img for img in extracted_images if os.path.exists(img)]
        if not valid_images:
            log_info("[LLM V10] No valid extracted images found on disk — skipping injection")
            return

        # Prioritize: diagram_focus > concept > process > comparison > summary
        priority = ["diagram_focus", "concept", "process", "comparison", "summary", "intro"]
        target_scenes = []
        for ptype in priority:
            for s in scenes:
                if s.get("scene_type") == ptype and not s.get("diagram_refs"):
                    target_scenes.append(s)

        if not target_scenes:
            # If all scenes already have diagrams or are intro-only, use concept scenes
            target_scenes = [s for s in scenes if s.get("scene_type") != "intro" and not s.get("diagram_refs")]

        if not target_scenes:
            target_scenes = [s for s in scenes if not s.get("diagram_refs")]

        # Distribute images across target scenes
        for i, img in enumerate(valid_images):
            if not target_scenes:
                break
            target = target_scenes[i % len(target_scenes)]
            if not target.get("diagram_refs"):
                target["diagram_refs"] = []
            target["diagram_refs"].append(img)

        injected = sum(1 for s in scenes if s.get("diagram_refs"))
        log_info(f"[LLM V10] Auto-injected diagrams: {len(valid_images)} images → {injected} scenes")


class GeminiClient(LLMClient):
    """Gemini AI API client implementation"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash"
        self.initialized = False
        
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model_name)
                self.initialized = True
                log_info("[OK] Gemini API initialized")
            except Exception as e:
                log_error(f"Failed to initialize Gemini: {str(e)}")
                self.initialized = False
        else:
            log_info("⚠ No Gemini API key provided - using mock responses")
            self.initialized = False

    def _chat(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Gemini chat helper"""
        if not self.initialized:
            return ""
        try:
            prompt = f"{system}\n\nUSER REQUEST:\n{user}"
            response = self.client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            log_error(f"Gemini _chat error: {e}")
            return ""
    
    async def generate_answer(self, question: str, context: str) -> str:
        """Generate answer using Gemini API"""
        if not self.initialized:
            return self._mock_answer(question)
        
        try:
            prompt = f"""Based on the following context, answer the question concisely.

Context:
{context}

Question: {question}

Answer:"""
            
            log_debug(f"Calling Gemini for question: {question[:50]}...")
            
            response = self.client.generate_content(prompt)
            answer = response.text
            
            log_info(f"[OK] Generated answer ({len(answer)} chars)")
            return answer
        
        except Exception as e:
            log_error(f"Gemini API error: {str(e)}")
            return self._mock_answer(question)
    
    async def generate_lecture_script(
        self,
        content_title: str,
        content_summary: str,
        objectives: List[str]
    ) -> Dict:
        """Generate structured lecture script using Gemini"""
        if not self.initialized:
            return self._mock_lecture_script(content_title, objectives)
        
        try:
            objectives_str = "\n".join([f"{i+1}. {obj}" for i, obj in enumerate(objectives)])
            
            prompt = f"""Create a structured lecture script in JSON format for the following:

Title: {content_title}

Summary: {content_summary}

Learning Objectives:
{objectives_str}

Provide a JSON response with this structure:
{{
  "title": "string",
  "duration_minutes": number,
  "sections": [
    {{
      "section_number": number,
      "title": "string",
      "duration_minutes": number,
      "content": "string",
      "key_points": ["string"],
      "activities": ["string"]
    }}
  ],
  "assessment": {{
    "type": "string",
    "description": "string",
    "rubric": ["string"]
  }},
  "resources": ["string"]
}}

Return ONLY the JSON, no markdown formatting."""
            
            log_debug("Calling Gemini for lecture script generation...")
            
            response = self.client.generate_content(prompt)
            
            # Parse JSON response
            response_text = response.text
            
            # Remove markdown formatting if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            lecture_json = json.loads(response_text.strip())
            log_info("[OK] Generated lecture script")
            
            return lecture_json
        
        except Exception as e:
            log_error(f"Lecture generation error: {str(e)}")
            return self._mock_lecture_script(content_title, objectives)
    
    async def generate_quiz(
        self,
        content_summary: str,
        difficulty: str,
        num_questions: int
    ) -> Dict:
        """Generate quiz questions using Gemini"""
        if not self.initialized:
            return self._mock_quiz(difficulty, num_questions)
        
        try:
            prompt = f"""Create {num_questions} quiz questions in JSON format based on this content:

Content:
{content_summary}

Difficulty: {difficulty} (easy, medium, or hard)

Provide a JSON response with this structure:
{{
  "questions": [
    {{
      "id": number,
      "question_text": "string",
      "question_type": "multiple_choice",
      "difficulty": "string",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "string",
      "explanation": "string"
    }}
  ],
  "metadata": {{
    "total_questions": number,
    "difficulty_level": "string",
    "estimated_time_minutes": number
  }}
}}

Return ONLY the JSON, no markdown formatting."""
            
            log_debug(f"Calling Gemini for quiz generation ({num_questions} questions)...")
            
            response = self.client.generate_content(prompt)
            
            response_text = response.text
            
            # Remove markdown formatting if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            quiz_json = json.loads(response_text.strip())
            log_info(f"[OK] Generated quiz with {num_questions} questions")
            
            return quiz_json
        
        except Exception as e:
            log_error(f"Quiz generation error: {str(e)}")
            return self._mock_quiz(difficulty, num_questions)
    
    async def generate_summary(self, content: str) -> str:
        """Generate summary using Gemini"""
        if not self.initialized:
            return self._mock_summary()
        
        try:
            prompt = f"""Summarize the following content in 2-3 sentences:

{content}

Summary:"""
            
            response = self.client.generate_content(prompt)
            summary = response.text
            
            log_info(f"[OK] Generated summary ({len(summary)} chars)")
            return summary
        
        except Exception as e:
            log_error(f"Summary generation error: {str(e)}")
            return self._mock_summary()

    async def generate_video_script(self, context_text: str, duration_minutes: int, target_audience: str = "students") -> str:
        """Generate a spoken video script using Gemini"""
        if not self.initialized:
            return await self._mock_video_script(context_text, duration_minutes, target_audience)

        try:
            # Estimate word count: ~150 words per minute
            target_words = duration_minutes * 150
            
            prompt = f"""You are an expert teacher creating a script for an educational video. 
            
Context/Source Material:
{context_text[:10000]}... (truncated if too long)

Task: Write a spoken lecture script for a video.
Target Audience: {target_audience}
Target Duration: {duration_minutes} minutes (approx. {target_words} words).

Guidelines:
1. The script should be engaging, clear, and educational.
2. It should be written exactly as it will be spoken by the avatar.
3. Do not include scene directions like [Camera zooms in] or (Pause). Just the spoken text.
4. Start with a brief welcome and topic introduction.
5. Cover the key points from the source material.
6. End with a short summary.

Script:"""

            log_debug(f"Calling Gemini for video script ({duration_minutes} min)...")
            response = self.client.generate_content(prompt)
            script = response.text
            
            # Cleanup common artifacts if any remain
            script = script.replace("**", "").replace("##", "")
            
            log_info(f"[OK] Generated video script ({len(script)} chars)")
            return script

        except Exception as e:
            log_error(f"Video script generation error: {str(e)}")
            return "Error generating script. " + context_text[:500]

    async def _mock_video_script(self, context_text: str, duration_minutes: int, target_audience: str) -> str:
        """Mock video script generator"""
        words = duration_minutes * 150
        return f"Welcome everyone. Today we are going to discuss an interesting topic based on the materials provided. {context_text[:200]}... This concludes our brief overview. Thank you for listening."
    
    # ============ Mock Fallback Responses ============
    
    def _mock_answer(self, question: str) -> str:
        """Generate mock answer for testing"""
        return f"""Based on the provided context, {question.lower()}

Key points from the context:
- The document contains relevant information about the topic
- Multiple perspectives are discussed
- Examples and explanations are provided to illustrate the concepts

In summary, the answer depends on understanding the underlying principles and applying them to the specific question asked."""
    
    def _mock_lecture_script(self, title: str, objectives: List[str]) -> Dict:
        """Generate mock lecture script"""
        return {
            "title": title,
            "duration_minutes": 45,
            "sections": [
                {
                    "section_number": 1,
                    "title": "Introduction",
                    "duration_minutes": 5,
                    "content": "Introduce the main topic and set the context for learning.",
                    "key_points": ["Main concept definition", "Relevance to students"],
                    "activities": ["Welcome and icebreaker"]
                },
                {
                    "section_number": 2,
                    "title": "Core Content",
                    "duration_minutes": 25,
                    "content": "Deep dive into the subject matter with examples and case studies.",
                    "key_points": [f"Objective: {obj}" for obj in objectives[:2]],
                    "activities": ["Presentation", "Visual aids", "Interactive discussion"]
                },
                {
                    "section_number": 3,
                    "title": "Practice & Application",
                    "duration_minutes": 10,
                    "content": "Hands-on activities and practical exercises.",
                    "key_points": ["Real-world applications", "Problem-solving"],
                    "activities": ["Group exercises", "Problem-solving activity"]
                },
                {
                    "section_number": 4,
                    "title": "Conclusion & Q&A",
                    "duration_minutes": 5,
                    "content": "Summarize key points and address questions.",
                    "key_points": ["Key takeaways", "Next steps"],
                    "activities": ["Q&A session", "Summary"]
                }
            ],
            "assessment": {
                "type": "Formative",
                "description": "Continuous assessment through questions and exercises",
                "rubric": ["Understanding of concepts", "Ability to apply knowledge", "Participation"]
            },
            "resources": [
                "Course materials",
                "Reference documents",
                "Example code/files",
                "External resources"
            ]
        }
    
    def _mock_quiz(self, difficulty: str, num_questions: int) -> Dict:
        """Generate mock quiz"""
        questions = []
        
        topics = [
            "What is the main concept discussed?",
            "Which of the following is correct?",
            "How would you apply this concept?",
            "What is an example of this principle?",
            "Why is this important?"
        ]
        
        for i in range(num_questions):
            questions.append({
                "id": i + 1,
                "question_text": topics[i % len(topics)],
                "question_type": "multiple_choice",
                "difficulty": difficulty,
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": f"This is the correct answer because it aligns with the key concepts discussed in the material."
            })
        
        return {
            "questions": questions,
            "metadata": {
                "total_questions": num_questions,
                "difficulty_level": difficulty,
                "estimated_time_minutes": num_questions * 2
            }
        }
    
    def _mock_summary(self) -> str:
        """Generate mock summary"""
        return "This content provides comprehensive information about the topic, covering key concepts, practical applications, and real-world examples that help illustrate the main ideas."


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API keys"""

    def __init__(self):
        self.initialized = False

    def _chat(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Mock chat helper"""
        return json.dumps({
            "scenes": [
                {
                    "scene_id": "mock_1",
                    "scene_type": "concept",
                    "topic": "Mock Topic",
                    "heading_left": "Introduction",
                    "gold_word": "Mock",
                    "heading_right": "Getting Started",
                    "narration": "This is a mock narration for testing the pipeline without an API key.",
                    "bullets": [{"text": "First point", "zoom_word": "First", "trigger_word": "First"}],
                    "timeline": [{"time_hint": 0.5, "action": "heading_glow", "target": "heading_left"}],
                    "diagram_refs": [],
                    "takeaway": "Mock Takeaway",
                    "background_keyword": "abstract technology"
                }
            ]
        })
    
    async def generate_answer(self, question: str, context: str) -> str:
        """Answer from actual context text."""
        # Find most relevant sentence in context
        q_words = set(question.lower().split())
        best, best_score = "", 0
        for sentence in context.replace('\n', '. ').split('.'):
            sentence = sentence.strip()
            if not sentence:
                continue
            score = sum(1 for w in q_words if w in sentence.lower())
            if score > best_score:
                best, best_score = sentence, score
        if best:
            return f"Based on the document: {best}. This relates to your question about {question.lower().rstrip('?')}."
        return f"The document covers: {context[:300]}..."
    
    async def generate_lecture_script(
        self,
        content_title: str,
        content_summary: str,
        objectives: List[str]
    ) -> Dict:
        """Return mock lecture script"""
        return {
            "title": content_title,
            "duration_minutes": 50,
            "sections": [
                {
                    "section_number": 1,
                    "title": "Introduction & Context",
                    "duration_minutes": 5,
                    "content": "Set the stage and introduce key concepts",
                    "key_points": ["Context", "Relevance"],
                    "activities": ["Opening remarks"]
                },
                {
                    "section_number": 2,
                    "title": "Main Content",
                    "duration_minutes": 30,
                    "content": "Detailed exploration of topics",
                    "key_points": objectives,
                    "activities": ["Lecture", "Discussion", "Examples"]
                },
                {
                    "section_number": 3,
                    "title": "Practice & Wrap-up",
                    "duration_minutes": 15,
                    "content": "Apply knowledge and summarize",
                    "key_points": ["Application", "Summary"],
                    "activities": ["Exercises", "Q&A"]
                }
            ],
            "assessment": {
                "type": "Formative",
                "description": "Assessment through exercises and discussion",
                "rubric": ["Participation", "Understanding", "Application"]
            },
            "resources": ["Materials", "References"]
        }
    
    async def generate_quiz(
        self,
        content_summary: str,
        difficulty: str,
        num_questions: int
    ) -> Dict:
        """Return mock quiz"""
        return {
            "questions": [
                {
                    "id": i + 1,
                    "question_text": f"Question {i + 1} about the content",
                    "question_type": "multiple_choice",
                    "difficulty": difficulty,
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "This is the correct answer."
                }
                for i in range(num_questions)
            ],
            "metadata": {
                "total_questions": num_questions,
                "difficulty_level": difficulty,
                "estimated_time_minutes": num_questions * 2
            }
        }
    
    async def generate_summary(self, content: str) -> str:
        """Return mock summary"""
        return f"Summary of provided content with key points highlighted."

    async def generate_video_script(self, context_text: str, duration_minutes: int, target_audience: str = "students") -> str:
        """Generate a real lecture script from the actual context text."""
        return self.generate_script_from_content(context_text)

    def generate_script_from_content(self, content_text: str) -> str:
        """Build a structured lecture script from the actual extracted document text."""
        import re
        # Extract meaningful sentences (no single chars, no page numbers)
        raw = content_text.replace('\r', ' ').replace('\n', ' ')
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw)
                     if len(s.strip()) > 40 and not s.strip().isdigit()]

        total = len(sentences)
        intro_end   = max(1, total // 5)
        core_end    = max(intro_end + 1, total * 3 // 5)
        example_end = max(core_end + 1, total * 4 // 5)

        intro_text   = ' '.join(sentences[:intro_end])[:1200]
        core_text    = ' '.join(sentences[intro_end:core_end])[:2500]
        example_text = ' '.join(sentences[core_end:example_end])[:1200]
        summary_text = ' '.join(sentences[example_end:])[:800]

        if not intro_text:
            intro_text = content_text[:600]

        script = f"""Welcome, everyone. Today we are going to explore an important and fascinating topic drawn directly from your course materials. By the end of this lecture you will have a solid grasp of the core ideas and be able to apply them in real situations. Let us begin.

Introduction.
{intro_text}

Core Concepts.
{core_text if core_text else 'The material introduces several foundational principles that build upon each other.'}

Real-World Examples and Applications.
{example_text if example_text else 'These concepts can be applied in many practical settings that you will encounter in your studies and career.'}

Summary.
{summary_text if summary_text else 'To summarise, we have covered the main points from today\'s material.'} That concludes our lecture for today. Please review the material and bring any questions to our next session. Thank you."""

        return script


class GroqClient(LLMClient):
    """Groq API client using LLaMA 3.3 (llama-3.3-70b-versatile) — fast, free tier available"""

    MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.initialized = False
        try:
            from groq import Groq
            self._client = Groq(api_key=api_key)
            self.initialized = True
            log_info("[OK] GroqClient (LLaMA 3) initialized")
        except Exception as e:
            log_error(f"GroqClient init failed: {e}")

    def _chat(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Internal chat helper."""
        if not self.initialized:
            return ""
        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self._client.chat.completions.create(
                    model=self.MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                import traceback
                error_msg = str(e)
                log_error(f"GroqClient._chat error (attempt {attempt+1}/{max_retries}): {error_msg}")
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    log_info("Rate limited. Waiting 10 seconds before retry...")
                    time.sleep(10)
                elif attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    return f"ERROR: {error_msg}"
        return ""

    # ── Core pipeline method ───────────────────────────────────────────────────

    def generate_script_from_content(self, content_text: str) -> str:
        """Generate a plain-text lecture script from raw document content.

        Professor-style prompt as specified in the project requirements.
        """
        system = (
            "You are an inspiring, friendly, and highly engaging university teacher. "
            "Based on the following document content, write a spoken lecture script. "
            "You are NOT just reading the document; you are TEACHING it to students. "
            "Explain complex concepts, diagrams, and tables in very simple, easy-to-understand words. "
            "Make it a two-way, interactive-feeling lecture (e.g., 'Now, imagine you have...', 'Why does this happen? Let me explain...'). "
            "Structure it smoothly: Introduction → Core Concepts → Examples → Summary. "
            "Write ONLY the exact words you will speak out loud. No stage directions, no markdown headers."
        )
        user = f"Document content:\n\n{content_text[:12000]}"
        result = self._chat(system, user, max_tokens=4096)
        if not result:
            log_error("GroqClient: empty script returned, using fallback")
            return f"Welcome. Today we will study the following content:\n\n{content_text[:500]}"
        log_info(f"[OK] GroqClient: script generated ({len(result)} chars)")
        return result

    def generate_per_slide_script(self, page_num: int, vlm_description: str, raw_text: str) -> str:
        """Generates a strictly 120-word script for ONE specific slide using its exact visual properties."""
        
        system = (
            "You are an energetic university professor giving a lecture. "
            "Write ONE natural teaching paragraph (120-150 words) for this slide.\n\n"
            "Use BOTH the raw extracted slide text and the visual description:\n"
            "- Extract exact numbers/weights directly from the TEXT to avoid mistakes.\n"
            "- Use the VISUAL DESCRIPTION to understand the layout and flow.\n"
            "- Combine them for a 100% accurate, natural explanation.\n\n"
            "RULES:\n"
            "1. Start with what's VISIBLE on slide — specific nodes, edges, weights, diagrams by name\n"
            "2. Explain the concept in plain words — what it means\n"
            "3. Give the intuition — WHY it works this way\n"
            "4. If multiple sums/examples are shown (e.g. 11, 8, 10, 7), COMPARE them and explain why the lowest is chosen.\n"
            "5. If algorithms (Prim's, Kruskal's) are mentioned, briefly explain HOW they work (e.g., Prim's grows one vertex at a time, Kruskal's sorts edges by weight).\n\n"
            "TONE: Conversational, enthusiastic, like talking to students\n"
            "      NOT like reading a textbook\n"
            "      ONE flowing paragraph only\n\n"
            "AVOID:\n"
            "- Numbered lists\n"
            "- Ignoring diagram details\n"
            "- Generic statements with no specifics"
        )

        user = f"Slide number: {page_num}\n\nEXTRACTED TEXT FROM SLIDE:\n{raw_text}\n\nVISUAL DESCRIPTION (VLM):\n{vlm_description}"

        return self._chat(system, user, max_tokens=256)

    def generate_vlm_enriched_script(self, pages_data: list) -> str:
        """Generate a lecture script from VLM-analysed slide descriptions.

        This produces richer scripts because it uses visual understanding
        of diagrams, tables, and mixed content — not just raw text.

        Args:
            pages_data: List of dicts from vlm_service.process_pdf_with_vlm(),
                        each containing 'page_type', 'vlm_description',
                        'lecture_content', 'page_num'.

        Returns:
            Full lecture script string.
        """
        # Build a structured context from all VLM descriptions
        slide_descriptions = []
        for p in pages_data:
            desc = p.get("vlm_description") or p.get("lecture_content") or p.get("raw_text", "")
            if desc.strip():
                slide_descriptions.append(
                    f"[Slide {p['page_num']} — {p.get('page_type', 'mixed')}]: {desc.strip()}"
                )

        if not slide_descriptions:
            return "Welcome. No slide content was available for analysis."

        combined = "\n\n".join(slide_descriptions)

        system = (
            "You are a friendly, passionate, and brilliant university teacher delivering a video lecture. "
            "You have been provided with detailed descriptions of your presentation slides (some are diagrams, some data tables, some text). "
            "Your task is to synthesize these into one continuous, highly engaging spoken script.\n\n"
            "Rules for being an amazing teacher:\n"
            "- Speak naturally and interactively. Ask rhetorical questions like 'Why is this important?'.\n"
            "- Explain things in EASY, simple wording. DO NOT just read the slide descriptions, but DO explicitly mention the specific math, letters (A, B, C, D), and numbers from the slides.\n"
            "- For Diagrams & Flowcharts: Actively point out the specific details on the screen! Say things like, 'As you can see on the screen, node A connects to node B...' DO NOT skip the specific variables, calculations, or visual nodes.\n"
            "- For Tables: Do not quote raw data rows blindly. Explain what the specific data *shows* in simple terms.\n"
            "- IMPORTANT: Do NOT repeat the phrase 'Imagine you are a...' or use the exact same analogy more than once! Pick exactly ONE overarching analogy for the entire lecture and weave it naturally.\n"
            "- Use natural, varied transitions between concepts instead of repetitive phrases. Sound like a real human.\n"
            "- Write ONLY the exact spoken words. NO stage directions, NO markdown headers."
        )

        user = f"Here are the VLM descriptions of each slide:\n\n{combined[:12000]}"

        result = self._chat(system, user, max_tokens=4096)
        if not result:
            log_error("GroqClient: VLM-enriched script generation failed, using fallback")
            # Fallback: join raw descriptions
            return "Welcome everyone. " + " ".join(
                p.get("lecture_content", "")[:200] for p in pages_data
            )

        log_info(f"[OK] GroqClient: VLM-enriched script ({len(result)} chars)")
        return result

    # ── LLMClient interface (other methods with sensible Groq implementations) ─

    async def generate_answer(self, question: str, context: str) -> str:
        system = "You are a helpful university tutor. Answer student questions based on the provided context."
        user = f"Context:\n{context}\n\nQuestion: {question}"
        return self._chat(system, user, max_tokens=512) or f"Based on the material: {question}"

    async def generate_lecture_script(self, content_title: str, content_summary: str, objectives: List[str]) -> Dict:
        objectives_str = "\n".join(f"{i+1}. {o}" for i, o in enumerate(objectives))
        system = "You are a curriculum expert. Return a JSON lecture script following the provided structure."
        user = (
            f"Title: {content_title}\nSummary: {content_summary}\n"
            f"Objectives:\n{objectives_str}\n\n"
            "Return JSON: {\"title\": str, \"duration_minutes\": int, \"sections\": ["
            "{\"section_number\": int, \"title\": str, \"duration_minutes\": int, \"content\": str,"
            " \"key_points\": [str], \"activities\": [str]}], \"assessment\": {\"type\": str,"
            " \"description\": str, \"rubric\": [str]}, \"resources\": [str]}"
        )
        raw = self._chat(system, user, max_tokens=2048)
        try:
            # Strip markdown fences if present
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception:
            return {"title": content_title, "sections": [], "resources": []}

    async def generate_quiz(self, content_summary: str, difficulty: str, num_questions: int) -> Dict:
        system = "You are a quiz creator. Return a JSON quiz."
        user = (
            f"Content: {content_summary[:3000]}\nDifficulty: {difficulty}\nQuestions: {num_questions}\n"
            "Return JSON: {\"questions\": [{\"id\": int, \"question_text\": str, \"options\": [str],"
            " \"correct_answer\": str, \"explanation\": str}], \"metadata\": {\"total_questions\": int,"
            " \"difficulty_level\": str, \"estimated_time_minutes\": int}}"
        )
        raw = self._chat(system, user, max_tokens=2048)
        try:
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception:
            return {"questions": [], "metadata": {"total_questions": 0}}

    async def generate_summary(self, content: str) -> str:
        system = "Summarise the content in 2-3 clear sentences."
        return self._chat(system, content[:6000], max_tokens=256) or "Summary not available."

    async def generate_video_script(self, context_text: str, duration_minutes: int, target_audience: str = "students") -> str:
        system = (
            "You are an expert educator creating a spoken video lecture script. "
            "Write the script as it will be spoken aloud — no stage directions, no markdown."
        )
        target_words = duration_minutes * 150
        user = (
            f"Source material:\n{context_text[:10000]}\n\n"
            f"Target audience: {target_audience}. "
            f"Target duration: {duration_minutes} min (~{target_words} words). "
            "Start with a welcome, cover key points, end with a summary."
        )
        return self._chat(system, user, max_tokens=4096) or context_text[:500]




# Global LLM client instance
_llm_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    """Get or create LLM client instance.

    Priority: Groq (LLaMA 3) → Gemini → Mock
    """
    global _llm_client

    if _llm_client is None:
        try:
            # 1. Try Groq (LLaMA 3)
            from app.config import settings
            groq_key = getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
            if groq_key and groq_key != "your_groq_api_key_here":
                client = GroqClient(api_key=groq_key)
                if client.initialized:
                    _llm_client = client
                    log_info("[OK] Using GroqClient (LLaMA 3)")
                    return _llm_client

            # 2. Try Gemini
            gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
            if gemini_key and gemini_key != "your_gemini_api_key_here":
                client = GeminiClient(api_key=gemini_key)
                if client.initialized:
                    _llm_client = client
                    log_info("[OK] Using GeminiClient")
                    return _llm_client

            # 3. Fallback to mock
            log_info("[WARNING] No API key found — using MockLLMClient")
            _llm_client = MockLLMClient()

        except Exception as e:
            log_error(f"Error initialising LLM client: {e}")
            _llm_client = MockLLMClient()

    return _llm_client

