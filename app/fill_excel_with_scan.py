from utils.aws_utils import extract_text_and_tables, get_textract_client
from utils.file_utils import save_upload_file_tmp
from utils.gemini_utils import generate_markdown_from_scan, get_gemini_client, generate_excel_mapping_from_markdown
from app.excel_to_markdown import convert_excel_to_markdown
from app.fill_excel_with_json import fill_excel_template


async def fill_excel_with_scan(request_id, excel_template, pdf_file):
    """
    Core logic for filling an Excel template with data from a scanned PDF.
    
    Args:
        request_id: Unique identifier for the request
        excel_template: UploadFile containing the Excel template
        pdf_file: UploadFile containing the scanned PDF
        
    Returns:
        tuple: (output_path, excel_path, pdf_path, raw_text_path, table_path)
    """
    excel_path = None
    pdf_path = None
    raw_text_path = None
    table_path = None
    output_path = None

    try:
        # Save uploaded files
        print(f"[{request_id}] Saving uploaded Excel template: {excel_template.filename}")
        excel_path = await save_upload_file_tmp(excel_template, suffix=".xlsx")
        print(f"[{request_id}] Template saved to: {excel_path}")
        print(f"[{request_id}] Saving uploaded PDF: {pdf_file.filename}")
        pdf_path = await save_upload_file_tmp(pdf_file, suffix=".pdf")
        print(f"[{request_id}] PDF saved to: {pdf_path}")
        
        # Initialize clients
        print(f"[{request_id}] Initializing AWS Textract and Google Gemini clients...")
        textract_client = get_textract_client()
        gemini_model = get_gemini_client()

        # 1. Convert Excel template to Markdown
        print(f"[{request_id}] Converting Excel template to Markdown: {excel_path}")
        success, template_markdown = convert_excel_to_markdown(excel_path)
        if not success:
            raise Exception(f"Failed to convert Excel template to markdown: {template_markdown}")
        print(f"[{request_id}] Excel template converted to Markdown successfully.")

        # 2. Process PDF scan to Markdown
        print(f"[{request_id}] Starting Textract processing for PDF: {pdf_path}")
        raw_text_path, table_path = extract_text_and_tables(textract_client, pdf_path)
        print(f"[{request_id}] Textract processing complete. Raw text: {raw_text_path}, Tables: {table_path}")
        print(f"[{request_id}] Starting Gemini enhancement for scan...")
        scan_markdown = generate_markdown_from_scan(gemini_model, pdf_path, raw_text_path, table_path)
        print(f"[{request_id}] Scan enhanced to Markdown successfully.")

        # 3. Generate data mapping using Gemini
        print(f"[{request_id}] Starting Gemini mapping between template Markdown and scan Markdown...")
        data_to_insert = generate_excel_mapping_from_markdown(gemini_model, template_markdown, scan_markdown)
        print(f"[{request_id}] Gemini mapping complete. Generated {len(data_to_insert)} mappings.")
        
        # 4. Fill the Excel template
        print(f"[{request_id}] Calling fill_excel_template...")
        output_path = excel_path.replace(".xlsx", "_filled.xlsx")
        success, error = fill_excel_template(excel_path, output_path, data_to_insert)
        if not success:
            raise Exception(f"Failed to fill Excel template after mapping: {error}")

        return output_path, excel_path, pdf_path, raw_text_path, table_path

    except Exception as e:
        # Clean up any files that were created before the error
        from utils.file_utils import cleanup_files
        cleanup_files(excel_path, pdf_path, raw_text_path, table_path, output_path)
        raise e 