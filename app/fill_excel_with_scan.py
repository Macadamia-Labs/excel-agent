import uuid
import os
import json
from typing import Tuple, List
from fastapi import UploadFile, HTTPException # Removed BackgroundTasks, no longer needed here

# Import core logic functions
from app.excel_to_markdown import convert_excel_to_markdown
from app.scan_to_markdown import convert_scan_to_markdown
from app.fill_excel_with_json import fill_excel_template

# Import utility functions
from utils.gemini_utils import generate_excel_mapping_from_markdown, get_gemini_client
from utils.file_utils import save_upload_file_tmp, cleanup_files # Added cleanup_files

async def fill_excel_with_scan(
    request_id: uuid.UUID,
    excel_template_path: str, # Changed from UploadFile
    document_path: str, # Changed from UploadFile
    document_filename: str # Added to get original filename for output
) -> Tuple[str, List[str]]: # Return output_path and list of files_to_cleanup
    """
    Core logic to fill an Excel template using data extracted from a scanned document.
    Accepts file paths instead of UploadFile objects.
    Returns the path to the filled Excel file and a list of temporary files created.
    """
    files_to_cleanup = []
    output_path = None
    excel_markdown = None
    scan_markdown = None
    doc_path = document_path # Use passed path
    excel_path = excel_template_path # Use passed path
    raw_text_path = None # Initialize
    table_path = None # Initialize

    try:
        # --- 1. Convert Excel Template to Markdown --- Needs excel_path
        print(f"[{request_id}] Converting Excel template to Markdown: {excel_path}")
        success, excel_markdown_or_error = convert_excel_to_markdown(excel_path)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to convert Excel template: {excel_markdown_or_error}")
        excel_markdown = excel_markdown_or_error
        print(f"[{request_id}] Excel template converted to Markdown successfully.")

        # --- 2. Convert Scan to Markdown --- Needs doc_path
        # Note: convert_scan_to_markdown now needs modification to accept a path 
        # OR we handle the saving/cleanup of the scan doc *before* calling this.
        # Let's assume convert_scan_to_markdown still handles saving its *own* temp files internally
        # and returns the paths for cleanup.
        # We will need to refactor convert_scan_to_markdown separately if it expects UploadFile.
        # *** FOR NOW: Assuming convert_scan_to_markdown accepts a path ***
        # If convert_scan_to_markdown does its own saving from UploadFile, we need to adjust the main.py call flow.
        # Let's adjust the plan: main.py saves the doc, passes the path here.
        # This function will NOT call convert_scan_to_markdown directly.
        # Instead, main.py will call it and pass the scan_markdown and the relevant paths.

        # REVISED PLAN: This function will receive markdown strings, not paths to convert.
        # This simplifies dependencies and focuses this function on mapping + filling.

    except Exception as e:
        print(f"[{request_id}] Error during initial conversion steps: {str(e)}")
        # Cleanup any files created *so far* if an error occurs early
        cleanup_files(*files_to_cleanup)
        raise # Re-raise the exception to be caught by the main route handler

# Let's simplify the refactor first. keep the conversions here for now.
# Assume convert_scan_to_markdown is updated to accept a path.

async def fill_excel_with_scan(
    request_id: uuid.UUID,
    excel_template_path: str, 
    document_path: str,
    document_original_filename: str, # For scan_to_markdown
    excel_original_filename: str # For naming output
) -> Tuple[str, str, str, str, str]: # output_path, excel_path, doc_path, raw_text_path, table_path
    """
    Core logic: Converts both files, gets mapping, fills template.
    Accepts file paths.
    Returns paths to all temporary files created including the final output.
    """
    excel_path = excel_template_path
    doc_path = document_path
    raw_text_path = None
    table_path = None
    output_path = None

    try:
        # --- 1. Convert Excel Template to Markdown --- 
        print(f"[{request_id}] Converting Excel template to Markdown: {excel_path}")
        success, excel_markdown_or_error = convert_excel_to_markdown(excel_path)
        if not success:
            raise RuntimeError(f"Failed to convert Excel template: {excel_markdown_or_error}")
        excel_markdown = excel_markdown_or_error
        print(f"[{request_id}] Excel template converted to Markdown successfully.")

        # --- 2. Convert Scan to Markdown --- 
        # This function needs the UploadFile object based on its current signature.
        # Let's revert the plan slightly: We'll pass the UploadFile object for the document
        # but the path for the already processed Excel template.

    except Exception as e:
        # This function won't handle cleanup directly, main.py will
        print(f"[{request_id}] Error during fill_excel_with_scan pre-processing: {str(e)}")
        raise

