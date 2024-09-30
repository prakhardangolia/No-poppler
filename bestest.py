import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import pandas as pd
import re
import pdf2image
import numpy as np
import os

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'], gpu=False)

# Function to preprocess images
def preprocess_image(image):
    image = image.convert('L')
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    image = image.filter(ImageFilter.SHARPEN)
    return image

def pil_image_to_numpy(image):
    return np.array(image)

def extract_text_using_easyocr(image):
    preprocessed_image = preprocess_image(image)
    image_array = pil_image_to_numpy(preprocessed_image)
    results = reader.readtext(image_array)
    full_text = " ".join([result[1] for result in results])
    return full_text

def extract_text_from_pdf_using_easyocr(pdf_path):
    images = pdf2image.convert_from_path(pdf_path)
    full_text = ""
    for image in images:
        text = extract_text_using_easyocr(image)
        full_text += text + "\n"
    return full_text

def extract_data_from_text(text):
    data = []
    pattern = re.compile(r"(0801[A-Z\d]*[A-Z]?)\s+([A-Za-z\s]+?)(?:\s*\(.*?\))?\s+(\d+(\.\d+)?|A|None|Absent|abs|D)", re.IGNORECASE)
    matches = pattern.findall(text)
    for match in matches:
        enrollment_no = match[0].strip()
        name = match[1].strip()
        marks_or_status = match[2].strip()
        if marks_or_status.lower() in ["a", "absent", "none", "abs"]:
            marks = None
            status = "Absent"
        elif marks_or_status.lower() == "d":
            marks = None
            status = "Detained"
        elif marks_or_status.replace(".", "").isdigit():
            marks = float(marks_or_status)
            status = "Present"
        else:
            marks = None
            status = "Unknown"
        data.append((enrollment_no, name, marks, status))
    return data

def process_data(data):
    df = pd.DataFrame(data, columns=['Enrollment No', 'Name', 'Marks', 'Status'])
    df.dropna(subset=['Enrollment No', 'Name'], inplace=True)
    df.loc[(df['Marks'].notnull()) & (df['Marks'] >= 22), 'Status'] = 'Pass'
    df.loc[(df['Marks'].notnull()) & (df['Marks'] < 22), 'Status'] = 'Fail'
    df['Detained'] = df['Status'] == 'Detained'
    df['Status'] = df['Status'].fillna('Absent')
    passed = df[df['Status'] == 'Pass']
    failed = df[df['Status'] == 'Fail']
    absent = df[df['Status'] == 'Absent']
    detained = df[df['Status'] == 'Detained']
    return passed, failed, absent, detained

def generate_excel(passed, failed, absent, detained, output_path):
    with pd.ExcelWriter(output_path) as writer:
        if not passed.empty:
            passed.to_excel(writer, sheet_name="Passed Students", index=False)
        if not failed.empty:
            failed.to_excel(writer, sheet_name="Failed Students", index=False)
        if not absent.empty:
            absent.to_excel(writer, sheet_name="Absent Students", index=False)
        if not detained.empty:
            detained.to_excel(writer, sheet_name="Detained Students", index=False)

def main():
    st.title("PDF to Excel Converter")
    st.write("Upload a PDF file containing student marks, and receive an Excel file.")

    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file is not None:
        pdf_path = os.path.join("/tmp", uploaded_file.name)  # Save uploaded file temporarily
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.write("Processing...")

        text = extract_text_from_pdf_using_easyocr(pdf_path)

        if not text.strip():
            st.error("No data extracted. Please check the PDF format.")
            return

        data = extract_data_from_text(text)

        passed, failed, absent, detained = process_data(data)

        output_path = os.path.join("/tmp", "student-marks.xlsx")
        generate_excel(passed, failed, absent, detained, output_path)

        st.success("Excel file created successfully!")
        st.write("You can download the Excel file below:")
        with open(output_path, "rb") as f:
            st.download_button("Download Excel File", f, file_name="student-marks.xlsx")

if __name__ == "__main__":
    main()
