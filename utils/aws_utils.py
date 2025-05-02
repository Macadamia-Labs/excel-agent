import os
import boto3
import tempfile
from dotenv import load_dotenv
from fastapi import HTTPException
import io
from PIL import Image
from pdf2image import convert_from_path

# Load environment variables
load_dotenv()

def get_textract_client():
    """Initializes and returns AWS Textract client."""
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')

    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise HTTPException(status_code=500, detail="AWS credentials not found in environment variables")

    try:
        client = boto3.client(
            'textract',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize AWS Textract client: {str(e)}")

def extract_text_and_tables(client, doc_path: str) -> tuple[str, str]:
    """
    Processes a document (PDF or image) using Textract, saves raw text and table data to temporary files, 
    and returns the paths to these files.
    """
    base_filename = os.path.splitext(os.path.basename(doc_path))[0]
    # Use temp files instead of writing to output dir directly in this utility
    raw_text_file_path = tempfile.mktemp(suffix=f"_{base_filename}_rawtext.txt")
    table_file_path = tempfile.mktemp(suffix=f"_{base_filename}_tables.txt")

    try:
        with open(raw_text_file_path, 'w', encoding='utf-8') as raw_text_file, \
             open(table_file_path, 'w', encoding='utf-8') as table_file:

            # Handle PDF or image file
            file_ext = os.path.splitext(doc_path)[1].lower()
            if file_ext == '.pdf':
                images = convert_from_path(doc_path)
            else:
                # For image files, create a single-item list
                images = [Image.open(doc_path)]

            for page_num, image in enumerate(images, start=1):
                raw_text_file.write(f"\n\n=== Page {page_num} ===\n\n")
                table_file.write(f"\n\n=== Page {page_num} ===\n\n")

                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()

                try:
                    response = client.analyze_document(
                        Document={'Bytes': img_byte_arr},
                        FeatureTypes=["TABLES", "FORMS", "SIGNATURES"]
                    )
                except Exception as e:
                     raise HTTPException(status_code=500, detail=f"AWS Textract API error on page {page_num}: {str(e)}")

                blocks = response.get('Blocks', [])
                blocks_map = {block['Id']: block for block in blocks}
                table_blocks = [block for block in blocks if block['BlockType'] == "TABLE"]

                # Process non-table text
                for block in blocks:
                    if 'Text' in block and block['BlockType'] != 'CELL':
                        raw_text_file.write(block['Text'] + '\n')

                # Process tables
                if table_blocks:
                    table_file.write(f"Found {len(table_blocks)} tables on page {page_num}\n\n")
                    for table_num, table in enumerate(table_blocks, 1):
                        table_file.write(f"Table {table_num}:\n")
                        if 'Relationships' in table:
                            table_cells = {}
                            max_row, max_col = 0, 0
                            for relationship in table['Relationships']:
                                if relationship['Type'] == 'CHILD':
                                    for cell_id in relationship['Ids']:
                                        cell = blocks_map.get(cell_id)
                                        if cell and cell['BlockType'] == 'CELL':
                                            row_index = cell['RowIndex']
                                            col_index = cell['ColumnIndex']
                                            max_row = max(max_row, row_index)
                                            max_col = max(max_col, col_index)
                                            cell_content = ''
                                            if 'Relationships' in cell:
                                                for cell_relationship in cell['Relationships']:
                                                    if cell_relationship['Type'] == 'CHILD':
                                                        for word_id in cell_relationship['Ids']:
                                                            word_block = blocks_map.get(word_id)
                                                            if word_block and 'Text' in word_block:
                                                                cell_content += word_block['Text'] + ' '
                                            table_cells[(row_index, col_index)] = cell_content.strip()
                            
                            for row in range(1, max_row + 1):
                                row_data = [table_cells.get((row, col), '') for col in range(1, max_col + 1)]
                                formatted_row = ' | '.join(cell.ljust(20) for cell in row_data) # Keep basic formatting
                                table_file.write(formatted_row + '\n')
                            table_file.write('\n' + '-'*80 + '\n\n')

        return raw_text_file_path, table_file_path

    except Exception as e:
        # Clean up temp files if error occurs during processing
        from .file_utils import cleanup_files # Avoid circular import at top level
        cleanup_files(raw_text_file_path, table_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing document with Textract: {str(e)}") 