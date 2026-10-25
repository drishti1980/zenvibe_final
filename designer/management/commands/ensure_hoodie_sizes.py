"""Populate missing hoodie size variants without modifying existing configurations.

Run: python manage.py ensure_hoodie_sizes
Review any fallback sizes against actual supplier availability before taking orders.
"""
import re

from django.core.management.base import BaseCommand
from designer.models import Product, ProductSizeVariant


class Command(BaseCommand):
    help = "Add size options to hoodie products with no existing size configuration."

    def handle(self, *args, **options):
        matched = created = skipped = 0
        for product in Product.objects.select_related("category__parent").all().iterator():
            category = product.category
            parent = category.parent if category else None
            name = str(product.name or "").lower()
            category_names = " ".join(
                str(getattr(c, "name", "") or "") for c in (category, parent)
            ).lower()
            if not (re.search(r"\bhood(?:ie|ies|ed sweatshirts?)\b", name)
                    or ("hoodie" in category_names and
                        re.search(r"hood|sweatshirt", name))):
                continue
            matched += 1
            if product.size_variants.exists():
                skipped += 1
                continue
            raw = product.source_attributes or {}
            declared = []
            if isinstance(raw, dict):
                for key, values in raw.items():
                    if str(key).strip().lower() in ("size", "sizes", "select size", "product size"):
                        if isinstance(values, str):
                            declared = [x.strip() for x in re.split(r"[,|]", values) if x.strip()]
                        elif isinstance(values, (list, tuple)):
                            declared = [str(x).strip() for x in values if str(x).strip()]
                        break
            sizes = declared or ["S", "M", "L", "XL", "2XL", "3XL"]
            for order, name in enumerate(dict.fromkeys(sizes)):
                key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                if not key:
                    continue
                _, was_created = ProductSizeVariant.objects.get_or_create(
                    product=product, size_key=key,
                    defaults={"name": name, "sort_order": order, "is_active": True},
                )
                created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Hoodie products found: {matched}; variants created: {created}; "
            f"already configured: {skipped}. Verify fallback sizes in Admin."
        ))
