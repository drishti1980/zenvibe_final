from django.core.management.base import BaseCommand
from designer.models import Product, DesignTemplate

SVG_BASE = "/static/designer/notebook_templates/"

TEMPLATES = [
    ("Notebook 001", "notebook-001.svg"),
    ("Notebook 002", "notebook-002.svg"),
    ("Notebook 003", "notebook-003.svg"),
]

class Command(BaseCommand):
    help = "Seed editable SVG notebook templates for the ZenVibe notebook products."

    def handle(self, *args, **options):
        products = Product.objects.filter(name__icontains="notebook")
        if not products.exists():
            self.stderr.write("No notebook products found.")
            return
        for product in products:
            for name, filename in TEMPLATES:
                payload = {
                    "version": 2,
                    "showProductMockup": False,
                    "document": {"width": 1000, "height": 1400},
                    "pages": [{
                        "name": "Notebook Cover",
                        "background": "#ffffff",
                        "objects": [{
                            "id": filename[:-4],
                            "type": "svg",
                            "src": SVG_BASE + filename,
                            "left": 0,
                            "top": 0,
                            "width": 1000,
                            "height": 1400,
                            "customerEditable": True,
                            "selectable": True,
                            "evented": True,
                            "locked": False,
                            "name": name + " editable SVG"
                        }]
                    }]
                }
                DesignTemplate.objects.update_or_create(
                    product=product, name=name,
                    defaults={"json_data": payload, "is_active": True}
                )
            self.stdout.write(self.style.SUCCESS(f"{product.id} — {product.name}: {len(TEMPLATES)} editable SVG templates ready"))
