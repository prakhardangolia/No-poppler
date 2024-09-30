import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import pandas as pd
import re
import fitz  # PyMuPDF
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

# Function to convert PDF to images using PyMuPDF
def extract_text_from_pdf_using_easyocr(pdf_path):
    images = extract_images_from_pdf(pdf_path)
    full_text = ""
    for image in images:
        text = extract_text_using_easyocr(image)
        full_text += text + "\n"
    return full_text

# Function to extract images from PDF using PyMuPDF
def extract_images_from_pdf(pdf_path):
    images = []
    with fitz.open(pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf.load_page(page_num)
            pix = page.get_pixmap()
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(image)
    return images

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
    pdf_path = r'E:\programming\newtest\Discrete mid matks-output.pdf'  # Replace with your actual PDF path
    output_path = r'E:\programming\newtest\student-marks.xlsx'

    text = extract_text_from_pdf_using_easyocr(pdf_path)

    if not text.strip():
        print("No data extracted. Please check the PDF format.")
        return

    data = extract_data_from_text(text)

    print("Extracted Data:\n", data)

    passed, failed, absent, detained = process_data(data)

    print("\nPassed Students:\n", passed)
    print("\nFailed Students:\n", failed)
    print("\nAbsent Students:\n", absent)
    print("\nDetained Students:\n", detained)

    total_students = len(pd.concat([passed, failed, absent, detained], ignore_index=True))
    print(f"\nTotal number of students: {total_students}")
    print(f"Number of students who passed: {len(passed)}")
    print(f"Number of students who failed: {len(failed)}")
    print(f"Number of students who were absent: {len(absent)}")
    print(f"Number of students who were detained: {len(detained)}")

    try:
        generate_excel(passed, failed, absent, detained, output_path)
        print("Excel file created successfully.")
    except PermissionError:
        print(f"Permission denied: Unable to write to '{output_path}'. Ensure the file is not open and try again.")
    except Exception as e:
        print(f"Error creating Excel file: {e}")

if __name__ == "__main__":
    main()
