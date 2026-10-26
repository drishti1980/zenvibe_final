"""Safely restore original coaster template JSON from an existing pre-change backup.

Only affects product 415; no seeding, generated artwork, or migrations.
Use --list-backups, then --backup <path> --dry-run, then --apply --confirm.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate

class Command(BaseCommand):
    help = "Restore saved coaster artwork from a pre-change JSON backup (product 415 only)."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)
        parser.add_argument("--list-backups", action="store_true")
        parser.add_argument("--backup", type=str)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args, **opts):
        if opts["product_id"] != 415:
            raise CommandError("This restoration is deliberately restricted to product 415.")
        folder = Path(settings.BASE_DIR) / "coaster_template_backups"
        if opts["list_backups"]:
            backups = sorted(folder.glob("coasters_*.json")) if folder.exists() else []
            if not backups:
                self.stdout.write("No coaster backup files found. Database left unchanged.")
            for file in backups:
                self.stdout.write(str(file))
            return
        if not opts["backup"]:
            raise CommandError("Pass --backup PATH or --list-backups.")
        if opts["dry_run"] == opts["apply"]:
            raise CommandError("Choose exactly one of --dry-run or --apply.")
        if opts["apply"] and not opts["confirm"]:
            raise CommandError("Restoration requires --confirm.")
        file = Path(opts["backup"]).resolve()
        if not file.is_file() or file.suffix.lower() != ".json":
            raise CommandError("Backup must be an existing JSON file.")
        if file.parent != folder.resolve():
            raise CommandError("Backup must be inside coaster_template_backups.")
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Cannot read backup: {exc}") from exc
        if not isinstance(data, list) or not data:
            raise CommandError("Backup must contain a nonempty list.")
        records = {}
        for item in data:
            if not isinstance(item, dict) or not {"id", "product_id", "json_data"} <= item.keys():
                raise CommandError("Invalid backup record.")
            if item["product_id"] != 415:
                raise CommandError("Backup contains another product. Refusing restore.")
            if item["id"] in records:
                raise CommandError("Backup has duplicate template IDs.")
            if not isinstance(item["json_data"], dict):
                raise CommandError("Invalid template JSON.")
            records[item["id"]] = item
        existing = list(DesignTemplate.objects.filter(product_id=415, id__in=records).order_by("id"))
        if len(existing) != len(records):
            raise CommandError("Backup template IDs do not match current product 415 records.")
        for t in existing:
            if not isinstance(records[t.id]["json_data"].get("pages"), list):
                raise CommandError(f"Backup template {t.id} has no pages array.")
        self.stdout.write(f"Validated {len(existing)} templates from {file.name}.")
        self.stdout.write("NOTE: This restores JSON artwork and names, not image preview files.")
        if opts["dry_run"]:
            self.stdout.write("Dry-run only; database unchanged.")
            return
        with transaction.atomic():
            for t in existing:
                entry = records[t.id]
                t.json_data = copy.deepcopy(entry["json_data"])
                fields = ["json_data"]
                if "name" in entry:
                    t.name = entry["name"]
                    fields.append("name")
                t.save(update_fields=fields)
        self.stdout.write(self.style.SUCCESS(f"Restored {len(existing)} coaster template records from backup."))
