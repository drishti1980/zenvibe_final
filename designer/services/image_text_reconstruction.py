"""Optional Python 3.10 image-to-editable-text reconstruction for Zenvibe.

This module is deliberately independent of the current template builder. It can
be called from a background job after an upload, without changing existing
product/editor behavior. Install designer/requirements-template-ocr.txt first.
"""
from __future__ import annotations

import io
import math
import threading
import uuid

from PIL import Image, ImageOps

_reader = None
_reader_lock = threading.Lock()
MAX_PIXELS = 25_000_000


def _reader_instance():
    global _reader
    with _reader_lock:
        if _reader is None:
            try:
                import easyocr
            except ImportError as exc:
                raise RuntimeError(
                    "OCR dependencies missing: pip install -r designer/requirements-template-ocr.txt"
                ) from exc
            _reader = easyocr.Reader(["en"], gpu=False)
        return _reader


def reconstruct_editable_text(uploaded_file, confidence=0.35):
    """Return a cleaned PNG and editable Fabric.js text objects.

    Original text pixels are inpainted only where recognized; complex
    backgrounds, logos, and fonts may need manual correction. No database writes.
    """
    import cv2
    import numpy as np

    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    if image.format not in {"JPEG", "PNG", "WEBP"}:
        raise ValueError("Upload JPG, PNG or WebP.")
    if image.width * image.height > MAX_PIXELS:
        raise ValueError("Image exceeds 25 megapixels.")
    rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"))
    height, width = rgb.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    objects = []
    detections = _reader_instance().readtext(rgb, detail=1, paragraph=False)
    for polygon, text, score in detections:
        if not str(text).strip() or float(score) < confidence:
            continue
        pts = np.asarray(polygon, dtype=np.float32)
        if pts.shape != (4, 2) or not np.isfinite(pts).all():
            continue
        pts[:, 0] = np.clip(pts[:, 0], 0, width - 1)
        pts[:, 1] = np.clip(pts[:, 1], 0, height - 1)
        line_width = float(np.linalg.norm(pts[1] - pts[0]))
        line_height = float(np.linalg.norm(pts[3] - pts[0]))
        if line_width < 2 or line_height < 2:
            continue
        poly = pts.astype(np.int32)
        x, y, bw, bh = cv2.boundingRect(poly)
        x, y = max(x, 0), max(y, 0)
        bw, bh = min(bw, width - x), min(bh, height - y)
        region = rgb[y:y + bh, x:x + bw]
        if region.size == 0:
            continue
        local_poly = np.zeros((bh, bw), dtype=np.uint8)
        cv2.fillPoly(local_poly, [poly - [x, y]], 255)
        bg = np.median(region.reshape(-1, 3), axis=0)
        delta = np.linalg.norm(region.astype(np.float32) - bg, axis=2)
        threshold = max(30.0, float(np.percentile(delta, 60)))
        glyphs = ((delta > threshold) & (local_poly > 0)).astype(np.uint8) * 255
        glyphs = cv2.dilate(glyphs, np.ones((3, 3), np.uint8), iterations=1)
        mask[y:y + bh, x:x + bw] |= glyphs
        ink = region[glyphs > 0]
        color = np.median(ink, axis=0) if len(ink) else [0, 0, 0]
        objects.append({
            "id": "ocr-" + uuid.uuid4().hex,
            "type": "textbox", "text": str(text).strip(),
            "left": float(pts[0, 0]), "top": float(pts[0, 1]),
            "width": line_width, "height": line_height,
            "fontSize": max(7, round(line_height * 0.8)),
            "fontFamily": "Arial", "fontWeight": "normal",
            "fill": "#" + "".join(f"{int(c):02x}" for c in color),
            "angle": math.degrees(math.atan2(
                float(pts[1, 1] - pts[0, 1]),
                float(pts[1, 0] - pts[0, 0]))),
            "editable": True, "selectable": True, "evented": True,
            "customerEditable": True, "ocrConfidence": float(score),
            "ocrPolygon": pts.tolist(),
        })
    cleaned = cv2.inpaint(rgb, mask, 3, cv2.INPAINT_TELEA) if mask.any() else rgb.copy()
    buffer = io.BytesIO()
    Image.fromarray(cleaned).save(buffer, format="PNG")
    return {"width": width, "height": height, "objects": objects,
            "cleaned_background_png": buffer.getvalue()}
