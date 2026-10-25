from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, ProductPrintArea, ProductPrintSurface


class Command(BaseCommand):
    help = "Apply the verified ZenVibe.ca Awards editor geometry captured in the supplied reference video."

    def handle(self, *args, **options):
        # The supplied video is specifically Crystal Diamond Cut Sports Medal.
        product = Product.objects.filter(
            name__icontains="Crystal Diamond Cut Sports Medal"
        ).order_by("-id").first()
        if not product:
            raise CommandError("Crystal Diamond Cut Sports Medal product was not found.")

        # Verified directly from the supplied ZenVibe.ca editor video:
        # horizontal ruler = 7 in, vertical ruler = 9 in.
        product.editor_layout_mode = "full_canvas"
        product.workspace_width_in = Decimal("7.000")
        product.workspace_height_in = Decimal("9.000")
        product.print_width_in = Decimal("7.000")
        product.print_height_in = Decimal("9.000")
        product.constrain_to_print_area = False
        product.show_product_reference = False
        product.save(update_fields=[
            "editor_layout_mode", "workspace_width_in", "workspace_height_in",
            "print_width_in", "print_height_in", "constrain_to_print_area",
            "show_product_reference",
        ])

        surface, _ = ProductPrintSurface.objects.update_or_create(
            product=product,
            label="Side 1",
            defaults={
                "workspace_width_in": Decimal("7.000"),
                "workspace_height_in": Decimal("9.000"),
                "print_width_in": Decimal("7.000"),
                "print_height_in": Decimal("9.000"),
                "sort_order": 0,
                "is_active": True,
            },
        )

        # Safe-zone rectangle measured from the supplied 1280x720 video frame.
        # Artboard: x=715..985, y=233..580.
        # Green safe zone: x=728..969, y=267..548.
        ProductPrintArea.objects.update_or_create(
            product=product,
            surface=surface,
            name="Safe zone",
            defaults={
                "left": Decimal("4.81"),
                "top": Decimal("9.80"),
                "width": Decimal("89.26"),
                "height": Decimal("80.98"),
                "print_width_in": Decimal("6.248"),
                "print_height_in": Decimal("7.288"),
                "sort_order": 0,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"{product.id} — {product.name}: verified video geometry applied | "
            "Side 1 = 7 × 9 in | full-canvas artwork | safe zone = "
            "4.81%/9.80%/89.26%/80.98% | no locked product mockup"
        ))
