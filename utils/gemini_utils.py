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
        model = genai.GenerativeModel('gemini-1.5-flash-latest') # Using flash as it's faster for this usually
        return model
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize Gemini client: {str(e)}")

def generate_markdown_from_scan(gemini_model, pdf_path: str, raw_text_path: str, table_path: str) -> str:
    """
    Generates markdown content from a PDF scan using Gemini, aided by Textract output.
    (Based on ocr.py:process_with_gemini)
    """
    try:
        images = convert_from_path(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert PDF to images for Gemini: {str(e)}")

    try:
        with open(raw_text_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        with open(table_path, 'r', encoding='utf-8') as f:
            table_data = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read Textract temp files: {str(e)}")

    prompt = """
    Analyze the images and extract all the text into well-formatted markdown.
    
    RULES:
    1. Maintain all tables in proper markdown format.
    2. Preserve any mathematical formulas using LaTeX notation (e.g., $...$ or $$...$$).
    3. Keep the document structure and hierarchy (headings, paragraphs, lists).
    4. Format measurements, units, and technical specifications correctly.
    5. Include relevant headers and sections.
    6. Preserve numerical data and calculations accurately.
    7. Format lists (bulleted and numbered) properly.
    8. Output ONLY the markdown content, without any introductory text or code fences like ```markdown.
    
    You are provided with raw text and table data extracted by AWS Textract as context. 
    This OCR data might contain errors, so use it as a guide but prioritize your own analysis of the images for accuracy and formatting.
    """

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
    prompt = f"""
    Analyze the Excel Template Markdown and the Scanned Document Markdown provided below.
    Your task is to identify the data present in the Scanned Document Markdown that corresponds to the placeholders or structure defined in the Excel Template Markdown.
    Generate ONLY a Python dictionary where:
    - Keys are the target cell IDs (e.g., "A1", "B2") in the Excel template where data should be inserted.
    - Values are the corresponding data extracted from the Scanned Document Markdown.
    
    IMPORTANT RULES:
    1. Only include mappings for data found in the Scanned Document Markdown.
    2. Ensure keys are valid Excel cell IDs (strings).
    3. Ensure values are appropriate Python types (strings, numbers, etc.).
    4. The output MUST be a single, valid Python dictionary literal. Do NOT include any other text, explanations, or code fences (```python ... ```).
    5. Pay attention to merged cell information in the template markdown (e.g., `(merged range: A4:E4)`) to correctly identify the primary cell ID for a merged area (e.g., A4).

    Excel Template Markdown:
    ------------------------
    {template_markdown}
    ------------------------

    Scanned Document Markdown:
    --------------------------
    {scan_markdown}
    --------------------------

    Python Dictionary Output:
    """

    try:
        response = gemini_model.generate_content(prompt)
        dict_string = response.text.strip()
        # Clean potential python fences
        dict_string = dict_string.removeprefix("```python").removesuffix("```").strip()
        
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