from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import os
import json
from fill_excel import fill_excel_template
from excel_to_markdown import convert_excel_to_markdown

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

@app.post("/fill-excel/")
def fill_excel(
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