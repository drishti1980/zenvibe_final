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
    help = "Add calendar photographs as replaceable layers to existing umbrella templates."

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
                objects = [
                    obj for obj in page.get("objects", [])
                    if obj.get("id") != "zv_calendar_replaceable_photo"
                ]
                # Place the image on the top printable canopy, avoiding the
                # existing editable brand text near the lower panel.
                # Insertion before brand objects ensures headline stays legible.
                photo = {
                    "id": "zv_calendar_replaceable_photo",
                    "name": "Replace Photo — Calendar Artwork",
                    "type": "image",
                    "src": urls[index % len(urls)],
                    "left": 275, "top": 175, "width": 500, "height": 420,
                    "scaleX": 1, "scaleY": 1, "angle": 0, "opacity": 1,
                    "selectable": True, "evented": True,
                    "customerEditable": True, "replaceable": True,
                }
                insert_at = next(
                    (i for i, obj in enumerate(objects)
                     if obj.get("type") in ("textbox", "text")),
                    len(objects),
                )
                objects.insert(insert_at, photo)
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
