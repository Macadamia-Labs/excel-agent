Analyze the images and extract all the text into well-formatted markdown.
You are provided the following inputs:

    1. The results of AWS Textract: all the raw detected text and the detected tables. 
    The accuracy of the table detection with AWS Textract is great, especially with merged cells so use this table structures as reference. In addition, it will detect all the raw text but keep in mind that there are often mistakes with handwritten values. For example, it extracted valyes like "43-895" where it should have been "43.895". Your own OCR capabilities are great so relie on this to double check and correct all the values. In addition, make sure that all the values make sense. For example, if all the values are numbers like "58.438" with decimal points, you should know that "58-438" is probably wrong and should be corrected.
    2. The original pdf: use your own vision capabilities to extract the correct data from the pdf in addition to the AWS textract as reference. 

RULES:

1. Maintain all tables in proper markdown format.
2. Preserve any mathematical formulas using LaTeX notation (e.g., $...$ or $$...$$).
3. Keep the document structure and hierarchy (headings, paragraphs, lists).
4. Format measurements, units, and technical specifications correctly.
5. Include relevant headers and sections.
6. Preserve numerical data and calculations accurately.
7. Format lists (bulleted and numbered) properly.
8. Output ONLY the markdown content, without any introductory text or code fences like ```markdown.
9. Use a decimal point for numbers rather than a comma: e.g. "58.438"

IMPORTANT: Pay attention to revision numbering, they could be given in romanic numbering like I, II, III, etc. 