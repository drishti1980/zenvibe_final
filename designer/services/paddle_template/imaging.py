"""Image validation, foreground estimation and glyph-mask inpainting."""

import io
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 25_000_000


def normalize_upload(upload):
    if upload.size > MAX_BYTES:
        raise ValueError("Image must be under 15 MB.")
    try:
        im = Image.open(upload)
        if im.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Use a PNG, JPEG or WEBP image.")
        if im.width * im.height > MAX_PIXELS:
            raise ValueError("Image must be under 25 megapixels.")
        im = ImageOps.exif_transpose(im).convert("RGB")
        out = io.BytesIO()
        im.save(out, format="PNG")
        return out.getvalue(), im.width, im.height
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Image cannot be decoded safely.") from exc


def polygon_mask(image, polygon):
    h, w = image.shape[:2]
    poly = np.asarray(polygon, dtype=np.int32)
    full = np.zeros((h, w), np.uint8)
    cv2.fillPoly(full, [poly], 255)
    x, y, bw, bh = cv2.boundingRect(poly)
    x, y = max(0, x), max(0, y)
    bw, bh = min(bw, w - x), min(bh, h - y)
    if bw <= 0 or bh <= 0:
        return full * 0, "#ffffff"
    region = image[y : y + bh, x : x + bw]
    # The median estimates the background; foreground may be light OR dark.
    bg = np.median(region.reshape(-1, 3), axis=0)
    distance = np.linalg.norm(region.astype(float) - bg, axis=2)
    threshold = max(30, float(np.percentile(distance, 60)))
    local = (distance > threshold).astype(np.uint8) * 255
    local &= full[y : y + bh, x : x + bw]
    pixels = region[local > 0]
    color = np.median(pixels, axis=0) if len(pixels) else [255, 255, 255]
    color = "#" + "".join(f"{int(c):02x}" for c in color)
    glyphs = np.zeros_like(full)
    glyphs[y : y + bh, x : x + bw] = local
    glyphs = cv2.dilate(glyphs, np.ones((3, 3), np.uint8), iterations=1)
    return glyphs, color


def repair_background(image, regions, changed_ids):
    changed = set(changed_ids)
    mask = np.zeros(image.shape[:2], np.uint8)
    for region in regions:
        if region["id"] in changed:
            glyphs, _ = polygon_mask(image, region["polygon"])
            mask |= glyphs
    if not mask.any():
        return image.copy()
    # Inpaint only detected glyph pixels; nearby texture and non-text artwork stay.
    return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)


def png_bytes(image):
    out = io.BytesIO()
    Image.fromarray(image).save(out, "PNG")
    return out.getvalue()
