from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import os

# Import core logic functions
from app.excel_to_markdown import convert_excel_to_markdown 
from app.scan_to_markdown import convert_scan_to_markdown
from app.fill_excel_with_json import fill_excel_template
from app.fill_excel_with_scan import fill_excel_with_scan

# Import utility functions
from utils.file_utils import save_upload_file_tmp, cleanup_files, convert_xls_to_xlsx
from utils.gemini_utils import generate_excel_mapping_from_markdown, get_gemini_client


# --- FastAPI App Setup ---
app = FastAPI(
    title="Excel Agent API",
    description="API for processing Excel files and scanned documents."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for now, adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---

@app.post("/scan-to-markdown/", 
          summary="Converts a scanned document (PDF or image) to Markdown using OCR and AI enhancement",
          response_description="Markdown content of the document")
async def scan_to_markdown_route(
    background_tasks: BackgroundTasks,
    document: UploadFile = File(..., description="Scanned document in PDF, PNG, or JPG format")
):
    """
    Receives a PDF or image file, processes it using AWS Textract and Google Gemini,
    and returns the extracted content as a Markdown string.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /scan-to-markdown/")

    # Validate file type
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
    file_ext = os.path.splitext(document.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )

    try:
        markdown_content, doc_path, raw_text_path, table_path = await convert_scan_to_markdown(request_id, document)
        
        # Schedule cleanup for all temporary files
        print(f"[{request_id}] Scheduling cleanup for: {doc_path}, {raw_text_path}, {table_path}")
        background_tasks.add_task(cleanup_files, doc_path, raw_text_path, table_path)
        
        # Return the markdown content
        print(f"[{request_id}] Returning Markdown content.")
        return PlainTextResponse(content=markdown_content, media_type="text/markdown")

    except HTTPException as http_exc:
        cleanup_files(doc_path, raw_text_path, table_path)
        raise http_exc
    except Exception as e:
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        cleanup_files(doc_path, raw_text_path, table_path)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
    

@app.post("/excel-to-markdown/",
          summary="Converts an Excel file to a Markdown representation",
          response_description="Markdown content describing the Excel structure")
async def excel_to_markdown_route(
    background_tasks: BackgroundTasks,
    excel_file: UploadFile = File(..., description="Excel file (.xlsx or .xls) to convert")
):
    """
    Receives an Excel file (.xlsx or .xls), converts it to Markdown detailing its structure
    (sheets, rows, columns), and returns the Markdown content.
    If an .xls file is provided, it's converted to .xlsx first.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /excel-to-markdown/")
    original_excel_path = None
    processed_excel_path = None # This will hold the path to the .xlsx file used for processing
    files_to_cleanup = []

    try:
        # Save uploaded Excel file
        file_ext = os.path.splitext(excel_file.filename)[1].lower()
        print(f"[{request_id}] Saving uploaded Excel file: {excel_file.filename}")
        original_excel_path = await save_upload_file_tmp(excel_file, suffix=file_ext)
        files_to_cleanup.append(original_excel_path)
        print(f"[{request_id}] Original Excel file saved to: {original_excel_path}")

        # Convert .xls to .xlsx if necessary
        if file_ext == '.xls':
            print(f"[{request_id}] .xls file detected. Converting to .xlsx...")
            processed_excel_path = convert_xls_to_xlsx(original_excel_path)
            files_to_cleanup.append(processed_excel_path) # Add converted file for cleanup
            print(f"[{request_id}] Converted .xlsx file path: {processed_excel_path}")
        elif file_ext == '.xlsx':
            processed_excel_path = original_excel_path
        else:
            print(f"[{request_id}] Error: Invalid Excel file format {file_ext}")
            raise HTTPException(status_code=400, detail="Invalid file format. Only .xlsx and .xls are supported.")

        # Convert Excel (now guaranteed .xlsx) to Markdown
        print(f"[{request_id}] Calling convert_excel_to_markdown for: {processed_excel_path}")
        success, markdown_content = convert_excel_to_markdown(processed_excel_path)
        if not success:
            print(f"[{request_id}] Error converting Excel to Markdown: {markdown_content}")
            raise HTTPException(status_code=500, detail=f"Failed to convert Excel to Markdown: {markdown_content}")

        print(f"[{request_id}] Excel converted to Markdown successfully.")

        # Schedule cleanup of all temporary files
        print(f"[{request_id}] Scheduling cleanup for: {files_to_cleanup}")
        background_tasks.add_task(cleanup_files, *files_to_cleanup) # Unpack list

        # Return the markdown content
        print(f"[{request_id}] Returning Markdown content.")
        return PlainTextResponse(content=markdown_content, media_type="text/markdown")

    except HTTPException as http_exc:
        cleanup_files(*files_to_cleanup) # Cleanup immediately on known errors
        raise http_exc
    except Exception as e:
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        cleanup_files(*files_to_cleanup) # Cleanup immediately on unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@app.post("/fill-excel-with-json/",
          summary="Fills an Excel template using provided JSON data",
          response_description="The filled Excel file")
