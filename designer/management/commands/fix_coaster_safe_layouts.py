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


PALETTES = [
    ("#121C2B", "#FFF9EC", "#C6A56C"), ("#163D39", "#F7F5EA", "#C8A96B"),
    ("#321E2D", "#FFF2F1", "#D9A6B5"), ("#182E4B", "#F7FAFF", "#A9C6DD"),
    ("#3B2821", "#FFF6E8", "#D3A172"), ("#F4EEE3", "#243443", "#B3834D"),
    ("#F0F5F0", "#20483D", "#78A99C"), ("#261D3C", "#F9F3FF", "#B6A1D9"),
    ("#F9F0EE", "#4B2939", "#BE8395"), ("#18272B", "#F6F6EE", "#A7C6BB"),
]
THEMES = [
    ("HERITAGE", "EST. 2026"), ("ATELIER", "HANDCRAFTED"),
    ("SIGNATURE", "PREMIUM EDITION"), ("STUDIO", "DESIGNED FOR YOU"),
    ("CLASSIC", "TIMELESS QUALITY"), ("BOUTIQUE", "MADE WITH CARE"),
    ("MONOGRAM", "PERSONAL COLLECTION"), ("MODERN", "SIMPLY DISTINCTIVE"),
    ("PRESTIGE", "THE FINEST DETAILS"), ("ESSENTIAL", "YOUR PERSONAL STYLE"),
]


def primitive(identifier, kind, **properties):
    return dict(id=identifier, name=identifier.replace("_", " ").title(),
                type=kind, scaleX=1, scaleY=1, angle=0, opacity=1,
                customerEditable=True, selectable=True, evented=True,
                **properties)


def safe_artwork(product, index):
    """100 curated editable variations: 10 visual systems x 10 art directions.

    Meaningful objects are within a central circular safe region. Decorative
    motifs occupy a dedicated upper band; text occupies separate lower bands.
    """
    background, ink, gold = PALETTES[(index // 10) % 10]
    theme, subtitle = THEMES[index % 10]
    system = index % 10
    objects = [primitive("background", "rect", left=0, top=0,
                         width=1000, height=1000, fill=background,
                         stroke=None, strokeWidth=0)]

    def ring(name, radius, width=4, color=None, cy=500):
        objects.append(primitive(name, "circle", left=500-radius,
                                 top=cy-radius, radius=radius,
                                 fill="transparent", stroke=color or gold,
                                 strokeWidth=width))

    def bar(name, x, y, w, h=3):
        objects.append(primitive(name, "rect", left=x, top=y, width=w,
                                 height=h, fill=gold, stroke=None, strokeWidth=0))

    def label(name, value, x, y, width, size, color, font="Georgia"):
        objects.append(primitive(name, "textbox", left=x, top=y, width=width,
                                 text=value, fontSize=size, fontFamily=font,
                                 fontWeight="700", textAlign="center",
                                 lineHeight=1.08, fill=color, stroke=None,
                                 strokeWidth=0))

    # Outer accent border stays safely inside the circular cut edge.
    if system in (0, 2, 4, 6, 8):
        ring("fine_border", 334, 4)
    elif system in (1, 5, 9):
        ring("fine_border", 330, 3)
        ring("inner_border", 317, 2, ink)

    # Ten clearly differentiated, non-overlapping emblem arrangements.
    if system == 0:
        ring("crest", 49, 4, cy=355)
        label("crest_letter", "Z", 467, 309, 66, 45, ink)
    elif system == 1:
        bar("ornament_top", 414, 341, 172, 5)
        bar("ornament_bottom", 444, 378, 112, 3)
    elif system == 2:
        ring("seal_outer", 57, 3, cy=355)
        ring("seal_inner", 45, 2, ink, cy=355)
    elif system == 3:
        for n in range(5):
            x=436+n*28
            objects.append(primitive("star_%s" % n, "circle",
                left=x, top=350, radius=7 if n!=2 else 11,
                fill=gold, stroke=None, strokeWidth=0))
    elif system == 4:
        label("emblem", "✦", 465, 320, 70, 58, gold)
    elif system == 5:
        bar("monogram_top", 444, 318, 112, 4)
        label("monogram", "ZV", 440, 337, 120, 43, ink)
    elif system == 6:
        ring("medallion", 51, 4, cy=355)
        label("emblem", "01", 453, 332, 94, 34, ink)
    elif system == 7:
        bar("accent_left", 402, 354, 80, 4)
        bar("accent_right", 518, 354, 80, 4)
        objects.append(primitive("center_dot", "circle",
            left=491, top=347, radius=9, fill=gold,
            stroke=None, strokeWidth=0))
    elif system == 8:
        ring("medallion", 51, 4)
        label("emblem", "A", 470, 324, 60, 48, ink)
    else:
        bar("rule_a", 430, 338, 140, 4)
        bar("rule_b", 450, 358, 100, 3)
        bar("rule_c", 470, 377, 60, 3)

    # Fixed bands and generous whitespace: no collision with ornaments.
    label("brand", "YOUR BRAND", 270, 441, 460, 52, ink)
    label("theme", theme, 330, 524, 340, 24, gold, "Poppins")
    label("subtitle", subtitle, 320, 570, 360, 16, ink, "Poppins")
    bar("footer_accent", 445, 631, 110, 3)
    return objects


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
