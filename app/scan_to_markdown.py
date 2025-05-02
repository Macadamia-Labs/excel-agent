from utils.aws_utils import extract_text_and_tables, get_textract_client
from utils.file_utils import save_upload_file_tmp
from utils.gemini_utils import generate_markdown_from_scan, get_gemini_client


async def convert_scan_to_markdown(request_id, pdf_file):
    pdf_path = None
    raw_text_path = None
    table_path = None
    
    # Save uploaded PDF
    print(f"[{request_id}] Saving uploaded PDF: {pdf_file.filename}")
    pdf_path = await save_upload_file_tmp(pdf_file, suffix=".pdf")
    print(f"[{request_id}] PDF saved to: {pdf_path}")
    
    # Initialize clients
    print(f"[{request_id}] Initializing AWS Textract and Google Gemini clients...")
    textract_client = get_textract_client()
    gemini_model = get_gemini_client()

    # Process PDF with Textract
    print(f"[{request_id}] Starting Textract processing for: {pdf_path}")
    raw_text_path, table_path = extract_text_and_tables(textract_client, pdf_path)
    print(f"[{request_id}] Textract processing complete. Raw text: {raw_text_path}, Tables: {table_path}")
    
    # Enhance OCR with Gemini
    print(f"[{request_id}] Starting Gemini enhancement...")
    markdown_content = generate_markdown_from_scan(gemini_model, pdf_path, raw_text_path, table_path)
    print(f"[{request_id}] Gemini enhancement complete.")
    
    return markdown_content, pdf_path, raw_text_path, table_path