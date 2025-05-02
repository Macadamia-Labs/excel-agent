from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid

# Import core logic functions
from app.excel_to_markdown import convert_excel_to_markdown 
from app.scan_to_markdown import convert_scan_to_markdown
from app.fill_excel_with_json import fill_excel_template
from app.fill_excel_with_scan import fill_excel_with_scan

# Import utility functions
from utils.file_utils import save_upload_file_tmp, cleanup_files


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
          summary="Converts a scanned PDF document to Markdown using OCR and AI enhancement",
          response_description="Markdown content of the document")
async def scan_to_markdown_route(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(..., description="Scanned document in PDF format")
):
    """
    Receives a PDF, processes it using AWS Textract and Google Gemini,
    and returns the extracted content as a Markdown string.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /scan-to-markdown/")

    try:
        markdown_content, pdf_path, raw_text_path, table_path = await convert_scan_to_markdown(request_id, pdf_file)
        
        # Schedule cleanup for all temporary files
        print(f"[{request_id}] Scheduling cleanup for: {pdf_path}, {raw_text_path}, {table_path}")
        background_tasks.add_task(cleanup_files, pdf_path, raw_text_path, table_path)
        
        # Return the markdown content
        print(f"[{request_id}] Returning Markdown content.")
        return PlainTextResponse(content=markdown_content, media_type="text/markdown")

    except HTTPException as http_exc:
        cleanup_files(pdf_path, raw_text_path, table_path)
        raise http_exc
    except Exception as e:
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        cleanup_files(pdf_path, raw_text_path, table_path)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")
    

@app.post("/excel-to-markdown/",
          summary="Converts an Excel file to a Markdown representation",
          response_description="Markdown content describing the Excel structure")
async def excel_to_markdown_route(
    background_tasks: BackgroundTasks,
    excel_file: UploadFile = File(..., description="Excel file (.xlsx) to convert")
):
    """
    Receives an Excel file, converts it to Markdown detailing its structure 
    (sheets, rows, columns), and returns the Markdown content.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /excel-to-markdown/")
    excel_path = None
    try:
        # Save uploaded Excel file
        print(f"[{request_id}] Saving uploaded Excel file: {excel_file.filename}")
        excel_path = await save_upload_file_tmp(excel_file, suffix=".xlsx")
        print(f"[{request_id}] Excel file saved to: {excel_path}")

        # Convert Excel to Markdown
        print(f"[{request_id}] Calling convert_excel_to_markdown for: {excel_path}")
        success, markdown_content = convert_excel_to_markdown(excel_path)
        if not success:
            # Ensure temporary file is cleaned up even if conversion fails
            print(f"[{request_id}] Error converting Excel to Markdown: {markdown_content}")
            cleanup_files(excel_path) 
            raise HTTPException(status_code=500, detail=f"Failed to convert Excel to Markdown: {markdown_content}")
        
        print(f"[{request_id}] Excel converted to Markdown successfully.")

        # Schedule cleanup of the temporary Excel file
        print(f"[{request_id}] Scheduling cleanup for: {excel_path}")
        background_tasks.add_task(cleanup_files, excel_path)
        
        # Return the markdown content
        print(f"[{request_id}] Returning Markdown content.")
        return PlainTextResponse(content=markdown_content, media_type="text/markdown")

    except HTTPException as http_exc:
        cleanup_files(excel_path)
        raise http_exc
    except Exception as e:
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        cleanup_files(excel_path)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@app.post("/fill-excel-with-json/",
          summary="Fills an Excel template using provided JSON data",
          response_description="The filled Excel file")
async def fill_excel_with_json_route(
    background_tasks: BackgroundTasks,
    excel_template: UploadFile = File(..., description="Excel template file (.xlsx)"),
    data_json: str = Form(..., description="JSON string mapping cell IDs to values")
):
    """
    Receives an Excel template and a JSON string, fills the template, 
    and returns the resulting Excel file.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /fill-excel-with-json/")
    template_path = None
    output_path = None
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
        print(f"[{request_id}] Saving uploaded template: {excel_template.filename}")
        template_path = await save_upload_file_tmp(excel_template, suffix=".xlsx")
        output_path = template_path.replace(".xlsx", "_filled.xlsx")
        print(f"[{request_id}] Template saved to: {template_path}")

        # Fill the Excel template using the function from fill_excel.py
        print(f"[{request_id}] Calling fill_excel_template...")
        success, error = fill_excel_template(template_path, output_path, data_to_insert)
        if not success:
            # Ensure temporary files are cleaned up even if filling fails before background task runs
            print(f"[{request_id}] Error during template filling: {error}")
            cleanup_files(template_path, output_path) 
            raise HTTPException(status_code=500, detail=f"Failed to fill Excel template: {error}")

        # Schedule cleanup of temporary files
        print(f"[{request_id}] Scheduling cleanup for: {template_path}, {output_path}")
        background_tasks.add_task(cleanup_files, template_path, output_path)

        # Return the filled file
        output_filename = excel_template.filename.replace(".xlsx", "_filled.xlsx") if excel_template.filename else "filled_template.xlsx"
        print(f"[{request_id}] Returning filled file: {output_filename}")
        return FileResponse(
            output_path,
            filename=output_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly
        cleanup_files(template_path, output_path) # Cleanup before raising
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        cleanup_files(template_path, output_path) # Cleanup before raising
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")


@app.post("/fill-excel-with-scan/",
          summary="Fills an Excel template using data extracted from a scanned PDF",
          response_description="The filled Excel file")
async def fill_excel_with_scan_route(
    background_tasks: BackgroundTasks,
    excel_template: UploadFile = File(..., description="Excel template file (.xlsx)"),
    pdf_file: UploadFile = File(..., description="Scanned document in PDF format containing data")
):
    """
    Receives an Excel template and a scanned PDF. Converts both to Markdown, 
    uses Gemini to map data from the scan to the template, fills the template, 
    and returns the resulting Excel file.
    """
    request_id = uuid.uuid4()
    print(f"[{request_id}] Received request for /fill-excel-with-scan/")

    try:
        # Call the core logic function
        output_path, excel_path, pdf_path, raw_text_path, table_path = await fill_excel_with_scan(
            request_id, excel_template, pdf_file
        )

        # Schedule cleanup for all temporary files
        print(f"[{request_id}] Scheduling cleanup for: {excel_path}, {pdf_path}, {raw_text_path}, {table_path}, {output_path}")
        background_tasks.add_task(cleanup_files, excel_path, pdf_path, raw_text_path, table_path, output_path)

        # Return the filled Excel file
        output_filename = excel_template.filename.replace(".xlsx", "_filled.xlsx") if excel_template.filename else "filled_template.xlsx"
        print(f"[{request_id}] Returning filled file: {output_filename}")
        return FileResponse(
            output_path,
            filename=output_filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print(f"[{request_id}] An unexpected server error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

# --- Optional: Add a root endpoint for basic info ---
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the Excel Agent API. See /docs for details."} 