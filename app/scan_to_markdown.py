from utils.aws_utils import extract_text_and_tables, get_textract_client
from utils.file_utils import save_upload_file_tmp, cleanup_files
from utils.gemini_utils import generate_markdown_from_scan, get_gemini_client
import os
from PIL import Image
import io
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException


async def convert_scan_to_markdown(
    request_id: uuid.UUID,
    document_input: UploadFile | str,
    original_filename: str | None = None # Used if document_input is str
) -> Tuple[str, str, str, str]: # Returns: markdown_content, doc_path, raw_text_path, table_path
    """
    Processes a scanned document (PDF or image) from an UploadFile or a file path.
    Extracts text/tables using AWS Textract, enhances using Gemini, returns Markdown.
    Manages cleanup for internally generated temp files (raw_text, tables).
    The caller is responsible for cleaning up the input doc_path if it was provided as a string.
    Returns: (markdown_content, doc_path, raw_text_path, table_path)
    """
    input_doc_path = None
    saved_doc_path = None # Path if we saved an UploadFile
    raw_text_path = None
    table_path = None
    cleanup_list_internal = [] # Files created *by this function* to clean up

    try:
        # --- 1. Determine Input Path --- 
        if isinstance(document_input, UploadFile):
            document = document_input
            file_ext = os.path.splitext(document.filename)[1].lower()
            print(f"[{request_id}] Saving uploaded document: {document.filename}")
            saved_doc_path = await save_upload_file_tmp(document, suffix=file_ext)
            # This path needs cleanup if we error out before returning
            input_doc_path = saved_doc_path 
            print(f"[{request_id}] Document saved to: {input_doc_path}")
        elif isinstance(document_input, str):
            input_doc_path = document_input
            if not os.path.exists(input_doc_path):
                raise FileNotFoundError(f"Document not found at path: {input_doc_path}")
            print(f"[{request_id}] Processing document from path: {input_doc_path}")
            # Caller is responsible for cleaning up this path
        else:
            raise TypeError("document_input must be UploadFile or str")

        # --- 2. Initialize Clients --- 
        print(f"[{request_id}] Initializing AWS Textract and Google Gemini clients...")
        textract_client = get_textract_client()
        gemini_model = get_gemini_client()

        # --- 3. Process with Textract --- 
        print(f"[{request_id}] Starting Textract processing for: {input_doc_path}")
        # extract_text_and_tables creates and returns paths to temp files
        raw_text_path, table_path = extract_text_and_tables(textract_client, input_doc_path)
        cleanup_list_internal.extend([raw_text_path, table_path]) # Add Textract temps for internal cleanup
        print(f"[{request_id}] Textract processing complete. Raw text: {raw_text_path}, Tables: {table_path}")

        # --- 4. Enhance with Gemini --- 
        print(f"[{request_id}] Starting Gemini enhancement...")
        markdown_content = generate_markdown_from_scan(gemini_model, input_doc_path, raw_text_path, table_path)
        print(f"[{request_id}] Gemini enhancement complete.")

        # --- 5. Return Results --- 
        # Return the markdown, the input_doc_path (caller might need it), and the paths to the intermediate files
        return markdown_content, input_doc_path, raw_text_path, table_path

    except Exception as e:
        print(f"[{request_id}] Error during scan_to_markdown: {str(e)}")
        # Clean up internally created temp files (Textract output)
        cleanup_files(*[p for p in cleanup_list_internal if p])
        # If we saved an UploadFile, clean that up too on error
        if saved_doc_path:
            cleanup_files(saved_doc_path)
        raise # Re-raise exception for the route handler