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
    """Ten distinct editorial compositions, each with ten themed art directions.

    A 1000px square document is shared across all coaster shapes. Every
    non-background element fits the central 640px square (safe for a round
    coaster); backgrounds bleed to the cut edge.
    """
    import math

    direction = index // 10
    layout = index % 10
    background, ink, accent = PALETTES[direction % len(PALETTES)]
    theme, subtitle = THEMES[direction % len(THEMES)]
    o = []

    def add(name, kind, **props):
        o.append(primitive(name, kind, **props))

    def rect(name, x, y, w, h, color):
        add(name, "rect", left=x, top=y, width=w, height=h,
            fill=color, stroke=None, strokeWidth=0)

    def dot(name, x, y, r, color):
        add(name, "circle", left=x-r, top=y-r, radius=r,
            fill=color, stroke=None, strokeWidth=0)

    def ring(name, x, y, r, color, sw=3):
        add(name, "circle", left=x-r, top=y-r, radius=r,
            fill="transparent", stroke=color, strokeWidth=sw)

    def line(name, x1, y1, x2, y2, color, sw=3):
        add(name, "line", left=min(x1,x2), top=min(y1,y2),
            x1=x1, y1=y1, x2=x2, y2=y2,
            fill=None, stroke=color, strokeWidth=sw)

    def label(name, value, x, y, w, size, color, family="Georgia",
              align="center", weight="700"):
        add(name, "textbox", left=x, top=y, width=w, text=value,
            fontSize=size, fontFamily=family, fontWeight=weight,
            textAlign=align, lineHeight=1.08,
            fill=color, stroke=None, strokeWidth=0)

    rect("background", 0, 0, 1000, 1000, background)
    # Rich but restrained motifs; each layout has its own geometry.
    if layout == 0:  # Heritage seal
        ring("outer_seal",500,500,320,accent,5)
        ring("inner_seal",500,500,306,accent,2)
        label("monogram","ZV",420,310,160,88,accent)
        line("rule",360,437,640,437,accent)
        label("brand","YOUR BRAND",260,463,480,52,ink)
        label("tag",subtitle,315,548,370,19,accent,"Poppins")
    elif layout == 1:  # Modern editorial, offset typographic hierarchy
        rect("left_panel",205,255,12,485,accent)
        label("eyebrow",theme,260,294,460,24,accent,"Poppins","left")
        label("brand","YOUR\\nBRAND",258,378,485,91,ink,"Georgia","left")
        line("rule",265,616,665,616,accent,5)
        label("tag",subtitle,265,649,450,19,ink,"Poppins","left")
    elif layout == 2:  # Botanical sprig with negative space
        for n in range(7):
            y=280+n*55
            line("stem_%s"%n,330,y,360,y+32,accent,3)
            dot("leaf_%s"%n,321 if n%2 else 370,y+12,12,accent)
        label("brand","YOUR BRAND",400,383,355,58,ink,"Georgia","left")
        label("tag",theme,400,475,330,24,accent,"Poppins","left")
        line("rule",402,531,688,531,accent)
        label("detail",subtitle,400,559,330,17,ink,"Poppins","left")
    elif layout == 3:  # Architectural geometry
        rect("arch_left",300,284,9,320,accent)
        rect("arch_right",691,284,9,320,accent)
        line("arch_top",305,284,695,284,accent,5)
        label("brand","YOUR BRAND",318,400,364,54,ink)
        label("tag",theme,350,493,300,25,accent,"Poppins")
        label("detail",subtitle,330,552,340,16,ink,"Poppins")
    elif layout == 4:  # Fine dining hospitality
        label("eyebrow","THE "+theme,340,289,320,22,accent,"Poppins")
        line("rule_top",365,343,635,343,accent,3)
        label("brand","YOUR BRAND",257,396,486,66,ink)
        line("rule_bottom",365,506,635,506,accent,3)
        label("detail",subtitle,330,553,340,20,accent,"Poppins")
        dot("footer",500,623,7,accent)
    elif layout == 5:  # Monogram letterpress
        label("large_initial","Z",318,271,364,180,accent)
        label("brand","YOUR BRAND",310,506,380,50,ink)
        line("rule",403,585,597,585,accent,3)
        label("detail",theme,352,611,296,19,accent,"Poppins")
    elif layout == 6:  # Art deco rays, separated from type
        for n in range(9):
            a=math.pi+(n*math.pi/8)
            x1=500+72*math.cos(a); y1=371+72*math.sin(a)
            x2=500+119*math.cos(a); y2=371+119*math.sin(a)
            line("ray_%s"%n,x1,y1,x2,y2,accent,4)
        dot("sun",500,371,37,accent)
        label("brand","YOUR BRAND",273,483,454,59,ink)
        label("tag",theme,338,578,324,23,accent,"Poppins")
    elif layout == 7:  # Boutique label
        rect("accent_block",304,294,392,86,accent)
        label("eyebrow",theme,324,315,352,36,background,"Poppins")
        label("brand","YOUR BRAND",255,425,490,66,ink)
        label("tag",subtitle,325,540,350,21,accent,"Poppins")
        line("rule",392,606,608,606,accent)
    elif layout == 8:  # Gallery composition
        rect("art_block",304,273,152,152,accent)
        ring("art_cutout",380,349,55,background,10)
        line("art_line",510,296,684,296,accent,4)
        label("eyebrow",theme,509,333,190,23,accent,"Poppins","left")
        label("brand","YOUR BRAND",290,484,420,64,ink)
        label("tag",subtitle,315,576,370,19,accent,"Poppins")
    else:  # Scandinavian minimal
        dot("art_dot",500,328,34,accent)
        line("art_rule",445,389,555,389,accent,4)
        label("brand","YOUR BRAND",270,463,460,62,ink)
        label("tag",theme,360,563,280,22,accent,"Poppins")
        label("detail",subtitle,330,615,340,16,ink,"Poppins")

    # Small thematic details change per art direction without modifying
    # the structure, typography or safe area.
    if direction in (1, 4, 7) and layout in (0, 4, 7, 9):
        dot("signature_dot_left",348,677,5,accent)
        dot("signature_dot_right",652,677,5,accent)
    return o


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
                updated["coasterSafeLayoutVersion"] = 2
                template.json_data = updated
                template.save(update_fields=["json_data"])

        self.stdout.write(self.style.SUCCESS(
            f"Updated {len(templates)} templates; backup: {backup_file}"
        ))
