import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import pandas as pd
import re
import numpy as np

# Initialize EasyOCR Reader
reader = easyocr.Reader(['en'], gpu=False)

# Function to preprocess images
def preprocess_image(image):
    image = image.convert('L')  # Convert to grayscale
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)  # Enhance contrast
    image = image.filter(ImageFilter.MedianFilter(size=3))  # Reduce noise
    image = image.filter(ImageFilter.SHARPEN)  # Sharpen image
    return image

# Function to convert PIL Image to numpy array
def pil_image_to_numpy(image):
    return np.array(image)

# Function to extract text from image using EasyOCR
def extract_text_using_easyocr(image):
    preprocessed_image = preprocess_image(image)  # Preprocess the image
    image_array = pil_image_to_numpy(preprocessed_image)  # Convert PIL Image to numpy array
    results = reader.readtext(image_array)  # Use EasyOCR to extract text
    full_text = " ".join([result[1] for result in results])
    return full_text

# Function to extract data from text using regex
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

# Function to process the data
def process_data(data):
    df = pd.DataFrame(data, columns=['Enrollment No', 'Name', 'Marks', 'Status'])
    df.dropna(subset=['Enrollment No', 'Name'], inplace=True)  # Drop rows with missing values
    df.loc[(df['Marks'].notnull()) & (df['Marks'] >= 22), 'Status'] = 'Pass'
    df.loc[(df['Marks'].notnull()) & (df['Marks'] < 22), 'Status'] = 'Fail'
    df['Detained'] = df['Status'] == 'Detained'
    df['Status'] = df['Status'].fillna('Absent')

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

# Main function for Streamlit app
def main():
    st.title("Student Marks Extractor from PDF")
    
    # Upload PDF file
    pdf_file = st.file_uploader("Upload PDF file", type=["pdf"])

    if pdf_file is not None:
        images = pdf2image.convert_from_bytes(pdf_file.read())  # Convert PDF to images
        full_text = ""

        for image in images:
            text = extract_text_using_easyocr(image)
            full_text += text + "\n"

        if not full_text.strip():
            st.warning("No data extracted. Please check the PDF format.")
            return

        # Extract data using regex
        data = extract_data_from_text(full_text)
        passed, failed, absent, detained = process_data(data)

        # Display results
        st.subheader("Results")
        st.write("Total students:", len(data))
        st.write("Passed students:", len(passed))
        st.write("Failed students:", len(failed))
        st.write("Absent students:", len(absent))
        st.write("Detained students:", len(detained))

        # Show DataFrames
        st.write("Passed Students:", passed)
        st.write("Failed Students:", failed)
        st.write("Absent Students:", absent)
        st.write("Detained Students:", detained)

        # Download button for Excel file
        output_path = "student_marks.xlsx"
        generate_excel(passed, failed, absent, detained, output_path)
        with open(output_path, "rb") as f:
            st.download_button("Download Excel file", f, "student_marks.xlsx")

if __name__ == "__main__":
    main()
