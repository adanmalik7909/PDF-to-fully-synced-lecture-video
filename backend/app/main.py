"""FastAPI main application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings, create_required_directories
from app.database.db import init_db
from app.utils.logger import log_info, log_error
# Routes will be imported and registered at the end of the file to prevent startup deadlocks
import os
import sys
import asyncio

# Windows Asyncio Fix for Subprocesses (Required for Playwright)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Ensure project root is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
log_info(f"Root directory: {root_dir}")

# Create required directories
create_required_directories()

# Initialize database
try:
    init_db()
except Exception as e:
    log_info(f"Database initialization failed (non-fatal for static file test): {e}")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    log_info("=" * 50)
    log_info("SmartStudyInstructor API Starting...")
    log_info(f"DEBUG MODE: {settings.DEBUG}")
    
    # We no longer use legacy Colab/HeyGen services in the V14 pipeline.
    # The new pipeline uses the Kaggle Cloud Engine for lipsync.

    yield
    log_info("SmartStudyInstructor API Shutting Down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="SmartStudyInstructor API",
    description="MVP Prototype for FYP - Smart Study Instructor System",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount frontend files
from pathlib import Path
base_path = Path(__file__).resolve().parent.parent.parent
frontend_path = str(base_path / "frontend")

if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=frontend_path), name="frontend")
    log_info(f"[OK] Frontend mounted at /assets from {frontend_path}")



# ============ Frontend HTML Routes ============
from fastapi.responses import HTMLResponse

@app.get("/")
async def serve_index():
    html_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Index not found</h1>", status_code=404)

@app.get("/blueprint", response_class=HTMLResponse)
async def serve_blueprint_editor():
    html_path = os.path.join(frontend_path, "blueprint_editor.html")
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content = content.replace('href="css/', 'href="/assets/css/')
        content = content.replace('src="js/', 'src="/assets/js/')
        return HTMLResponse(content=content)
    return HTMLResponse(content="<h1>Blueprint Editor not found</h1>", status_code=404)

# --- DEFERRED ROUTE REGISTRATION ---
# We import and include routes here to ensure they don't block the initial startup sequence
try:
    from app.routes import rag, blueprint_routes
    app.include_router(rag.router)
    app.include_router(blueprint_routes.router)
    log_info("[OK] Core pipeline routes registered successfully (Deferred)")
except Exception as e:
    import traceback
    log_info(f"[CRITICAL] Deferred Route Registration failed: {e}")
    traceback.print_exc()

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "SmartStudyInstructor is alive"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=8000,
        reload=settings.DEBUG
    )
