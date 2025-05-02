# excel-agent

A Python toolchain for extracting, filling, and analyzing Excel files, with AI-powered analysis using Google Gemini.

## What it does

- Converts Excel files to Markdown
- Fills Excel templates with data
- Uses Google Gemini to analyze and compare template and OCR-extracted data
- **Now also provides a FastAPI endpoint to fill Excel templates via HTTP**

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Set up your API key:**
   - Create a `.env` file with:
     ```
     GEMINI_API_KEY=your_google_gemini_api_key
     ```
3. **Input files:**
   - Place your Excel template in `input/`
   - Place OCR Markdown files in `output/` (if needed)

## Usage

- **Convert Excel to Markdown:**
  ```bash
  python main.py
  ```
- **Fill Excel template:**
  - Edit `data_to_insert` in `excel.py` as needed
  ```bash
  python excel.py
  ```
- **Run Gemini analysis:**
  ```bash
  python gemini.py
  ```
- **Run FastAPI app:**
  ```bash
  uvicorn fastapi-app:app --reload
  ```
- **Fill Excel via API:**
  - POST to `/fill-excel/` with an Excel file and a JSON dictionary of cell values.
  - Example using `curl`:
    ```bash
    curl -X POST "http://localhost:8000/fill-excel/" \
      -F "excel_template=@input/IGEG1688I.xlsx" \
      -F 'data_json={"F4":"205274-101.01.01","F5":"Hilcorp Alaska"}' \
      -o filled_template.xlsx
    ```

## Files

- `main.py` – Excel to Markdown
- `excel.py` – Fill Excel template
- `gemini.py` – AI analysis
- `fastapi-app.py` – FastAPI app for Excel filling
- `prompt/gemini.md` – Gemini prompt

---

MIT License
