"""Correct the known canopy minimum without changing other products' admin rules."""
from django.core.management.base import BaseCommand
from designer.models import Product


class Command(BaseCommand):
    help = "Set the confirmed single-unit minimum for the 10x10 canopy (product 391)."

    def handle(self, *args, **kwargs):
        product = Product.objects.filter(pk=391).first()
        if not product:
            self.stdout.write(self.style.WARNING("Product 391 not found; nothing changed."))
            return
        name = product.name.lower()
        if "canopy" not in name or "10" not in name:
            self.stdout.write(self.style.ERROR("Product 391 is not the expected 10x10 canopy; nothing changed."))
            return
        if product.minimum_quantity != 1:
            previous = product.minimum_quantity
            product.minimum_quantity = 1
            product.save(update_fields=["minimum_quantity"])
            self.stdout.write(self.style.SUCCESS(f"Updated {product.name}: minimum {previous} -> 1"))
        else:
            self.stdout.write(self.style.SUCCESS("Canopy minimum already 1."))
