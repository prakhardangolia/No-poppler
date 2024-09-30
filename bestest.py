import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import easyocr
import os
from PIL import Image

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'])

def extract_text_using_easyocr(image):
    """Extract text from the given image using EasyOCR."""
    result = reader.readtext(image)
    text = ''
    for (bbox, text_part, prob) in result:
        text += text_part + ' '
    return text.strip()

def extract_text_from_pdf_using_easyocr(pdf_file):
    """Extract text from a PDF file using PyMuPDF and EasyOCR."""
    # Read the PDF file into bytes
    pdf_bytes = pdf_file.read()  # Read the file content into bytes
    doc = fitz.open("pdf", pdf_bytes)  # Open the PDF from bytes
    full_text = ""

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Use EasyOCR to extract text
        text = extract_text_using_easyocr(img)
        full_text += text + "\n"

    return full_text

def generate_excel(passed, failed, absent, detained, output_path):
    """Generate Excel files based on student data."""
    with pd.ExcelWriter(output_path) as writer:
        if not passed.empty:
            passed.to_excel(writer, sheet_name='Passed', index=False)
        if not failed.empty:
            failed.to_excel(writer, sheet_name='Failed', index=False)
        if not absent.empty:
            absent.to_excel(writer, sheet_name='Absent', index=False)
        if not detained.empty:
            detained.to_excel(writer, sheet_name='Detained', index=False)

def process_data(extracted_text):
    """Process the extracted text and classify students based on marks."""
    data = []
    for line in extracted_text.strip().split('\n'):
        try:
            # Assuming data is in the format: Name, Marks
            name, marks = line.rsplit(',', 1)
            marks = marks.strip()
            data.append((name.strip(), marks))
        except ValueError:
            continue  # Skip lines that don't match the expected format

    df = pd.DataFrame(data, columns=['Name', 'Marks'])

    # Classify students based on their marks
    passed = df[df['Marks'].astype(str).str.isnumeric() & (df['Marks'].astype(int) > 21)]
    failed = df[df['Marks'].astype(str).str.isnumeric() & (df['Marks'].astype(int) < 22)]
    absent = df[df['Marks'] == 'A']
    detained = df[df['Marks'] == 'D']
    
    return passed, failed, absent, detained

def main():
    st.title("PDF to Excel Converter")
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    
    if uploaded_file is not None:
        # Extract text from the uploaded PDF
        extracted_text = extract_text_from_pdf_using_easyocr(uploaded_file)

        # Display extracted text
        st.subheader("Extracted Text:")
        st.text(extracted_text)

        # Process data and generate Excel files
        passed, failed, absent, detained = process_data(extracted_text)

        # Show dataframes in the app
        st.subheader("Passed Students")
        st.dataframe(passed)
        st.subheader("Failed Students")
        st.dataframe(failed)
        st.subheader("Absent Students")
        st.dataframe(absent)
        st.subheader("Detained Students")
        st.dataframe(detained)

        # Generate Excel files
        output_path = "students_data.xlsx"
        generate_excel(passed, failed, absent, detained, output_path)
        
        # Allow user to download the generated Excel file
        with open(output_path, "rb") as f:
            st.download_button("Download Excel File", f, file_name=output_path)

if __name__ == "__main__":
    main()
