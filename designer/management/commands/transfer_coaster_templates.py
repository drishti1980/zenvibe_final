"""Transfer real editable coaster DesignTemplate records between Zenvibe databases.

Run export in original Zenvibe, import in zenvibe_final. No fabricated designs.
"""
import json
import zipfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product


class Command(BaseCommand):
    help = "Export/import coaster templates and preview images as a ZIP."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["export", "inspect", "import"])
        parser.add_argument("--product-id", type=int, required=False)
        parser.add_argument("--file", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--replace-existing", action="store_true")

    def handle(self, *args, **options):
        action = options["action"]
        path = Path(options["file"])
        product_id = options["product_id"]
        if action == "export":
            if not product_id:
                raise CommandError("Export requires --product-id")
            if not Product.objects.filter(pk=product_id).exists():
                raise CommandError(f"Product {product_id} does not exist")
            records = list(DesignTemplate.objects.filter(product_id=product_id, is_active=True).order_by("pk"))
            if not records:
                raise CommandError("No active coaster templates found in the SOURCE database. No export created.")
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = []
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for index, template in enumerate(records):
                    preview_name = None
                    if template.preview:
                        try:
                            with template.preview.open("rb") as stream:
                                image = stream.read()
                            preview_name = f"previews/{index:04d}-{template.pk}{Path(template.preview.name).suffix.lower() or '.png'}"
                            archive.writestr(preview_name, image)
                        except (OSError, IOError, ValueError) as exc:
                            self.stderr.write(f"Preview unavailable for template {template.pk}: {exc}")
                    payload.append({"source_id": template.pk, "name": template.name,
                                    "json_data": template.json_data, "preview": preview_name})
                archive.writestr("templates.json", json.dumps({"format": "zenvibe-coaster-transfer-v1",
                    "source_product_id": product_id, "templates": payload}, ensure_ascii=False, indent=2))
            self.stdout.write(self.style.SUCCESS(f"Exported {len(records)} real coaster templates to {path}"))
            return

        if not path.is_file():
            raise CommandError(f"ZIP not found: {path}")
        with zipfile.ZipFile(path) as archive:
            try:
                payload = json.loads(archive.read("templates.json"))
            except (KeyError, ValueError, UnicodeDecodeError) as exc:
                raise CommandError(f"Invalid coaster transfer archive: {exc}") from exc
            if payload.get("format") != "zenvibe-coaster-transfer-v1":
                raise CommandError("Unrecognised transfer archive format")
            records = payload.get("templates", [])
            if not records:
                raise CommandError("Archive contains no templates")
            for record in records:
                data = record.get("json_data")
                if not isinstance(data, dict) or not data.get("pages"):
                    raise CommandError(f"Template {record.get('source_id')} has no editable pages")
                preview = record.get("preview")
                if preview and preview not in archive.namelist():
                    raise CommandError(f"Missing preview file: {preview}")
            self.stdout.write(f"Archive: {len(records)} templates from source product {payload['source_product_id']}")
            if action == "inspect":
                for record in records[:10]:
                    self.stdout.write(f"  {record['source_id']}: {record['name']}")
                return
            if not product_id or not Product.objects.filter(pk=product_id).exists():
                raise CommandError("Import requires an existing target --product-id")
            existing = list(DesignTemplate.objects.filter(product_id=product_id, is_active=True).order_by("pk"))
            replacing = options["replace_existing"]
            if replacing and len(existing) != len(records):
                raise CommandError(f"Replacement requires same count: target={len(existing)}, source={len(records)}")
            self.stdout.write(f"Target product {product_id}: {len(existing)} active templates")
            self.stdout.write("Mode: replace existing IDs" if replacing else "Mode: create new templates (keep existing untouched)")
            if not options["apply"]:
                self.stdout.write(self.style.WARNING("Dry run only. Add --apply to import."))
                return
            previews = [archive.read(record["preview"]) if record.get("preview") else None for record in records]
            with transaction.atomic():
                for index, (record, preview_bytes) in enumerate(zip(records, previews)):
                    if replacing:
                        template = existing[index]
                        template.name = record["name"][:140]
                        template.json_data = record["json_data"]
                    else:
                        template = DesignTemplate(product_id=product_id, name=record["name"][:140],
                                                  json_data=record["json_data"], is_active=True)
                    if preview_bytes:
                        suffix = Path(record["preview"]).suffix.lower()
                        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                            raise CommandError(f"Unsupported preview extension: {suffix}")
                        template.preview.save(f"coaster-import-{product_id}-{index + 1:03d}{suffix}",
                                              ContentFile(preview_bytes), save=False)
                    template.save()
            self.stdout.write(self.style.SUCCESS(f"Imported {len(records)} coaster templates into product {product_id}"))
