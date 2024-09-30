import os
import io
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import pandas as pd
import re
import numpy as np
import fitz  # PyMuPDF
import streamlit as st

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

# Function to extract images from PDF
def extract_images_from_pdf(pdf_path):
    images = []
    with fitz.open(pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            image_list = page.get_images(full=True)
            for img in image_list:
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                images.append(image)
    return images

# Function to extract text from PDF using EasyOCR
def extract_text_from_pdf_using_easyocr(pdf_path):
    images = extract_images_from_pdf(pdf_path)
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
        if not passed.empty:
            passed.to_excel(writer, sheet_name="Passed Students", index=False)
        if not failed.empty:
            failed.to_excel(writer, sheet_name="Failed Students", index=False)
        if not absent.empty:
            absent.to_excel(writer, sheet_name="Absent Students", index=False)
        if not detained.empty:
            detained.to_excel(writer, sheet_name="Detained Students", index=False)

# Main function
def main():
    st.title("Student Marks Extraction from PDF")

    pdf_file = st.file_uploader("Upload a PDF", type=["pdf"])

    if pdf_file is not None:
        # Create a temporary directory for saving uploaded files
        temp_dir = "temp_dir"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)  # Create the directory if it doesn't exist

        # Save the uploaded file temporarily
        pdf_path = os.path.join(temp_dir, pdf_file.name)
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getbuffer())

        # Check if the PDF file exists
        if not os.path.exists(pdf_path):
            st.error(f"Error: The file {pdf_path} does not exist.")
            return

        # Attempt to extract text from the PDF using EasyOCR
        text = extract_text_from_pdf_using_easyocr(pdf_path)

        if not text.strip():
            st.error("No data extracted. Please check the PDF format.")
            return

        # Extract data using regex
        data = extract_data_from_text(text)

        # Process the data
        passed, failed, absent, detained = process_data(data)

        # Generate Excel output path
        output_path = os.path.join(temp_dir, "student-marks.xlsx")
        generate_excel(passed, failed, absent, detained, output_path)

        # Display DataFrames in the app
        st.subheader("Passed Students")
        st.dataframe(passed)

        st.subheader("Failed Students")
        st.dataframe(failed)

        st.subheader("Absent Students")
        st.dataframe(absent)

        st.subheader("Detained Students")
        st.dataframe(detained)

        # Provide a download link for the generated Excel file
        with open(output_path, "rb") as f:
            st.download_button("Download Excel File", f, "student-marks.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
