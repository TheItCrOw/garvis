import base64
import io
from PIL import Image, ImageOps
import binascii
import re
import math
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

def resize_and_compress_base64(b64, quality=67):
    img_data = base64.b64decode(b64)
    img = Image.open(BytesIO(img_data))
    width, height = img.size

    output_size=(width * 0.66, height * 0.66)
    img.thumbnail(output_size) # Maintains aspect ratio [1]
    
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True) # [12]
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def png_b64_to_jpg_b64_no_alpha(
    png_b64: str,
    bg=(255, 255, 255),
    quality: int = 100
) -> str:
    """
    Convert a base64-encoded PNG image (optionally a data URL) to a base64-encoded JPEG,
    removing transparency by compositing onto a solid background.

    Args:
        png_b64: Base64 string, with or without a 'data:image/png;base64,...' prefix.
        bg: Background RGB tuple (default white).
        quality: JPEG quality (1-95 recommended).

    Returns:
        Base64 string of the resulting JPEG (no data URL prefix).
    """
    img = Image.open(io.BytesIO(png_b64))

    # Remove alpha by compositing if needed
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, bg)
        background.paste(img, mask=img.split()[-1])  # alpha channel
        out = background
    else:
        out = img.convert("RGB")

    # Encode to JPEG bytes
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=quality, optimize=True)
    jpg_bytes = buf.getvalue()

    # Return base64 (no prefix)
    return base64.b64encode(jpg_bytes).decode("utf-8")