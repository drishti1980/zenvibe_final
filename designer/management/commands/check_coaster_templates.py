"""Diagnose actual coaster template JSON and preview state without modifying data."""
from django.core.management.base import BaseCommand
from designer.models import DesignTemplate, Product

class Command(BaseCommand):
    help="Check saved coaster artwork and previews; does not modify anything."
    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)
        parser.add_argument("--template-id", type=int)
    def handle(self, *args, **opts):
        pid=opts["product_id"]
        p=Product.objects.filter(pk=pid).first()
        if not p:
            self.stderr.write(self.style.ERROR(f"Product {pid} not found"))
            return
        self.stdout.write(f"Product: {p.pk} | {p.name}")
        qs=DesignTemplate.objects.filter(product_id=pid).order_by("id")
        self.stdout.write(f"Templates: {qs.count()} total, {qs.filter(is_active=True).count()} active")
        if opts["template_id"]:
            qs=qs.filter(pk=opts["template_id"])
        else:
            qs=qs.filter(is_active=True)[:5]
        for t in qs:
            data=t.json_data or {}
            pages=data.get("pages") or []
            objects=pages[0].get("objects",[]) if pages else []
            texts=[(o.get("text"),o.get("left"),o.get("top"),o.get("fontSize")) for o in objects if o.get("type") in ("textbox","text","i-text")]
            self.stdout.write(f"ID {t.pk}: {t.name}")
            self.stdout.write(f"  generator={data.get('generator')!r}; objects={len(objects)}; texts={texts[:8]}")
            self.stdout.write(f"  preview_file={t.preview.name if t.preview else 'NONE'}")
            self.stdout.write(f"  preview_url={t.preview.url if t.preview else 'NONE'}")
            self.stdout.write(f"  updated_at={t.updated_at}")
