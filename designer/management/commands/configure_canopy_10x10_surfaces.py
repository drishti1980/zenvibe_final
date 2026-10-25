from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, ProductPrintSurface

class Command(BaseCommand):
    help = "Configure the Admin-managed 10x10 canopy print surfaces."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=391)
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **opts):
        product_id = opts["product_id"]
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise CommandError(f"Product {product_id} does not exist.")

        surfaces = [
            ("Canopy Top", 120, 120),
            ("Full Back Wall - Outside", 117, 80),
            ("Full Back Wall - Inside", 117, 80),
            ("Left Half Wall - Outside", 117, 38),
            ("Left Half Wall - Inside", 117, 38),
            ("Right Half Wall - Outside", 117, 38),
            ("Right Half Wall - Inside", 117, 38),
        ]

        if opts["replace"]:
            product.print_surfaces.all().delete()

        for order, (label, width, height) in enumerate(surfaces, start=1):
            obj, created = ProductPrintSurface.objects.update_or_create(
                product=product,
                label=label,
                defaults={
                    "print_width_in": width,
                    "print_height_in": height,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            self.stdout.write(
                f"{'Created' if created else 'Updated'}: "
                f"{order}. {label} — {width} x {height} in"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Configured {len(surfaces)} Admin print surfaces for product {product.id}: {product.name}"
        ))
