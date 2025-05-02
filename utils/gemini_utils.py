import os
from google import generativeai as genai
from dotenv import load_dotenv
from fastapi import HTTPException
import io
from PIL import Image
from pdf2image import convert_from_path
import base64
import ast

# Load environment variables
load_dotenv()

def get_gemini_client():
    """Initializes and returns Google Gemini client."""
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not found in environment variables")
    
    try:
        # Configure the client
        genai.configure(api_key=GEMINI_API_KEY)
        # Initialize the generative model (adjust model name as needed)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Gemini client: {str(e)}")

def read_prompt_file(filename):
    """Read a prompt file from the prompt directory."""
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', filename)
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read prompt file {filename}: {str(e)}")

def generate_markdown_from_scan(gemini_model, doc_path: str, raw_text_path: str, table_path: str) -> str:
    """
    Generates markdown content from a document scan (PDF or image) using Gemini, aided by Textract output.
    """
    try:
        # Handle PDF or image file
        file_ext = os.path.splitext(doc_path)[1].lower()
        if file_ext == '.pdf':
            images = convert_from_path(doc_path)
        else:
            # For image files, create a single-item list
            images = [Image.open(doc_path)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document for Gemini: {str(e)}")

    try:
        with open(raw_text_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        with open(table_path, 'r', encoding='utf-8') as f:
            table_data = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read Textract temp files: {str(e)}")

    prompt = read_prompt_file('markdown-generation.md')

    content_parts = [
        prompt,
        f"Raw Text Context (from AWS Textract):\n{raw_text}",
        f"Table Data Context (from AWS Textract):\n{table_data}"
    ]

    for image in images:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        content_parts.append(Image.open(io.BytesIO(img_byte_arr)))
        
    try:
        # Use generate_content for multimodal input
        response = gemini_model.generate_content(content_parts)
        markdown_content = response.text.strip()
        # Clean potential markdown fences (though the prompt asks not to include them)
        markdown_content = markdown_content.removeprefix("```markdown").removesuffix("```").strip()
        return markdown_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error during markdown generation: {str(e)}")

def generate_excel_mapping_from_markdown(gemini_model, template_markdown: str, scan_markdown: str) -> dict:
    """
    Uses Gemini to analyze template and scan markdown, returning a Python dictionary 
    mapping cell IDs to values for filling the Excel template.
    """
    prompt = read_prompt_file('excel-mapping.md')
    prompt = f"{prompt}\n\nExcel Template Definition:\n------------------------\n{template_markdown}\n------------------------\n\nOCR Extracted Data:\n--------------------------\n{scan_markdown}\n--------------------------\n"

    try:
        response = gemini_model.generate_content(prompt)
        
        dict_string = response.text.strip()

        # Save dict_string to file for debugging/logging
        with open("gemini_response.txt", "w") as f:
            f.write(dict_string)
        # Clean potential json fences
        dict_string = dict_string.removeprefix("```json").removesuffix("```").strip()
        
        # Safely evaluate the string to a dictionary
        try:
            data_to_insert = ast.literal_eval(dict_string)
            if not isinstance(data_to_insert, dict):
                raise ValueError("Gemini did not return a dictionary.")
            return data_to_insert
        except (SyntaxError, ValueError, TypeError) as e:
             raise HTTPException(status_code=500, detail=f"Gemini returned invalid dictionary format: {e}\nResponse: {dict_string}")
            
    except Exception as e:
        # Catch potential API errors or other issues
        # Check if 'response' exists before trying to access 'response.text'
        error_detail = f"Gemini API error during data mapping generation: {str(e)}"
        if 'response' in locals() and hasattr(response, 'text'):
             error_detail += f"\nRaw Response: {response.text[:500]}..." # Include partial response for debugging
        raise HTTPException(status_code=500, detail=error_detail) 