import fitz
from concurrent.futures import ThreadPoolExecutor

def _extract_text(page):
    text = page.get_text()
    return text.strip() if text and text.strip() else None

def parse_pdf_from_url_multithreaded(content, max_workers=2, chunk_size=1):
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            pages = list(doc)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                texts = list(executor.map(_extract_text, pages))
            if chunk_size > 1:
                chunks = []
                for i in range(0, len(texts), chunk_size):
                    chunk = ' '.join([t for t in texts[i:i+chunk_size] if t])
                    if chunk:
                        chunks.append(chunk)
                return chunks if chunks else ["No data found in this document (empty PDF)"]
            return [t for t in texts if t] or ["No data found in this document (empty PDF)"]
    except Exception as e:
        print(f"Failed to parse as PDF: {str(e)}")
        return [f"No data found in this document (not PDF or corrupted)"]

def parse_pdf_from_file_multithreaded(file_path, max_workers=2, chunk_size=1):
    try:
        with fitz.open(file_path) as doc:
            pages = list(doc)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                texts = list(executor.map(_extract_text, pages))
            if chunk_size > 1:
                chunks = []
                for i in range(0, len(texts), chunk_size):
                    chunk = ' '.join([t for t in texts[i:i+chunk_size] if t])
                    if chunk:
                        chunks.append(chunk)
                return chunks if chunks else ["No data found in this document (local PDF empty)"]
            return [t for t in texts if t] or ["No data found in this document (local PDF empty)"]
    except Exception as e:
        print(f"Failed to open local file: {str(e)}")
        return [f"No data found in this document (local file error)"]
