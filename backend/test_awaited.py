import asyncio
import os
import sys

sys.path.append(os.getcwd())

from app.services.blueprint_pipeline import BlueprintPipeline

async def main():
    blueprint = {
        "scenes": [
            {
                "scene_id": "test_scene",
                "narration": "Hello this is a high fidelity memory test.",
                "topic": "Diagnostic",
                "heading_left": "Stability Test",
                "gold_word": "fidelity",
                "heading_right": "Awaited Render",
                "bullets": [{"num": "01", "text": "Point 1", "zoom_word": "Point", "trigger_word": "Hello"}],
                "zoom_words": ["fidelity"],
                "diagram_refs": ["static/avatars/my_avatar.jpg"],
                "diagram_paths": ["static/avatars/my_avatar.jpg"],
                "diagram_data": {
                    "regions": [
                        {
                            "region_id": "step1",
                            "bbox": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.3},
                            "role": "process",
                            "description": "First step",
                            "explanation_order": 1,
                            "trigger_keyword": "Hello",
                            "highlight_color": "blue"
                        },
                        {
                            "region_id": "step2",
                            "bbox": {"x": 0.5, "y": 0.5, "width": 0.4, "height": 0.4},
                            "role": "output",
                            "description": "Second step",
                            "explanation_order": 2,
                            "trigger_keyword": "memory",
                            "highlight_color": "green"
                        }
                    ],
                    "connectors": [
                        {
                            "connector_id": "arrow_step1_to_step2",
                            "from_region_id": "step1",
                            "to_region_id": "step2",
                            "type": "dashed",
                            "path": [
                                {"x": 0.25, "y": 0.25},
                                {"x": 0.4, "y": 0.25},
                                {"x": 0.4, "y": 0.7},
                                {"x": 0.7, "y": 0.7}
                            ],
                            "label": "process transition",
                            "explanation_order": 1,
                            "trigger_keyword": "high"
                        }
                    ]
                }
            }
        ]
    }
    
    pipeline = BlueprintPipeline(output_dir="static/videos")
    print(f"Pipeline temp dir: {pipeline.temp_dir}")
    try:
        print("Rendering scene...")
        video_path = await pipeline.render_blueprint(blueprint)
        if video_path:
            print(f"SUCCESS: Video generated at {video_path}")
        else:
            print("FAILED: Video generated None")
    except Exception as e:
        print(f"CRASH: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pipeline.cleanup()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())
