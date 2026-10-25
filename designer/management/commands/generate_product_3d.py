"""Generate free, approximate 2.5D GLB meshes from product photos.

Requires: pip install Pillow numpy trimesh
This is silhouette extrusion, NOT photogrammetry or true image-to-3D reconstruction.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product

log = logging.getLogger(__name__)


def photo_to_glb(image_file, resolution=72, depth=0.13):
    try:
        import numpy as np
        import trimesh
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise CommandError("Install free dependencies: pip install Pillow numpy trimesh") from exc

    image_file.seek(0)
    image = Image.open(image_file).convert("RGBA")
    image = ImageOps.exif_transpose(image)
    image.thumbnail((resolution, resolution), Image.Resampling.LANCZOS)
    rgba = np.asarray(image)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]
    h, w = alpha.shape

    # Transparency is the only reliable automatic silhouette signal.
    # Opaque photos are rectangular slabs; do not pretend to infer their 3D shape.
    visible = alpha > 32
    if not visible.any():
        raise ValueError("Image has no visible pixels")

    vertices, colors, faces = [], [], []
    sx = 2.0 / max(w, h)
    half_depth = float(depth) / 2

    def quad(corners, color):
        base = len(vertices)
        vertices.extend(corners)
        colors.extend([list(map(int, color)) + [255]] * 4)
        faces.extend(((base, base + 1, base + 2), (base, base + 2, base + 3)))

    for y in range(h):
        for x in range(w):
            if not visible[y, x]:
                continue
            x0, x1 = (x - w / 2) * sx, (x + 1 - w / 2) * sx
            y0, y1 = (h / 2 - y - 1) * sx, (h / 2 - y) * sx
            c = rgb[y, x]
            # Front and back
            quad([(x0,y0,half_depth),(x1,y0,half_depth),(x1,y1,half_depth),(x0,y1,half_depth)], c)
            quad([(x1,y0,-half_depth),(x0,y0,-half_depth),(x0,y1,-half_depth),(x1,y1,-half_depth)], c)
            if x == 0 or not visible[y, x-1]:
                quad([(x0,y0,-half_depth),(x0,y0,half_depth),(x0,y1,half_depth),(x0,y1,-half_depth)], c)
            if x == w-1 or not visible[y, x+1]:
                quad([(x1,y0,half_depth),(x1,y0,-half_depth),(x1,y1,-half_depth),(x1,y1,half_depth)], c)
            if y == 0 or not visible[y-1, x]:
                quad([(x0,y1,half_depth),(x1,y1,half_depth),(x1,y1,-half_depth),(x0,y1,-half_depth)], c)
            if y == h-1 or not visible[y+1, x]:
                quad([(x0,y0,-half_depth),(x1,y0,-half_depth),(x1,y0,half_depth),(x0,y0,half_depth)], c)

    mesh = trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=np.float32),
        faces=np.asarray(faces, dtype=np.int64),
        vertex_colors=np.asarray(colors, dtype=np.uint8),
        process=False,
    )
    result = mesh.export(file_type="glb")
    return bytes(result), bool((alpha < 32).any())


class Command(BaseCommand):
    help = "Create free photo-based approximate 3D GLB models and save paths in Product.source_attributes."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--all", action="store_true", help="Process all products with images")
        group.add_argument("--product-id", type=int, help="Process one product")
        parser.add_argument("--replace", action="store_true", help="Regenerate existing models")
        parser.add_argument("--resolution", type=int, default=72, help="Maximum photo grid size (24-128)")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        resolution = options["resolution"]
        if not 24 <= resolution <= 128:
            raise CommandError("--resolution must be between 24 and 128")
        products = Product.objects.all() if options["all"] else Product.objects.filter(pk=options["product_id"])
        total = made = skipped = failed = 0
        for product in products.iterator():
            total += 1
            attrs = dict(product.source_attributes or {})
            if not product.image:
                skipped += 1
                continue
            if attrs.get("generated_3d_model") and not options["replace"]:
                skipped += 1
                continue
            if options["dry_run"]:
                self.stdout.write(f"Would generate: {product.pk} {product.name}")
                continue
            try:
                with product.image.open("rb") as src:
                    glb, transparent = photo_to_glb(src, resolution=resolution)
                path = f"products/generated_3d/product_{product.pk}.glb"
                # Storage may rename existing files, so delete only our known generated path.
                if default_storage.exists(path):
                    default_storage.delete(path)
                saved = default_storage.save(path, ContentFile(glb))
                attrs["generated_3d_model"] = saved
                attrs["generated_3d_method"] = "photo_silhouette_extrusion_v1"
                attrs["generated_3d_approved"] = False
                attrs["generated_3d_has_transparency"] = transparent
                Product.objects.filter(pk=product.pk).update(source_attributes=attrs)
                made += 1
                self.stdout.write(self.style.SUCCESS(f"Generated {product.pk}: {saved}"))
            except Exception as exc:
                failed += 1
                self.stderr.write(f"Failed {product.pk} ({product.name}): {exc}")
                log.exception("3D generation failed for product %s", product.pk)
        self.stdout.write(f"Processed {total}; generated {made}; skipped {skipped}; failed {failed}")