# --- Let's stick to the original plan but adjust `convert_scan_to_markdown` --- 
# Assumption: `convert_scan_to_markdown` is refactored to accept a path.
# If not, this edit will fail.

async def fill_excel_with_scan(
    request_id: uuid.UUID,
    excel_template_path: str, # Path to the .xlsx template
    document_path: str, # Path to the saved PDF/image
    document_original_filename: str, # Needed if scan_to_markdown uses it
    excel_original_filename: str # For naming output
) -> Tuple[str, str, str, str, str]: # output_path, excel_path, doc_path, raw_text_path, table_path
    """
    Core logic: Converts both files (from paths), gets mapping, fills template.
    Returns paths to all temporary files created including the final output.
    """
    excel_path = excel_template_path
    doc_path = document_path
    raw_text_path = None
    table_path = None
    output_path = None

    try:
        # --- 1. Convert Excel Template to Markdown --- 
        print(f"[{request_id}] Converting Excel template to Markdown: {excel_path}")
        success, excel_markdown_or_error = convert_excel_to_markdown(excel_path)
        if not success:
            raise RuntimeError(f"Failed to convert Excel template: {excel_markdown_or_error}")
        excel_markdown = excel_markdown_or_error
        print(f"[{request_id}] Excel template converted to Markdown successfully.")

        # --- 2. Convert Scan to Markdown --- 
        # Requires `convert_scan_to_markdown` to accept a file path instead of UploadFile
        # We will *assume* this change is made separately or this part will fail.
        print(f"[{request_id}] Converting Scan document to Markdown: {doc_path}")
        # Mock UploadFile object if necessary, or ideally refactor convert_scan_to_markdown
        # Let's assume refactoring of convert_scan_to_markdown to take path and original filename
        scan_markdown, _, raw_text_path, table_path = await convert_scan_to_markdown(request_id, doc_path, document_original_filename)
        # We get back paths to temp files created by convert_scan_to_markdown
        print(f"[{request_id}] Scan document converted to Markdown successfully.")

        # --- 3. Get Gemini Mapping --- 
        print(f"[{request_id}] Generating data mapping using Gemini...")
        gemini_client = get_gemini_client()
        mapping_json_str = generate_excel_mapping_from_markdown(
            gemini_client,
            excel_markdown, 
            scan_markdown
        )
        
        # The function already returns a dictionary, no need for json.loads
        data_to_insert = mapping_json_str # Rename variable for clarity
        if not isinstance(data_to_insert, dict):
            # This check might still be useful if the previous function fails silently
             raise RuntimeError("Mapping function did not return a valid dictionary object")

        print(f"[{request_id}] Data mapping generated successfully.")

        # --- 4. Fill Excel Template --- 
        output_path = excel_path.replace(".xlsx", "_filled.xlsx")
        print(f"[{request_id}] Filling Excel template: {excel_path} -> {output_path}")
        success, error = fill_excel_template(excel_path, output_path, data_to_insert)
        if not success:
            raise RuntimeError(f"Failed to fill Excel template: {error}")
        print(f"[{request_id}] Excel template filled successfully: {output_path}")

        # Return all relevant paths for cleanup by the caller (main.py)
        return output_path, excel_path, doc_path, raw_text_path, table_path

    except Exception as e:
        print(f"[{request_id}] Error during fill_excel_with_scan processing: {str(e)}")
        # Let main.py handle cleanup based on which paths are not None
        raise # Re-raise exception for main.py to catch 