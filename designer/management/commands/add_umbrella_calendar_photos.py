"""Add replaceable calendar photographs to existing umbrella templates.

Uses real, local calendar template photographs. No API, paid library or
minimum of 100 photographs required. Does not alter umbrella colours.

    python manage.py add_umbrella_calendar_photos --apply
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product
from designer.management.commands.build_umbrella_photo_library import (
    walk_images, resolve_media_url, usable, fingerprint,
)

class Command(BaseCommand):
    help = "Replace overlapping umbrella artwork with a single editable photo and caption."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=205)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        photos = {}
        for template in DesignTemplate.objects.filter(
            product__name__icontains="calendar"
        ).iterator():
            for src in walk_images(template.json_data):
                path = resolve_media_url(src, media_root, settings.MEDIA_URL)
                if path and usable(path):
                    try:
                        photos.setdefault(fingerprint(path), path)
                    except (OSError, ValueError):
                        pass
        paths = list(photos.values())
        if not paths:
            raise CommandError(
                "No local calendar photographs found. Existing umbrella templates unchanged."
            )
        qs = DesignTemplate.objects.filter(
            product_id=options["product_id"], is_active=True
        ).order_by("pk")
        count = qs.count()
        if not count:
            raise CommandError("No active umbrella templates found.")
        self.stdout.write(
            f"Found {len(paths)} distinct calendar photos for {count} umbrella templates."
        )
        if not options["apply"]:
            self.stdout.write("Preview only. Use --apply to add replaceable photos.")
            return
        urls = []
        for path in paths:
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            key = f"zenvibe/umbrella-calendar-photos/{digest[:24]}{path.suffix.lower()}"
            if not default_storage.exists(key):
                default_storage.save(key, ContentFile(data))
            urls.append(default_storage.url(key))
        changed = 0
        with transaction.atomic():
            for index, template in enumerate(qs.select_for_update()):
                payload = dict(template.json_data or {})
                pages = list(payload.get("pages") or [])
                if not pages:
                    continue
                page = dict(pages[0])
                # Ten different panel arrangements; image clipping is expressed
                # in Fabric's local polygon coordinates with absolutePositioned.
                # The product mockup is 1050 x 1000. These are visual templates,
                # not manufacturer-certified cutting/bleed artwork.
                existing = list(page.get("objects") or [])
                old_headline = next((str(o.get("text", "")) for o in existing
                    if str(o.get("id", "")).endswith("_headline")), "YOUR BRAND")
                old_subtitle = next((str(o.get("text", "")) for o in existing
                    if str(o.get("id", "")).endswith("_subtitle")), "")
                hub = (525, 500)
                rim = [(525,55),(842,178),(1000,445),(946,742),
                       (720,945),(330,945),(104,742),(50,445),(208,178)]
                # Eight physical canopy sectors, numbered clockwise.
                sectors = [(hub, rim[i], rim[i+1]) for i in range(8)]
                layouts = [
                    [4], [0,4], [2,6], [1,5], [3,7], [4,5],
                    [0,2,4,6], [1,3,5,7], [2,3,4], list(range(8)),
                ]
                chosen = layouts[index % len(layouts)]
                objects = []
                for n, sector_index in enumerate(chosen):
                    tri = sectors[sector_index]
                    min_x = min(pt[0] for pt in tri)
                    min_y = min(pt[1] for pt in tri)
                    max_x = max(pt[0] for pt in tri)
                    max_y = max(pt[1] for pt in tri)
                    width, height = max_x-min_x, max_y-min_y
                    # Polygon points are LOCAL to its bounding box. In Fabric,
                    # left/top are absolute canvas coordinates when absolutePositioned.
                    polygon = {
                        "type": "polygon",
                        "points": [{"x": x-min_x, "y": y-min_y} for x,y in tri],
                        "left": min_x, "top": min_y,
                        "width": width, "height": height,
                        "originX": "left", "originY": "top",
                        "absolutePositioned": True,
                        "fill": "#000000",
                    }
                    objects.append({
                        "id": f"zv_calendar_photo_{sector_index}",
                        "name": f"Replace Photo — Panel {sector_index+1}",
                        "type": "image",
                        "src": urls[(index+n) % len(urls)],
                        "left": min_x, "top": min_y,
                        "width": width, "height": height,
                        "scaleX": 1, "scaleY": 1,
                        "angle": 0, "opacity": 1,
                        "clipPath": polygon,
                        "selectable": True, "evented": True,
                        "customerEditable": True, "replaceable": True,
                    })
                # Keep branding separate and editable. Different placements
                # correspond to different print layouts, not just new photos.
                placements = [(410,785,230),(410,785,230),(410,785,230),
                              (410,785,230),(410,785,230),(390,795,270),
                              (395,790,260),(390,795,270),(410,790,230),
                              (405,785,240)]
                tx,ty,tw = placements[index % len(placements)]
                objects.append({
                    "id": "zv_umbrella_panel_headline", "name": "Brand Text",
                    "type": "textbox", "text": old_headline,
                    "left": tx, "top": ty, "width": tw,
                    "fontSize": 21, "fontFamily": "Poppins",
                    "fontWeight": "700", "textAlign": "center",
                    "fill": "#FFFFFF", "selectable": True,
                    "evented": True, "customerEditable": True,
                })
                if old_subtitle:
                    objects.append({
                        "id": "zv_umbrella_panel_subtitle", "name": "Tagline",
                        "type": "textbox", "text": old_subtitle,
                        "left": tx+10, "top": ty+39, "width": tw-20,
                        "fontSize": 13, "fontFamily": "Poppins",
                        "fontWeight": "600", "textAlign": "center",
                        "fill": "#FFFFFF", "selectable": True,
                        "evented": True, "customerEditable": True,
                    })
                page["objects"] = objects
                pages[0] = page
                payload["pages"] = pages
                # Keep admin and customer editor in sync.
                payload["adminPages"] = [dict(p) for p in pages]
                template.json_data = payload
                template.save(update_fields=["json_data"])
                changed += 1
        self.stdout.write(self.style.SUCCESS(
            f"Added editable, replaceable default photographs to {changed} umbrella templates."
        ))
        if len(paths) < count:
            self.stdout.write(
                f"Note: {len(paths)} photographs are reused across {count} templates; "
                "this does not make every design composition unique."
            )
