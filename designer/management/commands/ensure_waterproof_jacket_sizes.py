"""Add missing size variants to waterproof jacket products.

Usage: python manage.py ensure_waterproof_jacket_sizes
Existing size records are never modified. Review fallback sizes against supplier
availability before accepting customer orders.
"""
import re

from django.core.management.base import BaseCommand
from designer.models import Product, ProductSizeVariant


class Command(BaseCommand):
    help = "Configure missing size variants for waterproof jackets."

    def handle(self, *args, **options):
        created = 0
        matched = 0
        skipped = 0
        for product in Product.objects.select_related("category__parent").all().iterator():
            category = product.category
            parent = category.parent if category else None
            name = str(product.name or "").lower()
            categories = " ".join(str(getattr(c, "name", "") or "") for c in (category, parent)).lower()
            if not (("waterproof" in name and "jacket" in name) or
                    ("jacket" in name and "waterproof" in categories)):
                continue
            matched += 1
            if product.size_variants.exists():
                skipped += 1
                continue
            attributes = product.source_attributes or {}
            declared = []
            if isinstance(attributes, dict):
                for key, value in attributes.items():
                    if str(key).strip().lower() in ("size", "sizes", "select size", "product size"):
                        if isinstance(value, str):
                            declared = [v.strip() for v in re.split(r"[,|]", value) if v.strip()]
                        elif isinstance(value, (list, tuple)):
                            declared = [str(v).strip() for v in value if str(v).strip()]
                        break
            sizes = declared or ["S", "M", "L", "XL", "2XL", "3XL"]
            for index, name in enumerate(dict.fromkeys(sizes)):
                key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                if not key:
                    continue
                _, new = ProductSizeVariant.objects.get_or_create(
                    product=product, size_key=key,
                    defaults={"name": name, "sort_order": index, "is_active": True},
                )
                created += int(new)
        self.stdout.write(self.style.SUCCESS(
            f"Waterproof jacket products found: {matched}; "
            f"size variants created: {created}; already configured: {skipped}. "
            "Review fallback sizes in Admin before accepting orders."
        ))
