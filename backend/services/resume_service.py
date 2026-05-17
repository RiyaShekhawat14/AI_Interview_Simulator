try:
    from pypdf import PdfReader
except Exception:
    from PyPDF2 import PdfReader

def extract_resume_text(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return text
