import zipfile
from io import BytesIO
from .document_extractor import parse_pdf_from_url_multithreaded
from .ocr_extractor import is_image, extract_text_from_image_bytes

def extract_from_zip_bytes(zip_bytes):
    """
    Extract and process files inside a ZIP archive.
    Returns a dictionary: {filename: extracted_text_list}
    """
    results = {}
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as z:
            for file_name in z.namelist():
                try:
                    file_data = z.read(file_name)
                except Exception as e:
                    results[file_name] = [f"Failed to read file: {e}"]
                    continue

                # PDF files
                if file_name.lower().endswith(".pdf"):
                    results[file_name] = parse_pdf_from_url_multithreaded(BytesIO(file_data))

                # Image files
                elif is_image(file_data):
                    text = extract_text_from_image_bytes(file_data)
                    results[file_name] = [text] if text else ["No data found (image empty)"]

                # Unsupported files
                else:
                    results[file_name] = ["Unsupported file type inside ZIP"]

        return results if results else {"ZIP": ["No supported files found in archive"]}

    except zipfile.BadZipFile:
        return {"ZIP": ["Invalid or corrupted ZIP file"]}
    except Exception as e:
        return {"ZIP": [f"Error processing ZIP: {e}"]}