async def fill_excel_with_json_route(
    background_tasks: BackgroundTasks,
    excel_template: UploadFile = File(..., description="Excel template file (.xlsx or .xls)"),
    data_json: str = Form(..., description="JSON string mapping cell IDs to values")
):
    """
    Receives an Excel template (.xlsx or .xls) and a JSON string, fills the template,
    and returns the resulting Excel file.
    If an .xls template is provided, it's converted to .xlsx first.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /fill-excel-with-json/")
    original_template_path = None
    processed_template_path = None # This will hold the path to the .xlsx template used for processing
    output_path = None
    files_to_cleanup = []

    try:
        # Parse JSON data first to fail early
        try:
            data_to_insert = json.loads(data_json)
            if not isinstance(data_to_insert, dict):
                raise ValueError("Provided data_json is not a valid JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[{request_id}] Error: Invalid JSON format.")
            raise HTTPException(status_code=400, detail=f"Invalid data_json format: {e}")

        # Save uploaded Excel template
        file_ext = os.path.splitext(excel_template.filename)[1].lower()
        print(f"[{request_id}] Saving uploaded template: {excel_template.filename}")
        original_template_path = await save_upload_file_tmp(excel_template, suffix=file_ext)
        files_to_cleanup.append(original_template_path)
        print(f"[{request_id}] Original template saved to: {original_template_path}")

        # Convert .xls to .xlsx if necessary
        if file_ext == '.xls':
            print(f"[{request_id}] .xls template detected. Converting to .xlsx...")
            processed_template_path = convert_xls_to_xlsx(original_template_path)
            files_to_cleanup.append(processed_template_path) # Add converted file for cleanup
            print(f"[{request_id}] Converted .xlsx template path: {processed_template_path}")
        elif file_ext == '.xlsx':
            processed_template_path = original_template_path
        else:
            print(f"[{request_id}] Error: Invalid Excel template format {file_ext}")
            raise HTTPException(status_code=400, detail="Invalid template format. Only .xlsx and .xls are supported.")

        # Define output path (based on the processed template path)
        output_path = processed_template_path.replace(".xlsx", "_filled.xlsx")
        files_to_cleanup.append(output_path) # Add output file for cleanup

        # Fill the Excel template (now guaranteed .xlsx)
        print(f"[{request_id}] Calling fill_excel_template with template: {processed_template_path}, output: {output_path}")
        success, error = fill_excel_template(processed_template_path, output_path, data_to_insert)
        if not success:
            print(f"[{request_id}] Error during template filling: {error}")
            raise HTTPException(status_code=500, detail=f"Failed to fill Excel template: {error}")

        # Schedule cleanup of temporary files
        print(f"[{request_id}] Scheduling cleanup for: {files_to_cleanup}")
        background_tasks.add_task(cleanup_files, *files_to_cleanup)

        # Return the filled file
        output_filename = excel_template.filename.replace(file_ext, "_filled.xlsx") if excel_template.filename else "filled_template.xlsx"
        print(f"[{request_id}] Returning filled file: {output_filename}")
        return FileResponse(
            output_path,
            filename=output_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        cleanup_files(*files_to_cleanup) # Cleanup before raising
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        cleanup_files(*files_to_cleanup) # Cleanup before raising
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@app.post("/fill-excel-with-scan/",
          summary="Fills an Excel template using data extracted from a scanned document",
          response_description="The filled Excel file")
async def fill_excel_with_scan_route(
    background_tasks: BackgroundTasks,
    excel_template: UploadFile = File(..., description="Excel template file (.xlsx or .xls)"),
    document: UploadFile = File(..., description="Scanned document in PDF, PNG, or JPG format containing data")
):
    """
    Receives an Excel template (.xlsx or .xls) and a scanned document. Converts template if needed,
    converts scan to Markdown, uses Gemini to map data, fills the template, 
    and returns the resulting Excel file.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /fill-excel-with-scan/")
    
    original_template_path = None
    processed_template_path = None
    doc_path = None
    output_path = None
    raw_text_path = None # Path from scan_to_markdown
    table_path = None # Path from scan_to_markdown
    files_to_cleanup = []

    try:
        # --- 1. Validate and Save Document --- 
        allowed_doc_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
        doc_ext = os.path.splitext(document.filename)[1].lower()
        if doc_ext not in allowed_doc_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document file type '{doc_ext}'. Allowed types: {', '.join(allowed_doc_extensions)}"
            )
        print(f"[{request_id}] Saving uploaded document: {document.filename}")
        doc_path = await save_upload_file_tmp(document, suffix=doc_ext)
        files_to_cleanup.append(doc_path)
        print(f"[{request_id}] Document saved to: {doc_path}")

        # --- 2. Validate, Save, and Convert Excel Template --- 
        excel_ext = os.path.splitext(excel_template.filename)[1].lower()
        print(f"[{request_id}] Saving uploaded Excel template: {excel_template.filename}")
        original_template_path = await save_upload_file_tmp(excel_template, suffix=excel_ext)
        files_to_cleanup.append(original_template_path)
        print(f"[{request_id}] Original template saved to: {original_template_path}")

        if excel_ext == '.xls':
            print(f"[{request_id}] .xls template detected. Converting to .xlsx...")
            processed_template_path = convert_xls_to_xlsx(original_template_path)
            files_to_cleanup.append(processed_template_path) 
            print(f"[{request_id}] Converted .xlsx template path: {processed_template_path}")
        elif excel_ext == '.xlsx':
            processed_template_path = original_template_path
        else:
            raise HTTPException(status_code=400, detail=f"Invalid template file format '{excel_ext}'. Only .xlsx and .xls are supported.")

        # --- 3. Call the core logic function (with paths) --- 
        # Assumption: fill_excel_with_scan now takes paths and returns all created file paths
        print(f"[{request_id}] Calling core fill_excel_with_scan logic...")
        output_path, _, _, raw_text_path_from_func, table_path_from_func = await fill_excel_with_scan(
            request_id,
            processed_template_path, # Path to .xlsx
            doc_path, # Path to saved document
            document.filename, # Original document filename
            excel_template.filename # Original excel filename
        )
        # Add paths returned by the function to cleanup list if they exist
        if output_path: files_to_cleanup.append(output_path)
        if raw_text_path_from_func: files_to_cleanup.append(raw_text_path_from_func)
        if table_path_from_func: files_to_cleanup.append(table_path_from_func)
        # Note: excel_path and doc_path are already in files_to_cleanup

        print(f"[{request_id}] Core logic completed. Output path: {output_path}")

        # --- 4. Schedule Cleanup --- 
        print(f"[{request_id}] Scheduling cleanup for: {files_to_cleanup}")
        background_tasks.add_task(cleanup_files, *files_to_cleanup)

        # --- 5. Return File --- 
        output_filename = excel_template.filename.replace(excel_ext, "_filled.xlsx") if excel_template.filename else "filled_template.xlsx"
        print(f"[{request_id}] Returning filled file: {output_filename}")
        return FileResponse(
            output_path,
            filename=output_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException as http_exc:
        print(f"[{request_id}] HTTPException occurred: {http_exc.detail}")
        cleanup_files(*files_to_cleanup)
        raise http_exc
    except Exception as e:
        import traceback
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        print(traceback.format_exc()) # Print stack trace for debugging
        cleanup_files(*files_to_cleanup)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

# --- Optional: Add a root endpoint for basic info ---
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the Excel Agent API. See /docs for details."} 
