"""PaddleOCR 3.x adapter. No remote paid OCR API or silent fallback."""

import json
import math
import os
import threading
import uuid
import numpy as np
from .imaging import polygon_mask

_engine = None
_lock = threading.Lock()


def normalize_result(payload, image):
    if isinstance(payload, str):
        payload = json.loads(payload)
    result = payload.get("res", payload)
    texts = result.get("rec_texts", [])
    scores = result.get("rec_scores", [])
    polygons = result.get("rec_polys")
    if polygons is None:
        polygons = result.get("dt_polys", [])
    regions = []
    for text, score, polygon in zip(texts, scores, polygons):
        if not str(text).strip() or float(score) < 0.35:
            continue
        pts = np.asarray(polygon, dtype=float)
        if pts.shape != (4, 2) or not np.isfinite(pts).all():
            continue
        pts[:, 0] = np.clip(pts[:, 0], 0, image.shape[1] - 1)
        pts[:, 1] = np.clip(pts[:, 1], 0, image.shape[0] - 1)
        width = float(np.linalg.norm(pts[1] - pts[0]))
        height = float(np.linalg.norm(pts[3] - pts[0]))
        if width < 2 or height < 2:
            continue
        _, color = polygon_mask(image, pts.tolist())
        regions.append(
            {
                "id": str(uuid.uuid4()),
                "text": str(text).strip(),
                "confidence": round(float(score), 4),
                "polygon": pts.tolist(),
                "x": float(pts[0, 0]),
                "y": float(pts[0, 1]),
                "width": width,
                "height": height,
                "angle": math.degrees(
                    math.atan2(pts[1, 1] - pts[0, 1], pts[1, 0] - pts[0, 0])
                ),
                "color": color,
            }
        )
    return regions


def extract(image):
    global _engine
    # One CPU engine per process, serialized to avoid concurrent predictor access.
    with _lock:
        if _engine is None:
            try:
                from paddleocr import PaddleOCR
            except ImportError as exc:
                raise RuntimeError(
                    "Install requirements-ocr.txt to enable PaddleOCR."
                ) from exc
            options = dict(
                lang="en",
                device="cpu",
                cpu_threads=1,
                enable_mkldnn=False,
                ocr_version="PP-OCRv5",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            for name in ("text_detection_model_dir", "text_recognition_model_dir"):
                value = os.getenv(name.upper())
                if value:
                    options[name] = value
            _engine = PaddleOCR(**options)
        results = list(_engine.predict(image[:, :, ::-1].copy()))
        if not results:
            return []
        result = results[0]
        payload = result.json
        if callable(payload):
            payload = payload()
        return normalize_result(payload, image)
