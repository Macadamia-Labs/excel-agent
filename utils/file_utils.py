import tempfile
import shutil
import os
from fastapi import UploadFile
import pyexcel

async def save_upload_file_tmp(upload_file: UploadFile, suffix: str) -> str:
    """Saves an uploaded file to a temporary file and returns the path."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(upload_file.file, tmp_file)
            return tmp_file.name
    finally:
        await upload_file.close() # Ensure the file pointer is closed

def convert_xls_to_xlsx(xls_path: str) -> str:
    """Converts an XLS file to XLSX format."""
    xlsx_path = xls_path.replace(".xls", ".xlsx")
    try:
        pyexcel.save_book_as(file_name=xls_path, dest_file_name=xlsx_path)
        print(f"Successfully converted {xls_path} to {xlsx_path}")
        return xlsx_path
    except Exception as e:
        print(f"Error converting {xls_path} to {xlsx_path}: {e}")
        raise # Re-raise the exception to be handled by the caller

def cleanup_files(*file_paths):
    """Safely attempts to remove one or more files."""
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError: 
                # Log error or handle as needed, e.g., file not found
                pass 