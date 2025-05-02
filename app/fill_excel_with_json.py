import openpyxl
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
import os # Added for basename

def fill_excel_template(excel_template_file, output_file, data_to_insert):
    print(f"Starting to fill Excel template '{os.path.basename(excel_template_file)}'...")
    try:
        wb = load_workbook(filename=excel_template_file)
        ws = wb["Sheet1"]
        for cell_id, value in data_to_insert.items():
            ws[cell_id] = value
        wb.save(output_file)
        print(f"Successfully filled Excel template and saved to '{os.path.basename(output_file)}'.")
        return True, None
    except FileNotFoundError:
        print(f"Error filling template '{os.path.basename(excel_template_file)}': Template file not found.")
        return False, "Template file not found."
    except InvalidFileException:
        print(f"Error filling template '{os.path.basename(excel_template_file)}': Invalid Excel file.")
        return False, "Invalid Excel file."
    except KeyError:
        print(f"Error filling template '{os.path.basename(excel_template_file)}': Sheet1 not found.")
        return False, "Sheet1 not found in the workbook."
    except Exception as e:
        print(f"Error filling template '{os.path.basename(excel_template_file)}': {str(e)}")
        return False, str(e)