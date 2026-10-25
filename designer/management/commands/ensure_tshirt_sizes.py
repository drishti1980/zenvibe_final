"""Populate missing storefront sizes for T-shirt products only.

Run: python manage.py ensure_tshirt_sizes
Existing active/inactive size configurations are never overwritten.
"""
import re

from django.core.management.base import BaseCommand
from designer.models import Product, ProductSizeVariant


class Command(BaseCommand):
    help = "Add standard apparel size options to T-shirts missing size variants."

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for product in Product.objects.select_related("category__parent").all().iterator():
            category = product.category
            parent = category.parent if category else None
            label = " ".join(str(v or "") for v in (
                product.name,
                getattr(category, "name", ""),
                getattr(parent, "name", ""),
            )).lower()
            # Do not assign clothing sizes to hats, bags, or unrelated apparel.
            if not re.search(r"t[ -]?shirts?|tees?\b", label):
                continue
            if product.size_variants.exists():
                skipped += 1
                continue
            raw = product.source_attributes or {}
            declared = []
            if isinstance(raw, dict):
                for key, values in raw.items():
                    if str(key).strip().lower() in ("size", "sizes", "select size", "product size"):
                        if isinstance(values, str):
                            declared = [x.strip() for x in re.split(r"[,|/]", values) if x.strip()]
                        elif isinstance(values, (list, tuple)):
                            declared = [str(x).strip() for x in values if str(x).strip()]
                        break
            # Default range is a starting configuration; review stock/availability in Admin.
            sizes = declared or ["S", "M", "L", "XL", "2XL", "3XL"]
            for index, name in enumerate(dict.fromkeys(sizes)):
                key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                if not key:
                    continue
                _, was_created = ProductSizeVariant.objects.get_or_create(
                    product=product, size_key=key,
                    defaults={"name": name, "sort_order": index, "is_active": True},
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} T-shirt size variants; skipped {skipped} already configured products. "
            "Review sizes and availability in Django Admin."
        ))
