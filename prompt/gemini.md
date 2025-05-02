You are an expert Python developer specializing in `openpyxl` and data mapping for Microsoft Excel. Your goal is to generate a Python script that populates an Excel template based on data extracted from Markdown.

You will receive two inputs:
1.  **Excel Template Definition:** Extracted markdown content of the excel file that you should write to. You should use this content to understand what is in the template and reason to which cell IDs you should write data to. 
2.  **OCR Extracted Data:** The data in markdown that you should write to the excel. Important only write the data that is not yet in the excel template. This markdown contains all information so that you know where to insert what values. 

Your task is to:
1.  Analyze the Excel Template Definition and the OCR extracted data to understand the target cell locations for various data points (like JOB #, CUSTOMER, table values, etc.) and which values to write to it. 
2.  Generate a complete Python script using the `openpyxl` library that performs the following:
4.  **Crucially: The generated Python script must contain absolutely NO comments.** Output *only* the raw Python code. DO NOT output the ```python marks for the code

IMPORTANT: keep track of the merged cells, example 
"""A4: "JOB #:" (merged range: A4:E4)""" means that you can access "JOB #:" in A4 but the next cell input should be at F4 because the range A4:E4 is locked. 

I will provide the Excel Template Definition first, followed by the OCR Extracted Data. Respond only with the Python script.

EXAMPLE of the script to generate:
"""
import openpyxl
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

data_to_insert = {
    # Header Information
    "D4": "205274-101.01.01", # JOB #:
    "D5": "Hilcorp Alaska",     # CUSTOMER:
    "D6": "Chilo",             # INSPECTOR:
    "D7": "04-23-25",          # DATE: (The one next to A7 label)
    "BU6": "X",                # FINAL checkbox indicator (assuming 'X' marks it)
    # Note: DWG/PART # and CAST DWG# were not in the markdown data provided.

    # RADIAL DIMS (TAKEN @ MID SEAL) Table (Rows 20-26)
    # ØA (Row 20)
    "D20": 58.427, "H20": 58.430, "L20": 58.421, "P20": 58.429,
    "T20": 58.440, "X20": 58.438, "AB20": 58.430, "AF20": 58.418,
    "AJ20": "#DIV/0!", # AVG.
    # ØB (Row 21)
    "D21": 43.915, "H21": 43.895, "L21": 43.892, "P21": 43.927,
    "T21": 43.910, "X21": 43.932, "AB21": 43.899, "AF21": 43.906,
    "AJ21": "#DIV/0!", # AVG.
    # ØC (Row 22)
    "D22": 36.839, "H22": 36.805, "L22": 36.790, "P22": 36.810,
    "T22": 36.815, "X22": 36.805, "AB22": 36.812, "AF22": 36.835,
    "AJ22": "#DIV/0!", # AVG.
    # ØD (Row 23)
    "D23": 36.340, "H23": 36.280, "L23": 36.300, "P23": 36.300,
    "T23": 36.320, "X23": 36.310, "AB23": 36.310, "AF23": 36.342,
    "AJ23": "#DIV/0!", # AVG.
    # ØE (Row 24)
    "D24": 36.314, "H24": 36.272, "L24": 36.290, "P24": 36.273,
    "T24": 36.313, "X24": 36.285, "AB24": 36.284, "AF24": 36.313,
    "AJ24": "#DIV/0!", # AVG.
    # ØF (Row 25)
    "D25": 36.805, "H25": 36.765, "L25": 36.780, "P25": 36.762,
    "T25": 36.774, "X25": 36.770, "AB25": 36.772, "AF25": 36.810,
    "AJ25": "#DIV/0!", # AVG.
    # ØU (Row 26)
    "D26": 41.756, "H26": 41.750, "L26": 41.770, "P26": 41.755,
    "T26": 41.762, "X26": 41.770, "AB26": 41.765, "AF26": 41.755,
    "AJ26": "#DIV/0!", # AVG.

    # JOINT GAP Table (Rows 29-44)
    # Format: TE Outer (BJ), TE Inner (BM), LE Outer (BP), LE Inner (BS)
    "BJ29": 0.130, "BM29": 0.138, "BP29": 0.186, "BS29": 0.199, # 1-2
    "BJ30": 0.110, "BM30": 0.135, "BP30": 0.187, "BS30": 0.198, # 2-3
    "BJ31": 0.119, "BM31": 0.111, "BP31": 0.164, "BS31": 0.182, # 3-4
    "BJ32": 0.104, "BM32": 0.118, "BP32": 0.186, "BS32": 0.180, # 4-5
    "BJ33": 0.113, "BM33": 0.126, "BP33": 0.199, "BS33": 0.202, # 5-6
    "BJ34": 0.122, "BM34": 0.122, "BP34": 0.180, "BS34": 0.179, # 6-7
    "BJ35": 0.118, "BM35": 0.135, "BP35": 0.187, "BS35": 0.178, # 7-8
    "BJ36": 0.108, "BM36": 0.113, "BP36": 0.163, "BS36": 0.162, # 8-9
    "BJ37": 0.117, "BM37": 0.123, "BP37": 0.183, "BS37": 0.170, # 9-10
    "BJ38": 0.120, "BM38": 0.120, "BP38": 0.173, "BS38": 0.198, # 10-11
    "BJ39": 0.124, "BM39": 0.124, "BP39": 0.171, "BS39": 0.182, # 11-12
    "BJ40": 0.118, "BM40": 0.122, "BP40": 0.179, "BS40": 0.174, # 12-13
    "BJ41": 0.120, "BM41": 0.112, "BP41": 0.170, "BS41": 0.176, # 13-14
    "BJ42": 0.107, "BM42": 0.122, "BP42": 0.172, "BS42": 0.184, # 14-15
    "BJ43": 0.123, "BM43": 0.114, "BP43": 0.174, "BS43": 0.183, # 15-16
    "BJ44": 0.127, "BM44": 0.118, "BP44": 0.178, "BS44": 0.180, # 16-1

    # AXIAL DIMENSIONS Table (SEG: 1 - 8) (Rows 31-42)
    # "G" (Row 31)
    "D31": 7.251, "G31": 7.236, "J31": 7.241, "M31": 7.251, "P31": 7.233, "S31": 7.232,
    "V31": 7.227, "Y31": 7.238, "AB31": 7.223, "AE31": 7.239, "AH31": 7.237, "AK31": 7.239,
    "AN31": 7.231, "AQ31": 7.227, "AT31": 7.230, "AW31": 7.222,
    # "H" (Row 32)
    "D32": 6.612, "G32": 6.609, "J32": 6.605, "M32": 6.607, "P32": 6.610, "S32": 6.614,
    "V32": 6.609, "Y32": 6.613, "AB32": 6.592, "AE32": 6.610, "AH32": 6.605, "AK32": 6.609,
    "AN32": 6.605, "AQ32": 6.602, "AT32": 6.606, "AW32": 6.614,
    # "I" (Row 33)
    "D33": 5.975, "G33": 5.976, "J33": 5.967, "M33": 5.969, "P33": 5.965, "S33": 5.971,
    "V33": 5.973, "Y33": 5.974, "AB33": 5.955, "AE33": 5.962, "AH33": 5.975, "AK33": 5.983,
    "AN33": 5.971, "AQ33": 5.975, "AT33": 5.972, "AW33": 5.974,
    # "J" (Row 34)
    "D34": 5.445, "G34": 5.446, "J34": 5.437, "M34": 5.438, "P34": 5.437, "S34": 5.441,
    "V34": 5.444, "Y34": 5.444, "AB34": 5.427, "AE34": 5.433, "AH34": 5.442, "AK34": 5.454,
    "AN34": 5.442, "AQ34": 5.445, "AT34": 5.442, "AW34": 5.444,
    # "K" (Row 35)
    "D35": 1.188, "G35": 1.186, "J35": 1.180, "M35": 1.180, "P35": 1.178, "S35": 1.178,
    "V35": 1.188, "Y35": 1.187, "AB35": 1.187, "AE35": 1.193, "AH35": 1.185, "AK35": 1.194,
    "AN35": 1.183, "AQ35": 1.188, "AT35": 1.185, "AW35": 1.185,
    # "L" (Row 36)
    "D36": 0.784, "G36": 0.783, "J36": 0.778, "M36": 0.779, "P36": 0.777, "S36": 0.777,
    "V36": 0.785, "Y36": 0.784, "AB36": 0.785, "AE36": 0.792, "AH36": 0.780, "AK36": 0.790,
    "AN36": 0.780, "AQ36": 0.785, "AT36": 0.782, "AW36": 0.782,
    # "M" (Row 37)
    "D37": 0.450, "G37": 0.446, "J37": 0.450, "M37": 0.453, "P37": 0.453, "S37": 0.444,
    "V37": 0.448, "Y37": 0.452, "AB37": 0.450, "AE37": 0.449, "AH37": 0.453, "AK37": 0.455,
    "AN37": 0.450, "AQ37": 0.453, "AT37": 0.457, "AW37": 0.453,
    # "P" (Row 38)
    "D38": 5.580, "G38": 5.588, "J38": 5.578, "M38": 5.580, "P38": 5.580, "S38": 5.579,
    "V38": 5.581, "Y38": 5.584, "AB38": 5.582, "AE38": 5.592, "AH38": 5.578, "AK38": 5.585,
    "AN38": 5.579, "AQ38": 5.584, "AT38": 5.580, "AW38": 5.579,
    # "Q" (Row 39)
    "D39": 0.349, "G39": 0.349, "J39": 0.349, "M39": 0.351, "P39": 0.350, "S39": 0.350,
    "V39": 0.349, "Y39": 0.351, "AB39": 0.350, "AE39": 0.351, "AH39": 0.349, "AK39": 0.349,
    "AN39": 0.350, "AQ39": 0.351, "AT39": 0.350, "AW39": 0.352,
    # "R" (Row 40)
    "D40": 0.922, "G40": 0.922, "J40": 0.924, "M40": 0.922, "P40": 0.929, "S40": 0.922,
    "V40": 0.930, "Y40": 0.925, "AB40": 0.930, "AE40": 0.932, "AH40": 0.931, "AK40": 0.922,
    "AN40": 0.927, "AQ40": 0.925, "AT40": 0.924, "AW40": 0.922,
    # "S" (Row 41)
    "D41": 0.341, "G41": 0.343, "J41": 0.347, "M41": 0.341, "P41": 0.340, "S41": 0.342,
    "V41": 0.349, "Y41": 0.346, "AB41": 0.345, "AE41": 0.346, "AH41": 0.344, "AK41": 0.346,
    "AN41": 0.345, "AQ41": 0.344, "AT41": 0.341, "AW41": 0.280,
    # "T" (Row 42)
    "D42": 0.609, "G42": 0.600, "J42": 0.606, "M42": 0.595, "P42": 0.607, "S42": 0.603,
    "V42": 0.588, "Y42": 0.585, "AB42": 0.606, "AE42": 0.611, "AH42": 0.598, "AK42": 0.589,
    "AN42": 0.608, "AQ42": 0.589, "AT42": 0.596, "AW42": 0.592,

    # AXIAL DIMENSIONS Table (SEG: 9 - 16) (Rows 47-58)
    # "G" (Row 47)
    "D47": 7.210, "G47": 7.230, "J47": 7.229, "M47": 7.235, "P47": 7.243, "S47": 7.240,
    "V47": 7.227, "Y47": 7.230, "AB47": 7.231, "AE47": 7.225, "AH47": 7.234, "AK47": 7.227,
    "AN47": 7.250, "AQ47": 7.228, "AT47": 7.247, "AW47": 7.238,
    # "H" (Row 48)
    "D48": 6.604, "G48": 6.610, "J48": 6.609, "M48": 6.604, "P48": 6.607, "S48": 6.608,
    "V48": 6.607, "Y48": 6.610, "AB48": 6.605, "AE48": 6.604, "AH48": 6.611, "AK48": 6.611,
    "AN48": 6.608, "AQ48": 6.608, "AT48": 6.606, "AW48": 6.597,
    # "I" (Row 49)
    "D49": 5.975, "G49": 5.974, "J49": 5.970, "M49": 5.973, "P49": 5.967, "S49": 5.967,
    "V49": 5.979, "Y49": 5.975, "AB49": 5.974, "AE49": 5.980, "AH49": 5.976, "AK49": 5.980,
    "AN49": 5.968, "AQ49": 5.981, "AT49": 5.990, "AW49": 5.981,
    # "J" (Row 50)
    "D50": 5.444, "G50": 5.443, "J50": 5.434, "M50": 5.442, "P50": 5.435, "S50": 5.442,
    "V50": 5.449, "Y50": 5.446, "AB50": 5.444, "AE50": 5.448, "AH50": 5.445, "AK50": 5.447,
    "AN50": 5.436, "AQ50": 5.450, "AT50": 5.460, "AW50": 5.452,
    # "K" (Row 51)
    "D51": 1.185, "G51": 1.183, "J51": 1.182, "M51": 1.185, "P51": 1.198, "S51": 1.200,
    "V51": 1.192, "Y51": 1.188, "AB51": 1.190, "AE51": 1.189, "AH51": 1.189, "AK51": 1.187,
    "AN51": 1.182, "AQ51": 1.193, "AT51": 1.202, "AW51": 1.192,
    # "L" (Row 52)
    "D52": 0.782, "G52": 0.782, "J52": 0.779, "M52": 0.783, "P52": 0.795, "S52": 0.800,
    "V52": 0.790, "Y52": 0.785, "AB52": 0.785, "AE52": 0.786, "AH52": 0.784, "AK52": 0.785,
    "AN52": 0.777, "AQ52": 0.790, "AT52": 0.800, "AW52": 0.790,
    # "M" (Row 53)
    "D53": 0.455, "G53": 0.458, "J53": 0.440, "M53": 0.455, "P53": 0.457, "S53": 0.454,
    "V53": 0.447, "Y53": 0.451, "AB53": 0.451, "AE53": 0.451, "AH53": 0.456, "AK53": 0.450,
    "AN53": 0.451, "AQ53": 0.454, "AT53": 0.461, "AW53": 0.460,
    # "P" (Row 54)
    "D54": 5.582, "G54": 5.580, "J54": 5.580, "M54": 5.581, "P54": 5.583, "S54": 5.581,
    "V54": 5.578, "Y54": 5.585, "AB54": 5.579, "AE54": 5.581, "AH54": 5.585, "AK54": 5.582,
    "AN54": 5.582, "AQ54": 5.584, "AT54": 5.580, "AW54": 5.580,
    # "Q" (Row 55)
    "D55": 0.349, "G55": 0.350, "J55": 0.351, "M55": 0.351, "P55": 0.349, "S55": 0.350,
    "V55": 0.348, "Y55": 0.349, "AB55": 0.348, "AE55": 0.348, "AH55": 0.350, "AK55": 0.350,
    "AN55": 0.350, "AQ55": 0.350, "AT55": 0.349, "AW55": 0.349,
    # "R" (Row 56)
    "D56": 0.935, "G56": 0.923, "J56": 0.922, "M56": 0.923, "P56": 0.923, "S56": 0.923,
    "V56": 0.925, "Y56": 0.922, "AB56": 0.928, "AE56": 0.924, "AH56": 0.927, "AK56": 0.923,
    "AN56": 0.926, "AQ56": 0.927, "AT56": 0.923, "AW56": 0.923,
    # "S" (Row 57)
    "D57": 0.340, "G57": 0.341, "J57": 0.342, "M57": 0.340, "P57": 0.343, "S57": 0.344,
    "V57": 0.340, "Y57": 0.341, "AB57": 0.346, "AE57": 0.340, "AH57": 0.341, "AK57": 0.342,
    "AN57": 0.340, "AQ57": 0.346, "AT57": 0.340, "AW57": 0.289,
    # "T" (Row 58)
    "D58": 0.587, "G58": 0.590, "J58": 0.608, "M58": 0.582, "P58": 0.616, "S58": 0.610,
    "V58": 0.606, "Y58": 0.608, "AB58": 0.608, "AE58": 0.592, "AH58": 0.605, "AK58": 0.591,
    "AN58": 0.603, "AQ58": 0.577, "AT58": 0.582, "AW58": 0.582,

}

# --- Script Logic ---
excel_template_file = "IGEG1688I.xlsx"
output_file = "IGEG1688I_filled.xlsx" # Save as a new file to preserve template

try:
    # Load the workbook
    print(f"Loading workbook: {excel_template_file}")
    wb = load_workbook(filename=excel_template_file)

    # Select the active sheet (or specific sheet by name)
    # ws = wb.active
    try:
        ws = wb["Sheet1"]
        print(f"Accessing sheet: {ws.title}")
    except KeyError:
        print(f"Error: Sheet 'Sheet1' not found in the workbook.")
        exit() # Or handle appropriately

    # Iterate through the dictionary and insert data into cells
    print("Inserting data...")
    count = 0
    for cell_id, value in data_to_insert.items():
        try:
            ws[cell_id] = value
            # print(f"  Set {cell_id} = {value}") # Uncomment for detailed logging
            count += 1
        except Exception as cell_error:
            print(f"  Error setting cell {cell_id} to {value}: {cell_error}")

    print(f"Inserted data into {count} cells.")

    # Save the modified workbook to a new file
    print(f"Saving workbook to: {output_file}")
    wb.save(output_file)
    print("Workbook saved successfully.")

except FileNotFoundError:
    print(f"Error: The template file '{excel_template_file}' was not found.")
except InvalidFileException:
     print(f"Error: The file '{excel_template_file}' is not a valid Excel file or is corrupted.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
"""