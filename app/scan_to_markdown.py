from utils.aws_utils import extract_text_and_tables, get_textract_client
from utils.file_utils import save_upload_file_tmp
from utils.gemini_utils import generate_markdown_from_scan, get_gemini_client
import os
from PIL import Image
import io


async def convert_scan_to_markdown(request_id, document):
    doc_path = None
    raw_text_path = None
    table_path = None
    
    # Save uploaded document
    print(f"[{request_id}] Saving uploaded document: {document.filename}")
    file_ext = os.path.splitext(document.filename)[1].lower()
    doc_path = await save_upload_file_tmp(document, suffix=file_ext)
    print(f"[{request_id}] Document saved to: {doc_path}")
    
    # Initialize clients
    print(f"[{request_id}] Initializing AWS Textract and Google Gemini clients...")
    textract_client = get_textract_client()
    gemini_model = get_gemini_client()

    # Process document with Textract
    print(f"[{request_id}] Starting Textract processing for: {doc_path}")
    raw_text_path, table_path = extract_text_and_tables(textract_client, doc_path)
    print(f"[{request_id}] Textract processing complete. Raw text: {raw_text_path}, Tables: {table_path}")
    
    # Enhance OCR with Gemini
    print(f"[{request_id}] Starting Gemini enhancement...")
    markdown_content = generate_markdown_from_scan(gemini_model, doc_path, raw_text_path, table_path)
    print(f"[{request_id}] Gemini enhancement complete.")
    
    return markdown_content, doc_path, raw_text_path, table_path