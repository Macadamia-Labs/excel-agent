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
    You are an expert in data mapping for Microsoft Excel. Your goal is to analyze an Excel template definition and OCR extracted data to generate a mapping of cell locations to values.

    You will receive two inputs:
    1. Excel Template Definition: The markdown content of the excel file that you should write to. Use this to understand the template structure and identify target cell locations.
    2. OCR Extracted Data: The data in markdown that you should write to the excel. Only write data that is not yet in the excel template.

    IMPORTANT RULES:
    1. Keep track of merged cells. For example, if you see "A4: "JOB #:" (merged range: A4:E4)", write the corresponding value to F4 since A4:E4 is merged.
    2. For checkbox sections like "[x] FINAL", write "x" to the cell on the left of "FINAL" instead of replacing "FINAL".
    3. Do not write values to cells that contain formulas (indicated by "#DIV/0!" or similar).
    4. Output a JSON object where:
       - Keys are Excel cell IDs (e.g., "A1", "B2")
       - Values are the corresponding data to insert
    5. Only include mappings for data found in the OCR Extracted Data.
    6. ONLY write the data that is not yet in the excel template, meaning the data that needs to be inserted.
    7. Ensure values are appropriate types (strings, numbers, etc.).
    8. Return ALL the data that needs to be inserted, don't skip any cells or end eearly 

    Example of expected output format:
    {{
        "D4": "205274-101.01.01",
        "D5": "Hilcorp Alaska",
        "D6": "Chilo",
        "D7": "04-23-25",
        "BU6": "X",
        "D20": 58.427, "H20": 58.430, "L20": 58.421, "P20": 58.429,
        "T20": 58.440, "X20": 58.438, "AB20": 58.430, "AF20": 58.418,
        "D21": 43.915, "H21": 43.895, "L21": 43.892, "P21": 43.927,
        "T21": 43.910, "X21": 43.932, "AB21": 43.899, "AF21": 43.906,
        "D22": 36.839, "H22": 36.805, "L22": 36.790, "P22": 36.810,
        "T22": 36.815, "X22": 36.805, "AB22": 36.812, "AF22": 36.835,
        "D23": 36.340, "H23": 36.280, "L23": 36.300, "P23": 36.300,
        "T23": 36.320, "X23": 36.310, "AB23": 36.310, "AF23": 36.342,
        "D24": 36.314, "H24": 36.272, "L24": 36.290, "P24": 36.273
    }}

    Excel Template Definition:
    ------------------------
    {template_markdown}
    ------------------------

    OCR Extracted Data:
    --------------------------
    {scan_markdown}
    --------------------------

    Return ONLY the JSON object, without any additional text or code fences.
    """

    print("--------------------------------")
    print(prompt)
    print("--------------------------------")

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