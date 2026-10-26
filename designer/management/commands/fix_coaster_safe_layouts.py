from __future__ import annotations

"""Opt-in, backed-up repair for generated coaster template artwork.

Never runs during migrations, deployments, or imports. Use --dry-run first.
Existing template IDs, print rulers, product photos, and non-generated designs
are preserved. Artwork is deliberately rebuilt only on explicit --apply.
"""
import copy
import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate
from designer.management.commands.seed_promotional_product_templates import build_coaster


def safe_artwork(product, index):
    """Generate editable artwork, safely contained in both square and circle."""
    width, height, objects = build_coaster(product, index)
    if width != 1000 or height != 1000:
        raise CommandError("Unexpected coaster canvas dimensions")

    # Retain the generator's distinctive artwork, but uniformly scale it
    # into the inscribed circular-safe square. The background is rebuilt
    # separately to cover the full print area.
    background = next((o for o in objects if o.get("id") == "background"), None)
    fill = background.get("fill", "#FFFFFF") if background else "#FFFFFF"
    foreground = [copy.deepcopy(o) for o in objects if o.get("id") != "background"]

    # Keep entire source composition within the central 600x600 square,
    # whose furthest corner is only 424px from the circle centre.
    scale = 0.60
    offset = 200
    for obj in foreground:
        for coord in ("left", "top", "x1", "x2", "y1", "y2"):
            if isinstance(obj.get(coord), (int, float)):
                obj[coord] = offset + obj[coord] * scale
        for dim in ("width", "height", "radius", "rx", "ry", "strokeWidth", "fontSize"):
            if isinstance(obj.get(dim), (int, float)):
                obj[dim] *= scale

    return [{
        "id": "background", "name": "Background", "type": "rect",
        "left": 0, "top": 0, "width": 1000, "height": 1000,
        "fill": fill, "stroke": None, "strokeWidth": 0,
        "scaleX": 1, "scaleY": 1, "angle": 0, "opacity": 1,
        "customerEditable": True, "selectable": True, "evented": True,
    }] + foreground


class Command(BaseCommand):
    help = "Preview or repair generated coaster layouts with a JSON backup."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
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
        if options["dry_run"]:
            for template in templates[:10]:
                self.stdout.write(f"Would update {template.id}: {template.name}")
            self.stdout.write("Dry run complete; nothing changed.")
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

        counters = {}
        with transaction.atomic():
            for template in templates:
                idx = counters.get(template.product_id, 0)
                counters[template.product_id] = idx + 1
                updated = copy.deepcopy(template.json_data)
                artwork = safe_artwork(template.product, idx)
                for key in ("pages", "adminPages"):
                    for page in updated.get(key, []):
                        if isinstance(page, dict):
                            page["objects"] = copy.deepcopy(artwork)
                updated["coasterSafeLayoutVersion"] = 1
                template.json_data = updated
                template.save(update_fields=["json_data"])

        self.stdout.write(self.style.SUCCESS(
            f"Updated {len(templates)} templates; backup: {backup_file}"
        ))
