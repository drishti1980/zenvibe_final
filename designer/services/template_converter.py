from __future__ import annotations

import uuid
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image


def _save_uploaded_background(uploaded_file, template_id: int) -> tuple[str, int, int]:
    """Store the uploaded bitmap as the temporary source artwork.

    Template Builder then performs browser-side OCR + visual segmentation and
    replaces this temporary flat source with editable Fabric.js layers.
    """
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    image.load()
    image = image.convert("RGBA")
    width, height = image.size

    from io import BytesIO
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    filename = f"template_backgrounds/template-{template_id}-{uuid.uuid4().hex}.png"
    stored_name = default_storage.save(filename, ContentFile(output.getvalue()))
    return default_storage.url(stored_name), width, height


def convert_uploaded_template(uploaded_file, template_id: int) -> dict[str, Any]:
    """Create the temporary import document used by automatic reconstruction.

    The browser replaces this flat source with editable text and artwork layers
    before the administrator saves the master template.
    """
    background_url, width, height = _save_uploaded_background(uploaded_file, template_id)
    object_id = f"background-{uuid.uuid4().hex}"
    return {
        "version": 4,
        "pages": [{
            "name": "Front",
            "background": "#ffffff",
            "objects": [{
                "id": object_id,
                "objectId": object_id,
                "type": "image",
                "src": background_url,
                "left": 0,
                "top": 0,
                "width": width,
                "height": height,
                "scaleX": 1,
                "scaleY": 1,
                "angle": 0,
                "opacity": 1,
                "backgroundAsset": True,
                "customerEditable": True,
                "locked": False,
                "selectable": True,
                "evented": True,
                "name": "Editable artwork background",
            }],
        }],
        "import": {
            "mode": "auto-reconstruct-pending",
            "source_width": width,
            "source_height": height,
            "message": "Artwork imported and queued for automatic reconstruction into editable Fabric.js layers.",
        },
    }
