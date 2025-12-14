import os
from PIL import Image
from .db import to_json

BASE_UPLOAD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(BASE_UPLOAD, exist_ok=True)

def save_and_resize(img_file, filename_base: str, max_w: int = 1200):
    """img_file: streamlit UploadedFile; retorna caminho salvo."""
    img = Image.open(img_file)
    
    # Converter RGBA para RGB (JPEG não suporta transparência)
    if img.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = bg
    
    w, h = img.size
    if w > max_w:
        ratio = max_w / float(w)
        img = img.resize((max_w, int(h * ratio)))
    fname = f"{filename_base}.jpg"
    path = os.path.join(BASE_UPLOAD, fname)
    img.save(path, format="JPEG", quality=85)
    return path
