import sys
import os
import json
import asyncio

# Add backend to path
sys.path.append(os.getcwd())

from app.services.blueprint_pipeline import BlueprintPipeline

def test():
    print("--- Diagnostic: Local Blueprint Pipeline Test ---")
    
    # Simple 1-scene blueprint
    blueprint = {
        "scenes": [
            {
                "scene_id": "test_scene",
                "narration": "Hello this is a high fidelity memory test.",
                "slide_title": "Stability Test",
                "bullets": ["Point 1", "Point 2"],
                "gold_word": "fidelity"
            }
        ]
    }
    
    pipeline = BlueprintPipeline(output_dir="static/videos")
    print(f"Pipeline temp dir: {pipeline.temp_dir}")
    
    try:
        print("Rendering scene...")
        video_path = pipeline.render_blueprint(blueprint)
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
    test()
