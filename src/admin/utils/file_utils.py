import os
import tempfile
import pymupdf4llm
import asyncio


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file"""
    try:
        md_text = pymupdf4llm.to_markdown(pdf_path)  # Convert directly to Markdown
        return md_text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")


async def extract_text_from_pdf_async(pdf_path):
    """Async wrapper for extract_text_from_pdf"""
    # Use a thread pool to run the CPU-bound PDF extraction
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_text_from_pdf, pdf_path)


def save_temp_file(file_obj, filename=None):
    """Save an uploaded file to a temporary location and return the path"""
    if not filename:
        filename = file_obj.filename

    temp_path = os.path.join(tempfile.gettempdir(), filename)
    file_obj.save(temp_path)
    return temp_path


def cleanup_temp_file(path):
    """Remove a temporary file"""
    try:
        if os.path.exists(path):
            os.remove(path)
        return True
    except Exception:
        return False


def get_file_extension(filename):
    """Get the file extension from a filename"""
    return os.path.splitext(filename.lower())[1]


def read_text_file(file_path, encodings=None):
    """Read text from a file with multiple encoding attempts"""
    if encodings is None:
        encodings = ["utf-8", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # If all encodings fail, try binary mode and try to decode
    with open(file_path, "rb") as f:
        content = f.read()
        try:
            return content.decode("utf-8", errors="replace")
        except Exception as e:
            raise Exception(
                f"Failed to decode file {os.path.basename(file_path)}: {str(e)}"
            )
