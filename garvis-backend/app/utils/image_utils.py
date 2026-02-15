import base64
import io
from PIL import Image, ImageOps
import binascii
import re
import math
from io import BytesIO

def tiff_bytes_to_jpeg_bytes(tiff_bytes: bytes, *, quality: int = 100) -> bytes:
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

def decrease_image_size(b64, quality=50):
    """
    Lower the dimensions and quality of the image. Either using the 512 pixels or the 0.66 of the longest side, whatever side is lower.
    Then apply quality reduction at 50 (1-100), this is to save and minimize costs with the orchestrsating LLM
    """
    fallback_minimum_side = 512
    img_data = base64.b64decode(b64, validate=True)
    img = Image.open(BytesIO(img_data))
    
    width, height = img.size
    resized_size = (width * 0.66, height * 0.66)
    max_size = max(resized_size)
    actual_size = min(fallback_minimum_side, max_size)
    output_size=(actual_size, actual_size)
    img.thumbnail(output_size) # Maintains aspect ratio [1]
    
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True) # [12]
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def image_dimensions_to_square(
    b64: str,
    quality: int = 100
) -> str:
    """
    "Squares" the image if the input image is not a perfect square, the image will be centered and side with lower dimension will be filled with black border.
    """
    img_data = base64.b64decode(b64, validate=True)
    img = Image.open(BytesIO(img_data)).convert("RGB")

    width, height = img.size
    side = max(width, height)

    # Create square black canvas and center the image on it
    square = Image.new("RGB", (side, side), (0, 0, 0))
    square.paste(img, ((side - width) // 2, (side - height) // 2))

    buffer = BytesIO()
    square.save(buffer, format="JPEG", quality=quality, optimize=True)

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

    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=quality, optimize=True)
    jpg_bytes = buf.getvalue()

    return base64.b64encode(jpg_bytes).decode("utf-8")

def bmp_b64_to_jpg_b64(
    bmp_b64: str,
    quality: int = 100
) -> str:
    """
    Convert a base64-encoded BMP image (optionally a data URL) to a base64-encoded JPEG,
    removing transparency (if present) by compositing onto a solid background.

    Args:
        bmp_b64: Base64 string, with or without a 'data:image/bmp;base64,...' prefix.
        bg: Background RGB tuple (default white).
        quality: JPEG quality (1-95 recommended).

    Returns:
        Base64 string of the resulting JPEG (no data URL prefix).
    """

    # Load with Pillow
    img = Image.open(io.BytesIO(bmp_b64))

    if img.mode != 'RGB':
        img = img.convert('RGB')

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)

    return base64.b64encode(buf.getvalue()).decode("utf-8")