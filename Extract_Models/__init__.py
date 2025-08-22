from io import BytesIO
import requests
import os

from .document_extractor import parse_pdf_from_url_multithreaded, parse_pdf_from_file_multithreaded
from .ocr_extractor import is_image, extract_text_from_image_bytes
from .web_extractor import extract_text_from_html
from .zip_extractor import extract_from_zip_bytes
from .audio_extractor import transcribe_audio


def parse_document_url(url):
    try:
        res = requests.get(url)
        content = res.content
        content_type = res.headers.get("content-type", "").lower()
    except Exception as e:
        return [f"Download error: {str(e)}"]

    if "text/html" in content_type or url.endswith(".html"):
        return extract_text_from_html(content)

    if "zip" in content_type or url.endswith(".zip"):
        zip_results = extract_from_zip_bytes(content)
        return [f"{name}: {text}" for name, texts in zip_results.items() for text in texts]

    if "image" in content_type or is_image(content):
        text = extract_text_from_image_bytes(content)
        return [text] if text else ["No data found (image empty)"]

    if "pdf" in content_type or url.endswith(".pdf"):
        return parse_pdf_from_url_multithreaded(BytesIO(content))

    if any(ext in content_type for ext in ["audio", "mpeg", "mp3", "wav"]) or url.endswith((".mp3", ".wav", ".ogg", ".m4a")):
        return [transcribe_audio(url)]

    return ["Unsupported file type"]


def parse_document_file(file_path):
    if file_path.lower().endswith(".zip"):
        with open(file_path, "rb") as f:
            zip_results = extract_from_zip_bytes(f.read())
        return [f"{name}: {text}" for name, texts in zip_results.items() for text in texts]

    if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp")):
        with open(file_path, "rb") as f:
            text = extract_text_from_image_bytes(f.read())
        return [text] if text else ["No data found (image empty)"]

    if file_path.lower().endswith(".pdf"):
        return parse_pdf_from_file_multithreaded(file_path)

    if file_path.lower().endswith(".html"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return extract_text_from_html(content)

    if file_path.lower().endswith((".mp3", ".wav", ".ogg", ".m4a")):
        return [transcribe_audio(file_path)]

    return ["Unsupported file type"]
