import base64
import io
from PIL import Image, ImageOps

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