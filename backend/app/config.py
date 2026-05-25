"""Application Configuration"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings from .env file"""
    
    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Database
    DATABASE_URL: str = "sqlite:///./smart_study.db"
    SQLALCHEMY_ECHO: bool = False
    
    # Server
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Paths
    STATIC_DIR: str = "static"
    UPLOAD_FOLDER: str = "static/uploads"
    PDF_UPLOAD_FOLDER: str = "static/uploads/pdfs"
    EVIDENCE_FOLDER: str = "static/uploads/evidence"
    MODELS_FOLDER: str = "static/models"
    YOLO_MODEL_PATH: str = "static/models/yolov8n.pt"
    CHROMA_DB_PATH: str = "./chroma_data"
    AUDIO_FOLDER: str = "static/audio"
    VIDEO_FOLDER: str = "static/videos"

    # AI API Keys
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"

    # EchoMimicV2 Colab GPU Service
    # Set to the ngrok URL when Colab is running, or leave empty to disable
    COLAB_ECHOMIMIC_URL: str = ""

    # Asset APIs
    PEXELS_API_KEY: str = "oVo8bcjEf3Ot0WLMuardg1u5Z9hwiJf4Eeq4zi6JGRfs2OoIYf4fynL3"
    GIPHY_API_KEY: str = "NrG3DQ9NyLtX2OJlMx9EjAXFTpKL2qsn"
    STATIC_ASSETS_DIR: str = "static/assets"

    # HeyGen API Key (Overrides Colab if provided)
    HEYGEN_API_KEY: str = ""

    # OmniAvatar Colab GPU Service
    # Set to the ngrok URL when OmniAvatar Colab notebook is running
    COLAB_AVATAR_URL: str = ""
    AVATAR_IMAGE_PATH: str = "static/avatars/teacher_avatar.jpg"
    VIDEO_OUTPUT_DIR: str = "static/videos"

    # SadTalker Colab GPU Service
    # Set to the ngrok URL when SadTalker_Server.ipynb is running in Colab
    # This is SEPARATE from EchoMimicV2 — both can run simultaneously
    COLAB_SADTALKER_URL: str = ""

    # VLM (Vision Language Model) for slide image analysis
    # Uses Groq's LLaMA 4 Scout — free tier, multimodal (text + image)
    VLM_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    
    # Kaggle Distributed Cloud Rendering
    CLOUD_RENDER_URL: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clean up any potential copy-paste whitespaces from env vars
        for attr in ["CLOUD_RENDER_URL", "COLAB_ECHOMIMIC_URL", "COLAB_AVATAR_URL", "COLAB_SADTALKER_URL"]:
            val = getattr(self, attr, None)
            if isinstance(val, str):
                cleaned = val.strip()
                if cleaned != val:
                    print(f"⚠️ [Config] Cleaned leading/trailing whitespace from {attr}!")
                setattr(self, attr, cleaned)

    class Config:
        env_file = ".env"
        case_sensitive = True

# Load settings
settings = Settings()

# Create required directories
def create_required_directories():
    """Create all necessary directories if they don't exist"""
    dirs = [
        settings.UPLOAD_FOLDER,
        settings.PDF_UPLOAD_FOLDER,
        settings.EVIDENCE_FOLDER,
        settings.MODELS_FOLDER,
        settings.CHROMA_DB_PATH,
        settings.AUDIO_FOLDER,
        settings.VIDEO_FOLDER,
        settings.STATIC_ASSETS_DIR,
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
