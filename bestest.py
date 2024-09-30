import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import pandas as pd
import re
import pdf2image
import numpy as np

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'], gpu=False)

# Function to preprocess images
def preprocess_image(image):
    # Convert to grayscale
    image = image.convert('L')

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    # Apply a blur filter to reduce noise
    image = image.filter(ImageFilter.MedianFilter(size=3))

    # Sharpen the image to make text clearer
    image = image.filter(ImageFilter.SHARPEN)

    return image

# Function to convert PIL Image to numpy array
def pil_image_to_numpy(image):
    return np.array(image)

# Function to extract text from image using EasyOCR
def extract_text_using_easyocr(image):
    # Preprocess the image
    preprocessed_image = preprocess_image(image)

    # Convert PIL Image to numpy array
    image_array = pil_image_to_numpy(preprocessed_image)

    # Use EasyOCR to extract text
    results = reader.readtext(image_array)

    # Combine the text results
    full_text = " ".join([result[1] for result in results])
    return full_text

# Function to convert PDF to images and use EasyOCR
def extract_text_from_pdf_using_easyocr(pdf_file):
    images = pdf2image.convert_from_bytes(pdf_file.read())  # Convert PDF to images
    full_text = ""
    for image in images:
        text = extract_text_using_easyocr(image)
        full_text += text + "\n"
    return full_text

# Function to extract data from text using regex
def extract_data_from_text(text):
    data = []

    # Regex pattern to handle roll numbers, names, and marks/status including decimals
    pattern = re.compile(r"(0801[A-Z\d]*[A-Z]?)\s+([A-Za-z\s]+?)(?:\s*\(.*?\))?\s+(\d+(\.\d+)?|A|None|Absent|abs|D)", re.IGNORECASE)
    matches = pattern.findall(text)

    for match in matches:
        enrollment_no = match[0].strip()
        name = match[1].strip()
        marks_or_status = match[2].strip()

        # Determine status
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

# Function to process the data
def process_data(data):
    df = pd.DataFrame(data, columns=['Enrollment No', 'Name', 'Marks', 'Status'])

    # Drop rows where 'Enrollment No' or 'Name' is missing
    df.dropna(subset=['Enrollment No', 'Name'], inplace=True)

    # Handling status based on marks without modifying the decimal values
    df.loc[(df['Marks'].notnull()) & (df['Marks'] >= 22), 'Status'] = 'Pass'  # 22 or higher is Pass
    df.loc[(df['Marks'].notnull()) & (df['Marks'] < 22), 'Status'] = 'Fail'  # Less than 22 is Fail

    # Create a 'Detained' column for those with 'Detained' status
    df['Detained'] = df['Status'] == 'Detained'

    # Update status for 'Absent'
    df['Status'] = df['Status'].fillna('Absent')

    # Separate data into different categories
    passed = df[df['Status'] == 'Pass']
    failed = df[df['Status'] == 'Fail']
    absent = df[df['Status'] == 'Absent']
    detained = df[df['Status'] == 'Detained']

    return passed, failed, absent, detained

# Function to generate Excel sheets
def generate_excel(passed, failed, absent, detained, output_path):
    with pd.ExcelWriter(output_path) as writer:
        # Flag to track if at least one sheet is created
        sheet_created = False
        
        if not passed.empty:
            passed.to_excel(writer, sheet_name="Passed Students", index=False)
            sheet_created = True
        if not failed.empty:
            failed.to_excel(writer, sheet_name="Failed Students", index=False)
            sheet_created = True
        if not absent.empty:
            absent.to_excel(writer, sheet_name="Absent Students", index=False)
            sheet_created = True
        if not detained.empty:
            detained.to_excel(writer, sheet_name="Detained Students", index=False)
            sheet_created = True

        # Check if any sheets were created
        if not sheet_created:
            raise ValueError("No data to write to Excel. At least one sheet must be created.")

# Streamlit UI
def main():
    st.title("Student Marks Extraction from PDF")

    # File upload
    pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    
    if pdf_file is not None:
        # Attempt to extract text from the PDF using EasyOCR
        try:
            text = extract_text_from_pdf_using_easyocr(pdf_file)
            
            if not text.strip():
                st.error("No data extracted. Please check the PDF format.")
                return

            # Extract data using regex
            data = extract_data_from_text(text)

            # Process the data
            passed, failed, absent, detained = process_data(data)

            # Count and display the number of students in each category
            total_students = len(pd.concat([passed, failed, absent, detained], ignore_index=True))
            st.write(f"Total number of students: {total_students}")
            st.write(f"Number of students who passed: {len(passed)}")
            st.write(f"Number of students who failed: {len(failed)}")
            st.write(f"Number of students who were absent: {len(absent)}")
            st.write(f"Number of students who were detained: {len(detained)}")

            # Generate Excel file
            output_path = "student-marks.xlsx"
            generate_excel(passed, failed, absent, detained, output_path)

            # Provide download link for the Excel file
            with open(output_path, "rb") as f:
                st.download_button("Download Excel file", f, file_name="student-marks.xlsx")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
