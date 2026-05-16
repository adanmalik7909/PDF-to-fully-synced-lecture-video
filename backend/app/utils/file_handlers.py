"""File handling utilities"""
import os
from pathlib import Path
from datetime import datetime
from app.config import settings
from app.utils.logger import log_info, log_error

def save_uploaded_file(file, folder: str) -> str:
    """
    Save uploaded file and return filepath
    
    Args:
        file: UploadFile from FastAPI
        folder: target folder (pdf_upload_folder or evidence_folder)
    
    Returns:
        filepath relative to backend root
    """
    try:
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        filename = timestamp + file.filename
        
        # Full path
        filepath = os.path.join(folder, filename)
        
        # Create directory if not exists
        Path(folder).mkdir(parents=True, exist_ok=True)
        
        # Save file
        with open(filepath, "wb") as f:
            content = file.file.read()
            f.write(content)
        
        log_info(f"File saved: {filepath}")
        return filepath
    
    except Exception as e:
        log_error(f"Error saving file: {str(e)}", exc_info=True)
        raise

def delete_file(filepath: str) -> bool:
    """Delete a file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log_info(f"File deleted: {filepath}")
            return True
        return False
    except Exception as e:
        log_error(f"Error deleting file {filepath}: {str(e)}", exc_info=True)
        return False

def file_exists(filepath: str) -> bool:
    """Check if file exists"""
    return os.path.exists(filepath)

def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        log_error(f"Error getting file size: {str(e)}")
        return 0
