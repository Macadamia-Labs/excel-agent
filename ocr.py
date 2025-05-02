import boto3
import io
from PIL import Image, ImageDraw
from pdf2image import convert_from_path
import os
from dotenv import load_dotenv
from google.generativeai import genai
import base64

# Load environment variables from .env file
load_dotenv()

def ShowBoundingBox(draw, box, width, height, boxColor):
    left = width * box['Left']
    top = height * box['Top'] 
    draw.rectangle([left, top, left + (width * box['Width']), top + (height * box['Height'])], outline=boxColor)   

def ShowSelectedElement(draw, box, width, height, boxColor):
    left = width * box['Left']
    top = height * box['Top'] 
    draw.rectangle([left, top, left + (width * box['Width']), top + (height * box['Height'])], fill=boxColor)  

def DisplayBlockInformation(block):
    print('Id: {}'.format(block['Id']))
    if 'Text' in block:
        print('    Detected: ' + block['Text'])
    print('    Type: ' + block['BlockType'])
   
    if 'Confidence' in block:
        print('    Confidence: ' + "{:.2f}".format(block['Confidence']) + "%")

    if block['BlockType'] == 'CELL':
        print("    Cell information")
        print("        Column:" + str(block['ColumnIndex']))
        print("        Row:" + str(block['RowIndex']))
        print("        Column Span:" + str(block['ColumnSpan']))
        print("        RowSpan:" + str(block['ColumnSpan']))    
    
    if 'Relationships' in block:
        print('    Relationships: {}'.format(block['Relationships']))
    print('    Geometry: ')
    print('        Bounding Box: {}'.format(block['Geometry']['BoundingBox']))
    print('        Polygon: {}'.format(block['Geometry']['Polygon']))
    
    if block['BlockType'] == "KEY_VALUE_SET":
        print ('    Entity Type: ' + block['EntityTypes'][0])
    
    if block['BlockType'] == 'SELECTION_ELEMENT':
        print('    Selection element detected: ', end='')
        if block['SelectionStatus'] =='SELECTED':
            print('Selected')
        else:
            print('Not selected')    
    
    if 'Page' in block:
        print('Page: ' + block['Page'])
    print()

def process_text_analysis(client, pdf_file):
    # First convert PDF to images
    print("Converting PDF to images...")
    images = convert_from_path(pdf_file)
    
    # Create output directory if it doesn't exist
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get base filename without extension
    base_filename = os.path.splitext(os.path.basename(pdf_file))[0]
    
    # Open files for writing text and table data
    raw_text_file = open(f'{output_dir}/{base_filename}_rawtext.txt', 'w', encoding='utf-8')
    table_file = open(f'{output_dir}/{base_filename}_tables.txt', 'w', encoding='utf-8')
    
    try:
        # Process each page
        for page_num, image in enumerate(images, start=1):
            print(f"\nProcessing page {page_num}...")
            
            # Write page number to both files
            raw_text_file.write(f"\n\n=== Page {page_num} ===\n\n")
            table_file.write(f"\n\n=== Page {page_num} ===\n\n")
            
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Analyze the document
            response = client.analyze_document(
                Document={'Bytes': img_byte_arr},
                FeatureTypes=["TABLES", "FORMS", "SIGNATURES"]
            )
            
            blocks = response['Blocks']
            width, height = image.size
            
            # Create a new drawing layer
            draw = ImageDraw.Draw(image)
            
            # Create a dictionary to store block information
            blocks_map = {}
            table_blocks = []
            
            # First pass: Create a dictionary of all blocks
            for block in blocks:
                blocks_map[block['Id']] = block
                if block['BlockType'] == "TABLE":
                    table_blocks.append(block)
            
            # Process non-table text
            for block in blocks:
                if 'Text' in block and block['BlockType'] != 'CELL':
                    # Draw bounding boxes
                    ShowBoundingBox(draw, block['Geometry']['BoundingBox'], width, height, 'red')
                    left = width * block['Geometry']['BoundingBox']['Left']
                    top = height * block['Geometry']['BoundingBox']['Top']
                    draw.text((left, top-10), block['Text'][:20], fill='red')
                    
                    # Write to raw text file
                    raw_text_file.write(block['Text'] + '\n')
            
            # Process tables
            if table_blocks:
                table_file.write(f"Found {len(table_blocks)} tables on page {page_num}\n\n")
                
                for table_num, table in enumerate(table_blocks, 1):
                    table_file.write(f"Table {table_num}:\n")
                    
                    # Get all cells that belong to this table
                    if 'Relationships' in table:
                        table_cells = {}
                        max_row = 0
                        max_col = 0
                        
                        # Find table cells and their positions
                        for relationship in table['Relationships']:
                            if relationship['Type'] == 'CHILD':
                                for cell_id in relationship['Ids']:
                                    cell = blocks_map[cell_id]
                                    if cell['BlockType'] == 'CELL':
                                        row_index = cell['RowIndex']
                                        col_index = cell['ColumnIndex']
                                        max_row = max(max_row, row_index)
                                        max_col = max(max_col, col_index)
                                        cell_content = ''
                                        
                                        # Get cell content
                                        if 'Relationships' in cell:
                                            for cell_relationship in cell['Relationships']:
                                                if cell_relationship['Type'] == 'CHILD':
                                                    for word_id in cell_relationship['Ids']:
                                                        word_block = blocks_map[word_id]
                                                        if 'Text' in word_block:
                                                            cell_content += word_block['Text'] + ' '
                                        
                                        table_cells[(row_index, col_index)] = cell_content.strip()
                        
                        # Create and write the formatted table
                        for row in range(1, max_row + 1):
                            row_data = []
                            for col in range(1, max_col + 1):
                                content = table_cells.get((row, col), '')
                                row_data.append(content)
                            
                            # Format row with consistent spacing
                            formatted_row = ' | '.join(cell.ljust(20) for cell in row_data)
                            table_file.write(formatted_row + '\n')
                        
                        table_file.write('\n' + '-'*80 + '\n\n')
            
            # Save the annotated image with the original filename
            output_image_path = f'{output_dir}/{base_filename}_page_{page_num}.png'
            image.save(output_image_path)
            print(f"Annotated image saved as: {output_image_path}")
            
            # Display the image
            image.show()
    
    finally:
        # Close the files
        raw_text_file.close()
        table_file.close()
        
    print(f"\nRaw text saved to: {output_dir}/{base_filename}_rawtext.txt")
    print(f"Table data saved to: {output_dir}/{base_filename}_tables.txt")
    
    return len(blocks)

