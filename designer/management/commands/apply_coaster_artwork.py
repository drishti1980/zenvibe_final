"""Apply 100 editable coaster artworks to the EXISTING 100 database templates.

Uses one master artwork per index for Circle and Square; the gallery preview
shape is merely a mask. Does not generate 200 records or alter other products.
Backup automatically before any changes. Run --dry-run before --apply.
"""
from __future__ import annotations
import copy
import io
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from .coaster_curated_svg import load_curated_artwork, validate_library
from .rebuild_coaster_previews import render

class Command(BaseCommand):
    help = "Update product 415's existing 100 coaster artworks and previews from SVG library."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)
        parser.add_argument("--shape", choices=("circle", "square"), default="circle")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **opts):
        if opts["product_id"] != 415:
            raise CommandError("Only product 415 can be updated.")
        if opts["dry_run"] == opts["apply"]:
            raise CommandError("Choose exactly one of --dry-run or --apply.")
        product = Product.objects.filter(pk=415).first()
        if not product or "coaster" not in product.name.lower():
            raise CommandError("Product 415 must be a coaster.")
        templates = list(DesignTemplate.objects.filter(product_id=415, is_active=True).order_by("id"))
        if len(templates) != 100:
            raise CommandError(f"Expected exactly 100 active templates, found {len(templates)}.")
        validate_library()
        staged = []
        for index, template in enumerate(templates):
            objects = load_curated_artwork(index)
            ids = [obj["id"] for obj in objects]
            if len(ids) != len(set(ids)):
                raise CommandError(f"Duplicate object IDs in design {index + 1}.")
            if not isinstance(template.json_data, dict) or not template.json_data.get("pages"):
                raise CommandError(f"Template {template.pk} has no editable pages.")
            preview = io.BytesIO()
            render(objects, opts["shape"]).save(preview, format="PNG", optimize=True)
            staged.append((template, objects, preview.getvalue()))
        self.stdout.write(f"Validated {len(staged)} artworks for shared circle/square templates.")
        if opts["dry_run"]:
            self.stdout.write("Dry run completed; database and previews unchanged.")
            return
        folder = Path(settings.BASE_DIR) / "coaster_template_backups"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"coasters_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        records = [{"id": t.pk, "product_id": t.product_id, "name": t.name,
                    "json_data": t.json_data, "preview": t.preview.name if t.preview else None,
                    "is_active": t.is_active} for t in templates]
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        if len(json.loads(path.read_text(encoding="utf-8"))) != 100:
            raise CommandError("Backup verification failed.")
        self.stdout.write(f"Verified backup: {path}")
        with transaction.atomic():
            attrs = copy.deepcopy(product.source_attributes or {})
            attrs["Shape"] = ["Circle", "Square"]
            product.source_attributes = attrs
            product.save(update_fields=["source_attributes"])
            for index, (template, objects, png) in enumerate(staged):
                data = copy.deepcopy(template.json_data)
                for key in ("pages", "adminPages"):
                    for page in data.get(key, []):
                        if isinstance(page, dict):
                            page["objects"] = copy.deepcopy(objects)
                data["availableShapes"] = ["Circle", "Square"]
                data["shapeIndependentArtwork"] = True
                data["constrainToPrintArea"] = True
                data["coasterArtworkIndex"] = index
                data["coasterArtworkSource"] = "curated-svg"
                template.json_data = data
                template.preview.save(f"coaster-{template.pk}-{opts['shape']}-curated.png",
                                      ContentFile(png), save=False)
                template.save(update_fields=["json_data", "preview"])
        self.stdout.write(self.style.SUCCESS(
            "Updated 100 existing coaster templates and gallery previews. "
            "Both shapes share each design; refresh the gallery."
        ))
