from django.core.management.base import BaseCommand

from designer.models import Category, DesignTemplate, Product
from designer.seeders.catalog import ensure_pen_catalogue


class Command(BaseCommand):
    help = "Create or repair the default Pen category, products and editor presets."

    def handle(self, *args, **options):
        category, created = ensure_pen_catalogue(Category, Product, DesignTemplate)
        self.stdout.write(self.style.SUCCESS(
            f"Pen catalogue ready: category '{category.name}', "
            f"{category.products.filter(is_active=True, is_out_of_stock=False).count()} active products "
            f"({len(created)} newly created)."
        ))
