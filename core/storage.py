import os
from io import BytesIO
from PIL import Image
import requests
import traceback

# Local upload directory (fallback)
BASE_UPLOAD = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(BASE_UPLOAD, exist_ok=True)


def _upload_to_supabase(buf: BytesIO, key: str) -> str | None:
    """Tenta enviar o buffer para Supabase Storage e retorna URL pública ou None."""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    bucket = os.environ.get('SUPABASE_BUCKET', 'uploads')
    if not (supabase_url and supabase_key):
        return None

    # Correct Supabase Storage upload endpoint: POST /storage/v1/object/{bucket}/{file_path}
    upload_url = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{key}"
    headers = {
        'apikey': supabase_key,
        'Authorization': f'Bearer {supabase_key}',
        'Content-Type': 'image/jpeg',
        'x-upsert': 'true',
    }
    data = buf.getvalue()
    try:
        print(f"[storage] supabase upload start: url={upload_url} name={key}")
        resp = requests.post(upload_url, headers=headers, data=data, timeout=30)
        try:
            resp.raise_for_status()
        except Exception:
            # Log response for debugging
            print(f"[storage] supabase upload HTTP error: status={getattr(resp, 'status_code', None)} body={getattr(resp, 'text', None)}")
            print("[storage] exception:")
            traceback.print_exc()
            return None
        # public URL for public buckets
        public_url = f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{key}"
        print(f"[storage] supabase upload success: {public_url}")
        return public_url
    except Exception:
        print("[storage] supabase upload failed with exception:")
        traceback.print_exc()
        return None


def save_and_resize(img_file, filename_base: str, max_w: int = 1200):
    """img_file: streamlit UploadedFile; retorna URL pública ou caminho salvo localmente."""
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
    key = fname  # store at root of bucket under filename

    # Primeiro, tentar fazer upload para Supabase se configurado
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)

    public_url = _upload_to_supabase(buf, key)
    if public_url:
        return public_url

    # Fallback: salvar localmente e retornar caminho
    path = os.path.join(BASE_UPLOAD, fname)
    with open(path, 'wb') as f:
        f.write(buf.getvalue())
    return path
