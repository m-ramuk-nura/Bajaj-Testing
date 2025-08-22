import imghdr
from PIL import Image
import pytesseract
from io import BytesIO

def is_image(content):
    return imghdr.what(None, h=content) in ["jpeg", "png", "bmp", "gif", "tiff", "webp"]

def extract_text_from_image_bytes(image_bytes):
    image = Image.open(BytesIO(image_bytes))
    return pytesseract.image_to_string(image).strip()
