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
                # Replace the previous full-canvas artwork instead of stacking photos.
                # A clipped full-panel photo and editable caption occupy the front-bottom
                # canopy wedge in the 1050x1000 mockup coordinate system.
                # This is a conservative mockup preset, not a supplier dieline.
                existing = list(page.get("objects") or [])
                old_headline = next((str(o.get("text", "")) for o in existing
                    if str(o.get("id", "")).endswith("_headline")), "YOUR BRAND")
                old_subtitle = next((str(o.get("text", "")) for o in existing
                    if str(o.get("id", "")).endswith("_subtitle")), "")
                objects = [{
                    "id": "zv_calendar_replaceable_photo",
                    "name": "Replace Photo — Umbrella Panel",
                    "type": "image", "src": urls[index % len(urls)],
                    "left": 330, "top": 500, "width": 390, "height": 445,
                    "clipPath": {
                        "type": "polygon",
                        "points": [{"x": 525, "y": 500}, {"x": 720, "y": 945}, {"x": 330, "y": 945}],
                        "left": 330, "top": 500, "width": 390, "height": 445,
                        "absolutePositioned": True, "fill": "#000000",
                    },
                    "scaleX": 1, "scaleY": 1, "angle": 0, "opacity": 1,
                    "selectable": True, "evented": True,
                    "customerEditable": True, "replaceable": True,
                }, {
                    "id": "zv_umbrella_panel_headline", "name": "Brand Text",
                    "type": "textbox", "text": old_headline,
                    "left": 430, "top": 775, "width": 190,
                    "fontSize": 21, "fontFamily": "Poppins",
                    "fontWeight": "700", "textAlign": "center",
                    "fill": "#FFFFFF", "selectable": True,
                    "evented": True, "customerEditable": True,
                }]
                if old_subtitle:
                    objects.append({
                        "id": "zv_umbrella_panel_subtitle", "name": "Tagline",
                        "type": "textbox", "text": old_subtitle,
                        "left": 440, "top": 817, "width": 170,
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
