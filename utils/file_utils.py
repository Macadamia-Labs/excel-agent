import tempfile
import shutil
import os
from fastapi import UploadFile

async def save_upload_file_tmp(upload_file: UploadFile, suffix: str) -> str:
    """Saves an uploaded file to a temporary file and returns the path."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(upload_file.file, tmp_file)
            return tmp_file.name
    finally:
        await upload_file.close() # Ensure the file pointer is closed

def cleanup_files(*paths: str):
    """Safely removes the specified files."""
    for path in paths:
        if path: # Ensure path is not None or empty
            try:
                os.remove(path)
            except OSError: 
                # Log error or handle as needed, e.g., file not found
                pass 