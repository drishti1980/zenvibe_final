from __future__ import annotations

"""Opt-in, backed-up repair for generated coaster template artwork.

Never runs during migrations, deployments, or imports. Use --dry-run first.
Existing template IDs, print rulers, product photos, and non-generated designs
are preserved. Artwork is deliberately rebuilt only on explicit --apply.
"""
import copy
import io
import json
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageChops, ImageStat
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.files.base import ContentFile
from designer.models import DesignTemplate


from .zenvibe_coaster_luxury_v5 import safe_artwork, NAMES
from .rebuild_coaster_previews import render


class Command(BaseCommand):
    help = "Preview or repair generated coaster layouts with a JSON backup."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--preview-shape", choices=("circle", "square"), default="circle")
        parser.add_argument("--contact-sheet", action="store_true", help="Save a 10x10 visual review sheet")
        parser.add_argument("--confirm-replace-artwork", action="store_true",
                            help="Required to replace generated template artwork")

    def handle(self, *args, **options):
        if options["apply"] == options["dry_run"]:
            raise CommandError("Specify exactly one of --dry-run or --apply")

        # Generator versions differ: existing coaster records use
        # zenvibe-promotional-luxury-v26 rather than the seed constant.
        # Match known generated coaster records without including manual designs.
        qs = DesignTemplate.objects.select_related("product").filter(
            product__name__icontains="coaster", is_active=True,
            json_data__generator__startswith="zenvibe-promotional-",
        ).order_by("product_id", "id")
        if options["product_id"]:
            qs = qs.filter(product_id=options["product_id"])
        if options["apply"] and not options["product_id"]:
            raise CommandError("--apply requires --product-id to limit the change.")
        if options["apply"] and not options["confirm_replace_artwork"]:
            raise CommandError(
                "This operation replaces generated artwork. Review --dry-run, then "
                "pass --confirm-replace-artwork to proceed."
            )
        templates = list(qs)
        if not templates:
            raise CommandError("No matching generated coaster templates found.")

        self.stdout.write(f"Matched {len(templates)} generated coaster templates.")
        # Render and validate the actual artwork for every template BEFORE
        # modifying any database row. This catches generator exceptions even
        # in dry-run mode and avoids stale gallery preview files.
        staged = []
        counters = {}
        for template in templates:
            idx = counters.get(template.product_id, 0)
            counters[template.product_id] = idx + 1
            try:
                objects = safe_artwork(template.product, idx)
                if not isinstance(objects, list) or not objects:
                    raise ValueError("empty artwork")
                object_ids = [obj.get("id") for obj in objects]
                if len(set(object_ids)) != len(object_ids):
                    raise ValueError("duplicate object IDs")
                image = render(objects, options["preview_shape"])
                buffer = io.BytesIO()
                image.save(buffer, format="PNG", optimize=True)
                staged.append((template, objects, buffer.getvalue()))
            except Exception as exc:
                raise CommandError(
                    f"Template {template.id} failed artwork/preview validation: {exc}"
                ) from exc

        hashes = [hashlib.sha256(png).hexdigest() for _, _, png in staged]
        if len(hashes) != len(set(hashes)):
            raise CommandError("Duplicate rendered coaster previews detected; no database changes.")
        # Fail closed on near-identical layouts. Byte hashes alone only detect
        # exact copies; a recoloured duplicate still has different PNG bytes.
        # Compare structural edge maps so palette changes do not hide repeats.
        def silhouette(png):
            im = Image.open(io.BytesIO(png)).convert("L").resize((48, 48))
            # Edge structure is robust to recolouring and ignores flat backgrounds.
            from PIL import ImageFilter
            im = im.filter(ImageFilter.FIND_EDGES)
            return [1 if p > 38 else 0 for p in im.getdata()]
        signatures = [silhouette(png) for _, _, png in staged]
        near_duplicates = []
        for a in range(len(signatures)):
            for b in range(a + 1, len(signatures)):
                difference = sum(x != y for x, y in zip(signatures[a], signatures[b]))
                if difference < 30:
                    near_duplicates.append((a + 1, b + 1, difference))
        if near_duplicates:
            self.stdout.write(self.style.WARNING(
                f"Found {len(near_duplicates)} near-identical edge compositions. "
                f"Examples: {near_duplicates[:12]}. These need redesigned artwork."
            ))
            if options["apply"]:
                raise CommandError(
                    "Refusing to publish visually repetitive coaster artwork. "
                    "Redesign the flagged compositions and rerun --dry-run."
                )
        if options["contact_sheet"]:
            sheet = Image.new("RGB", (1200, 1400), "#f3f4f6")
            painter = ImageDraw.Draw(sheet)
            for j, (template, artwork, png) in enumerate(staged[:100]):
                thumb = Image.open(io.BytesIO(png)).convert("RGB")
                thumb.thumbnail((112, 112))
                x = (j % 10) * 120 + 4
                y = (j // 10) * 140 + 4
                sheet.paste(thumb, (x, y))
                painter.text((x + 5, y + 114), f"{j+1:03d}", fill="#111827")
            # Windows can reject overwriting a PNG currently open in an image
            # viewer (Errno 22/permission errors). Never reuse the same filename.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            sheet_path = Path(settings.BASE_DIR) / f"coaster_luxury_100_contact_sheet_{timestamp}.png"
            try:
                sheet.save(str(sheet_path), format="PNG")
            except OSError as exc:
                # Preview creation must not crash validation when the project
                # directory is locked or non-writable.
                fallback = Path(tempfile.gettempdir()) / f"zenvibe_coaster_contact_sheet_{timestamp}.png"
                try:
                    sheet.save(str(fallback), format="PNG")
                    sheet_path = fallback
                    self.stdout.write(self.style.WARNING(
                        f"Project directory preview save failed ({exc}); saved to temporary directory instead."
                    ))
                except OSError as fallback_exc:
                    raise CommandError(
                        f"Unable to save contact sheet to project or temp folder: {fallback_exc}"
                    ) from fallback_exc
            self.stdout.write(f"Visual review sheet: {sheet_path}")
        if options["dry_run"]:
            for template, objects, png in staged[:10]:
                self.stdout.write(
                    f"Validated {template.id}: {template.name} "
                    f"({len(objects)} editable objects, {len(png)} PNG bytes)"
                )
            self.stdout.write(
                f"Dry run complete: validated {len(staged)} templates; "
                "database and media unchanged."
            )
            return

        backup_dir = Path(settings.BASE_DIR) / "coaster_template_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = backup_dir / (
            "coasters_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json"
        )
        backup_file.write_text(json.dumps([
            {"id": t.id, "product_id": t.product_id,
             "name": t.name, "json_data": t.json_data}
            for t in templates
        ], indent=2, default=str), encoding="utf-8")
        self.stdout.write(f"Backup written: {backup_file}")

        with transaction.atomic():
            for template, artwork, preview_bytes in staged:
                updated = copy.deepcopy(template.json_data)
                for key in ("pages", "adminPages"):
                    for page in updated.get(key, []):
                        if isinstance(page, dict):
                            page["objects"] = copy.deepcopy(artwork)
                updated["coasterSafeLayoutVersion"] = 6
                updated["coasterArtworkGenerator"] = "luxury-v6-vector"
                updated["coasterArtworkIndex"] = next(i for i, item in enumerate(staged) if item[0].pk == template.pk)
                template.json_data = updated
                art_idx = updated['coasterArtworkIndex']
                template.name = f'{art_idx + 1:03d} — {NAMES[art_idx % 10]} — Original Artwork'
                filename = (
                    f"coaster-{template.id}-{options['preview_shape']}-luxury-v6.png"
                )
                template.preview.save(
                    filename, ContentFile(preview_bytes), save=False
                )
                template.save(update_fields=["json_data", "preview", "name"])

        self.stdout.write(self.style.SUCCESS(
            f"Updated {len(templates)} templates and gallery names/previews; backup: {backup_file}. "
            "Refresh the gallery and confirm the first card name has changed."
        ))
