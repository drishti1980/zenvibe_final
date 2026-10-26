"""UTF-8-safe backup of product 415 coaster templates, including preview references."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from designer.models import DesignTemplate

class Command(BaseCommand):
    help = "Backup coaster product 415 without Windows console encoding issues."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)

    def handle(self, *args, **opts):
        product_id = opts["product_id"]
        if product_id != 415:
            raise CommandError("This backup command is restricted to product 415.")
        records = list(DesignTemplate.objects.filter(product_id=product_id).order_by("id"))
        if not records:
            raise CommandError("No templates found for product 415.")
        folder = Path(settings.BASE_DIR) / "coaster_template_backups"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"coasters_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        data = [
            {"id": t.pk, "product_id": t.product_id, "name": t.name,
             "json_data": t.json_data, "preview": t.preview.name if t.preview else None,
             "is_active": t.is_active}
            for t in records
        ]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        check = json.loads(path.read_text(encoding="utf-8"))
        if len(check) != len(records):
            raise CommandError("Backup verification failed.")
        self.stdout.write(self.style.SUCCESS(f"Backed up {len(records)} coaster templates to {path}"))