def query_document(client, pdf_file, question):
    # Convert PDF to images first
    images = convert_from_path(pdf_file)
    
    for page_num, image in enumerate(images, start=1):
        # Convert PIL Image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        response = client.analyze_document(
            Document={'Bytes': img_byte_arr},
            FeatureTypes=["TABLES", "FORMS", "QUERIES"],
            QueriesConfig={'Queries':[
                {'Text': '{}'.format(question)}
            ]}
        )
        
        print(f"\nResults for page {page_num}:")
        for block in response['Blocks']:
            if block["BlockType"] == "QUERY":
                print("Query info:")
                print(block["Query"])
            if block["BlockType"] == "QUERY_RESULT":
                print("Query answer:")
                print(block["Text"])

def process_with_gemini(client, pdf_file, raw_text_path, table_path):
    """
    Process the PDF content with Google Gemini to generate enhanced markdown output.
    
    Args:
        client: AWS Textract client
        pdf_file: Path to the PDF file
        raw_text_path: Path to the raw text file
        table_path: Path to the table data file
        
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
        
        # Convert PDF to images
        print("Converting PDF to images for Gemini processing...")
        images = convert_from_path(pdf_file)
        
        # Read the raw text and table data
        with open(raw_text_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
        
        with open(table_path, 'r', encoding='utf-8') as f:
            table_data = f.read()
        
        # Create the prompt for Gemini
        prompt = """
        Analyze the images and extract all the text into well-formatted markdown.
        
        RULES:
        1. Maintain all tables in proper markdown format
        2. Preserve any mathematical formulas using LaTeX notation
        3. Keep the document structure and hierarchy
        4. Format any measurements, units, and technical specifications correctly
        5. Include any relevant headers and sections
        6. Preserve any numerical data and calculations
        7. Format lists and enumerations properly
        
        To help you, we have already used the OCR from AWS Textract that extracted the raw text from the document as well as the table data. However 
        However, this OCR is not completely accurate, and can contain errors. Therefore, use it as a help to your own skills. 
        """
        
        # Create the content parts, including images
        content_parts = [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"text": f"Raw Text Content from AWS Textract:\n{raw_text}"},
                    {"text": f"Table Data from AWS Textract:\n{table_data}"}
                ]
            }
        ]
        
        # Add images to content parts
        for image in images:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Add image to content parts
            content_parts[0]["parts"].append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(img_byte_arr).decode('utf-8')
                }
            })
        
        # Generate content using Gemini
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-preview-04-17",
            contents=content_parts
        )
        
        markdown_content = response.text.strip().replace("```markdown", "").replace("```", "")
        
        # Save the markdown output
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        base_filename = os.path.splitext(os.path.basename(pdf_file))[0]
        markdown_path = f'{output_dir}/{base_filename}_markdown.md'
        
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"\nGemini-enhanced markdown saved to: {markdown_path}")
        
    except Exception as e:
        print(f"Error in Gemini processing: {str(e)}")
        raise

def main():
    # AWS Credentials Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')  # Default to us-east-2 if not specified

    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS credentials not found in environment variables")

    # Initialize the Textract client with explicit credentials
    client = boto3.client(
        'textract',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    pdf_file = "input/sulzer.pdf"
    #pdf_file = "test1.pdf"
    # Process the document
    block_count = process_text_analysis(client, pdf_file)
    print("\nTotal blocks detected: " + str(block_count))
    
    # Get the paths to the generated files
    output_dir = 'output'
    base_filename = os.path.splitext(os.path.basename(pdf_file))[0]
    raw_text_path = f'{output_dir}/{base_filename}_rawtext.txt'
    table_path = f'{output_dir}/{base_filename}_tables.txt'
    
    # Process with Gemini
    process_with_gemini(client, pdf_file, raw_text_path, table_path)

if __name__ == "__main__":
    main()
