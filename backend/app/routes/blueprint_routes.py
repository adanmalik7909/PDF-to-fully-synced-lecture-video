from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from app.database.models import User
from app.auth.dependencies import get_current_teacher
from app.rag.llm_client import get_llm_client
from app.rag.rag_service import get_rag_service
from app.services.blueprint_pipeline import BlueprintPipeline
from app.config import settings
from app.utils.logger import log_info, log_error
import os
import json
import uuid

router = APIRouter(prefix="/api/blueprint", tags=["video-blueprint"])

# Job store for tracking blueprint renders
blueprint_jobs = {}

@router.post("/generate-draft")
async def generate_draft_blueprint(
    file: UploadFile = File(None),
    text_input: str = Form(None)
):
    """
    Phase 1: Extracts text + images from PDF, runs VLM vision analysis on each page,
    then asks LLM to generate a 5-scene JSON blueprint enriched with visual understanding.
    Alternatively, accepts raw text for quick testing.
    """
    if not file and not text_input:
        raise HTTPException(status_code=400, detail="Must provide either a PDF file or raw text.")

    text = ""
    extracted_images = []
    vlm_pages = []

    try:
        if file:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are supported.")
                
            # Save temp PDF
            temp_pdf = f"static/uploads/pdfs/temp_{uuid.uuid4().hex}.pdf"
            os.makedirs(os.path.dirname(temp_pdf), exist_ok=True)
            with open(temp_pdf, "wb") as f:
                content = await file.read()
                f.write(content)

            # Extract text
            rag = get_rag_service()
            text = rag.extract_text_from_pdf(temp_pdf)

            # Extract embedded images from PDF
            extracted_images = rag.extract_images_from_pdf(temp_pdf)

            if not text or len(text) < 50:
                os.remove(temp_pdf)
                raise HTTPException(status_code=400, detail="Could not extract enough text from PDF.")

            # ── VLM Vision Analysis (Groq LLaMA 4 Scout) ────────────────────────
            try:
                from app.services.vlm_service import process_pdf_with_vlm, analyze_diagram_with_vlm
                import tempfile
                vlm_temp_dir = tempfile.mkdtemp(prefix="vlm_pages_")
                llm = get_llm_client()
                
                # Analyze full pages
                vlm_pages = process_pdf_with_vlm(temp_pdf, llm, vlm_temp_dir, max_pages=8)
                log_info(f"VLM analysis complete: {len(vlm_pages)} pages analyzed")
                
                # Analyze extracted diagrams for spatial awareness (Limit to 3 to save API time)
                diagram_spatial_data = {}
                if extracted_images:
                    for i, img_path in enumerate(extracted_images[:3]):
                        coords = analyze_diagram_with_vlm(img_path, llm)
                        if coords:
                            diagram_spatial_data[img_path] = coords
                
            except Exception as vlm_err:
                log_error(f"VLM analysis skipped (non-fatal): {vlm_err}")
                diagram_spatial_data = {}
                
        elif text_input:
            text = text_input
            diagram_spatial_data = {}
            log_info("Using provided raw text for blueprint generation.")

        if file:
            os.remove(temp_pdf)

        # Force-reset LLM singleton so a stale MockLLMClient can't persist
        import app.rag.llm_client as _llm_mod
        _llm_mod._llm_client = None

        # ── Blueprint Generation (text + VLM + images) ───────────────────────
        llm = get_llm_client()
        log_info(f"[Blueprint] LLM client type: {type(llm).__name__}")
        
        try:
            from core.pedagogical_engine import PedagogicalEngine
            engine = PedagogicalEngine(llm_client=llm)
            blueprint = engine.generate_blueprint_v5(
                document_text=text,
                extracted_images=extracted_images,
                vlm_pages=vlm_pages,
                diagram_spatial_data=diagram_spatial_data
            )
        except Exception as e:
            log_error(f"PedagogicalEngine failed: {e}")
            blueprint = None

        if not blueprint or not isinstance(blueprint, dict) or not blueprint.get("scenes"):
            log_info("[Blueprint] Falling back to monolithic LLM prompt...")
            blueprint = await llm.generate_video_blueprint(
                document_text=text,
                extracted_images=extracted_images,
                vlm_pages=vlm_pages,
                diagram_spatial_data=diagram_spatial_data
            )

        if not blueprint or not isinstance(blueprint, dict) or not blueprint.get("scenes"):
            raise HTTPException(status_code=500, detail="LLM failed to return a valid blueprint.")

        return JSONResponse(content={
            "status": "success",
            "blueprint": blueprint,
            "vlm_pages_analyzed": len(vlm_pages),
            "extracted_images": extracted_images,  # actual paths, not just count
            "extracted_images_count": len(extracted_images)
        })

    except Exception as e:
        log_error(f"Generate draft failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import requests
import time

async def _render_task(job_id: str, blueprint_json: dict, user_id: int, avatar_path: str = None):
    import asyncio
    import sys
    if sys.platform == 'win32':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except:
            pass
            
    try:
        blueprint_jobs[job_id]["status"] = "processing"
        
        # Define progress callback
        def update_progress(progress_pct: int, step_desc: str):
            blueprint_jobs[job_id]["progress"] = progress_pct
            blueprint_jobs[job_id]["current_step"] = step_desc
            
        # V13 Update: We now ALWAYS run the local pipeline.
        # The pipeline itself is now smart enough to delegate the 
        # heavy LIPSINC work to the Kaggle Cloud URL automatically.
        log_info(f"[{job_id}] Running V14 local-cloud hybrid pipeline...")
        
        # Instantiate pipeline locally
        pipeline = BlueprintPipeline()
        if avatar_path:
            video_path = await pipeline.render_blueprint(blueprint_json, avatar_path=avatar_path, progress_callback=update_progress)
        else:
            video_path = await pipeline.render_blueprint(blueprint_json, progress_callback=update_progress)
        
        if video_path:
            filename = os.path.basename(video_path)
            blueprint_jobs[job_id]["status"] = "completed"
            blueprint_jobs[job_id]["video_url"] = f"/{settings.VIDEO_FOLDER}/{filename}"
            blueprint_jobs[job_id]["progress"] = 100
            blueprint_jobs[job_id]["current_step"] = "Done!"
        else:
            blueprint_jobs[job_id]["status"] = "failed"
            blueprint_jobs[job_id]["error"] = "Pipeline rendering returned None."
            
        pipeline.cleanup()
            
    except Exception as e:
        log_error(f"Render task {job_id} failed: {e}")
        blueprint_jobs[job_id]["status"] = "failed"
        blueprint_jobs[job_id]["error"] = str(e)

@router.post("/assemble")
async def assemble_video_blueprint(
    background_tasks: BackgroundTasks,
    blueprint_data: str = Form(...),
    avatar_file: UploadFile = File(None)
):
    """
    Phase 2 & 3: Accepts the updated JSON draft and pushes it to background rendering.
    """
    try:
        blueprint_json = json.loads(blueprint_data)
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        saved_avatar_path = None
        if avatar_file and avatar_file.filename:
            # Use absolute path to ensure FFmpeg can always find it
            avatar_dir = os.path.abspath("static/uploads/avatars")
            os.makedirs(avatar_dir, exist_ok=True)
            saved_avatar_path = os.path.join(avatar_dir, f"{job_id}_{avatar_file.filename}")
            with open(saved_avatar_path, "wb") as f:
                f.write(await avatar_file.read())
        
        blueprint_jobs[job_id] = {
            "status": "queued",
            "video_url": None,
            "error": None
        }
        
        background_tasks.add_task(_render_task, job_id, blueprint_json, 1, saved_avatar_path)
        
        return JSONResponse(content={"status": "success", "job_id": job_id})
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON blueprint.")
    except Exception as e:
        log_error(f"Assemble fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_blueprint_status(job_id: str):
    if job_id not in blueprint_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(content=blueprint_jobs[job_id])
