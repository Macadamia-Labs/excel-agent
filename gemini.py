import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

def process_with_gemini(template_markdown_file, ocr_markdown_file, excel_file_name):
    """
    Process the markdown content with Google Gemini to generate enhanced analysis.
    
    Args:
        template_markdown_file: Path to the template markdown file
        ocr_markdown_file: Path to the OCR-extracted markdown file
        excel_file_name: Name of the Excel file to be processed
        
    Returns:
        None
    """
    try:
        # Initialize Gemini
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        # Initialize Gemini client
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Read the prompt from gemini.md
        with open('prompt/gemini.md', 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        # Read both markdown contents
        with open(template_markdown_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        with open(ocr_markdown_file, 'r', encoding='utf-8') as f:
            ocr_content = f.read()
        
        # Create the content parts
        content_parts = [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"text": f"Markdown Content of excel template to fill in:\n{template_content}"},
                    {"text": f"Extracted markdown content with OCR from pdf:\n{ocr_content}"},
                    {"text": f"File name of excel file:\n{excel_file_name}"}
                ]
            }
        ]
        
        # Generate content using Gemini
        response = gemini_client.models.generate_content(
            # model="gemini-2.5-pro-preview-03-25",
            model="gemini-2.5-flash-preview-04-17",
            contents=content_parts
        )
        
        analysis_content = response.text.strip()
        
        # Save the analysis output
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        base_filename = os.path.splitext(os.path.basename(template_markdown_file))[0]
        analysis_path = f'{output_dir}/{base_filename}_analysis.md'
        
        with open(analysis_path, 'w', encoding='utf-8') as f:
            f.write(analysis_content)
            
        print(f"\nGemini analysis saved to: {analysis_path}")
        
    except Exception as e:
        print(f"Error in Gemini processing: {str(e)}")
        raise

def main():
    # Process both markdown files
    template_file = "output/IGEG1688I.md"  # Template markdown file
    ocr_file = "output/sulzer_markdown.md"  # OCR-extracted markdown file
    excel_file = "input/IGEG1688I.xlsx"  # Excel template file name
    process_with_gemini(template_file, ocr_file, excel_file)

if __name__ == "__main__":
    main()
