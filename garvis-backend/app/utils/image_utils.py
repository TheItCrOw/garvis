import base64
import io
from PIL import Image, ImageOps
import binascii
from io import BytesIO

def tiff_bytes_to_jpeg_bytes(tiff_bytes: bytes, *, quality: int = 95) -> bytes:
    with Image.open(io.BytesIO(tiff_bytes)) as im:
        # If it's a multi-page TIFF, take the first page/frame
        try:
            im.seek(0)
        except EOFError:
            pass

        # Normalize orientation from EXIF, if present
        im = ImageOps.exif_transpose(im)

        # JPEG can't store alpha/palette/1-bit etc. Ensure RGB
        if im.mode in ("RGBA", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")

        out = io.BytesIO()
        im.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
        return out.getvalue()
    
def b64_jpeg_from_tiff_bytes(tiff_bytes: bytes, *, quality: int = 95) -> str:
    jpeg_bytes = tiff_bytes_to_jpeg_bytes(tiff_bytes, quality=quality)
    return base64.b64encode(jpeg_bytes).decode("utf-8")    

def detect_image_mime_pillow(b64: str):
    # strip data URL if present
    if b64.strip().startswith("data:"):
        _, _, b64 = b64.partition(",")

    b64 = b64.strip()
    b64 += "=" * (-len(b64) % 4)

    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return {"is_image": False, "mime": None, "format": None}

    try:
        bio = BytesIO(raw)
        img = Image.open(bio)
        img.verify()  # verifies integrity without decoding full image
        fmt = (img.format or "").upper()  # e.g. 'PNG', 'JPEG'
    except Exception:
        return {"is_image": False, "mime": None, "format": None}

    mime = Image.MIME.get(fmt)  # e.g. 'image/png'
    return {"is_image": True, "mime": mime, "format": fmt}