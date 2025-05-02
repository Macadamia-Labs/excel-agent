from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import os
import json
from fill_excel_with_json import fill_excel_template
from excel_to_markdown import convert_excel_to_markdown
from ocr import process_text_analysis, process_with_gemini
import boto3
from dotenv import load_dotenv
import genai

# Load environment variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cleanup(template_path, output_path):
    try:
        os.remove(template_path)
    except Exception:
        pass
    try:
        os.remove(output_path)
    except Exception:
        pass

@app.post("/fill-excel-with-json/")
def fill_excel_with_json(
    background_tasks: BackgroundTasks,
    excel_template: UploadFile = File(...),
    data_json: str = Form(...)
):
    # Parse the data dictionary
    try:
        data_to_insert = json.loads(data_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid data_json: {e}")

    # Save the uploaded Excel template to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_template:
        shutil.copyfileobj(excel_template.file, tmp_template)
        template_path = tmp_template.name

    # Prepare output file path
    output_path = template_path.replace(".xlsx", "_filled.xlsx")

    # Fill the Excel template
    result, error = fill_excel_template(template_path, output_path, data_to_insert)
    if not result:
        os.remove(template_path)
        raise HTTPException(status_code=500, detail=f"Failed to fill Excel template: {error}")

    # Return the filled Excel file
    response = FileResponse(output_path, filename="filled_template.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    background_tasks.add_task(cleanup, template_path, output_path)
    return response

@app.post("/scan-to-markdown/")
async def scan_to_markdown(
    background_tasks: BackgroundTasks,
    pdf_file: UploadFile = File(...)
):
    # Save the uploaded PDF to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        shutil.copyfileobj(pdf_file.file, tmp_file)
        pdf_path = tmp_file.name

    try:
        # Initialize AWS Textract client
        AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')

        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            raise HTTPException(status_code=500, detail="AWS credentials not found in environment variables")

        client = boto3.client(
            'textract',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        # Process the document with Textract
        block_count = process_text_analysis(client, pdf_path)
        
        # Get the paths to the generated files
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        raw_text_path = f'output/{base_filename}_rawtext.txt'
        table_path = f'output/{base_filename}_tables.txt'
        
        # Process with Gemini
        process_with_gemini(client, pdf_path, raw_text_path, table_path)
        
        # Read the generated markdown
        markdown_path = f'output/{base_filename}_markdown.md'
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Clean up temporary files
        background_tasks.add_task(cleanup, pdf_path, None)
        
        # Return the markdown content
        return PlainTextResponse(
            content=markdown_content,
            media_type="text/markdown"
        )
        
    except Exception as e:
        os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.post("/excel-to-markdown/")
async def excel_to_markdown(
    background_tasks: BackgroundTasks,
    excel_file: UploadFile = File(...)
):
    # Save the uploaded Excel file to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        shutil.copyfileobj(excel_file.file, tmp_file)
        excel_path = tmp_file.name

    try:
        # Process the Excel file to Markdown
        success, result = convert_excel_to_markdown(excel_path)
        if not success:
            raise HTTPException(status_code=500, detail=result)
        
        # Clean up the temporary Excel file
        background_tasks.add_task(cleanup, excel_path, None)
        
        # Return the markdown content directly as text
        return PlainTextResponse(
            content=result,
            media_type="text/markdown"
        )
        
    except Exception as e:
        os.remove(excel_path)
        raise HTTPException(status_code=500, detail=f"Failed to convert Excel to Markdown: {str(e)}")

@app.post("/fill-excel-with-scan/")
async def fill_excel_with_scan(
    background_tasks: BackgroundTasks,
    excel_template: UploadFile = File(...),
    pdf_file: UploadFile = File(...)
):
    # Save the uploaded files to temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
        shutil.copyfileobj(excel_template.file, tmp_excel)
        excel_path = tmp_excel.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        shutil.copyfileobj(pdf_file.file, tmp_pdf)
        pdf_path = tmp_pdf.name

    try:
        # Initialize AWS Textract client
        AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')

        if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
            raise HTTPException(status_code=500, detail="AWS credentials not found in environment variables")

        client = boto3.client(
            'textract',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        # First convert Excel template to markdown
        success, template_markdown = convert_excel_to_markdown(excel_path)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to convert Excel template to markdown: {template_markdown}")

        # Save template markdown to temp file
        template_md_path = excel_path.replace(".xlsx", "_template.md")
        with open(template_md_path, 'w', encoding='utf-8') as f:
            f.write(template_markdown)

        # Process the PDF with Textract
        block_count = process_text_analysis(client, pdf_path)
        
        # Get the paths to the generated files
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        raw_text_path = f'output/{base_filename}_rawtext.txt'
        table_path = f'output/{base_filename}_tables.txt'
        
        # Process with Gemini
        process_with_gemini(client, pdf_path, raw_text_path, table_path)
        
        # Read the generated markdown
        scan_markdown_path = f'output/{base_filename}_markdown.md'
        with open(scan_markdown_path, 'r', encoding='utf-8') as f:
            scan_markdown = f.read()

        # Initialize Gemini for data mapping
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        if not GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found in environment variables")

        gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        # Create the prompt for data mapping
        prompt = """
        Analyze the Excel template markdown and the scanned document markdown to create a mapping of cell values.
        Return ONLY a Python dictionary where keys are cell IDs (e.g., "A1", "B2") and values are the corresponding values to insert.
        The output should be valid Python code that can be directly used with openpyxl.
        """

        # Create the content parts for Gemini
        content_parts = [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"text": f"Excel Template Markdown:\n{template_markdown}"},
                    {"text": f"Scanned Document Markdown:\n{scan_markdown}"}
                ]
            }
        ]

        # Generate content using Gemini
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=content_parts
        )

        # Extract the Python dictionary from Gemini's response
        data_to_insert = eval(response.text.strip())

        # Prepare output file path
        output_path = excel_path.replace(".xlsx", "_filled.xlsx")

        # Fill the Excel template
        result, error = fill_excel_template(excel_path, output_path, data_to_insert)
        if not result:
            raise HTTPException(status_code=500, detail=f"Failed to fill Excel template: {error}")

        # Clean up temporary files
        background_tasks.add_task(cleanup, excel_path, output_path)
        background_tasks.add_task(cleanup, pdf_path, None)
        background_tasks.add_task(cleanup, template_md_path, None)

        # Return the filled Excel file
        return FileResponse(
            output_path,
            filename="filled_template.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        # Clean up on error
        os.remove(excel_path)
        os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Failed to process files: {str(e)}") 