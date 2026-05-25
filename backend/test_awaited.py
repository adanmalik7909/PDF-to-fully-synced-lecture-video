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
                "zoom_words": ["fidelity"]
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
