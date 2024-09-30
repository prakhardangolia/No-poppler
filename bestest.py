import streamlit as st
import pandas as pd
import easyocr
import fitz  # Importing fitz for PDF handling
from io import BytesIO

# Function to extract text using EasyOCR
def extract_text_using_easyocr(image):
    """Extract text from an image using EasyOCR."""
    reader = easyocr.Reader(['en'])  # Create an EasyOCR reader
    result = reader.readtext(image)
    text = ''
    for (bbox, text, prob) in result:
        text += f"{text}\n"  # Append the text
    return text.strip()

# Function to extract text from PDF using EasyOCR
def extract_text_from_pdf_using_easyocr(pdf_file):
    """Extract text from a PDF file using EasyOCR."""
    images = []  # List to store extracted images
    pdf_reader = fitz.open(pdf_file)  # Open the PDF file
    for page in pdf_reader:
        img = page.get_pixmap()  # Convert page to an image
        img_bytes = img.tobytes()  # Convert image to bytes
        images.append(img_bytes)  # Append the image bytes to the list
    pdf_reader.close()  # Close the PDF file

    # Extract text from each image
    full_text = ''
    for img in images:
        full_text += extract_text_using_easyocr(img)

    return full_text

# Function to process the extracted text
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

    # Convert 'Marks' to numeric, coercing errors to NaN
    df['Marks'] = pd.to_numeric(df['Marks'], errors='coerce')

    # Classify students based on their marks
    passed = df[df['Marks'] > 21]
    failed = df[df['Marks'] < 22]
    absent = df[df['Marks'].isna() & df['Marks'].astype(str).str.contains('A')]
    detained = df[df['Marks'].isna() & df['Marks'].astype(str).str.contains('D')]
    
    return passed, failed, absent, detained

# Function to generate Excel files based on the classified data
def generate_excel(passed, failed, absent, detained, output_path):
    """Generate Excel files for the classified data."""
    with pd.ExcelWriter(output_path) as writer:
        passed.to_excel(writer, sheet_name='Passed', index=False)
        failed.to_excel(writer, sheet_name='Failed', index=False)
        absent.to_excel(writer, sheet_name='Absent', index=False)
        detained.to_excel(writer, sheet_name='Detained', index=False)

# Main function to run the Streamlit app
def main():
    st.title("Student Marks Classification")
    
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    
    if uploaded_file:
        extracted_text = extract_text_from_pdf_using_easyocr(uploaded_file)
        st.text_area("Extracted Text", value=extracted_text, height=300)
        
        passed, failed, absent, detained = process_data(extracted_text)
        
        # Display the results
        st.subheader("Passed Students")
        st.write(passed)
        
        st.subheader("Failed Students")
        st.write(failed)
        
        st.subheader("Absent Students")
        st.write(absent)
        
        st.subheader("Detained Students")
        st.write(detained)
        
        # Generate and download Excel files
        output_path = "student_marks_classification.xlsx"
        if st.button("Generate Excel Files"):
            generate_excel(passed, failed, absent, detained, output_path)
            with open(output_path, "rb") as f:
                st.download_button("Download Excel File", f, file_name=output_path)

if __name__ == "__main__":
    main()
