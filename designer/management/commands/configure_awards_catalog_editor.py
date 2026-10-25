from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, ProductPrintArea, ProductPrintSurface

MEDAL_NAME = "Crystal Diamond Cut Sports Medal"

class Command(BaseCommand):
    help = "Make every active canonical Award open as a product-first local editor without inventing physical ruler dimensions."

    def handle(self, *args, **options):
        qs = Product.objects.filter(
            category__name__icontains="award", is_active=True
        ).select_related("category").order_by("id")

        products = []
        for p in qs:
            attrs = p.source_attributes if isinstance(p.source_attributes, dict) else {}
            if attrs.get("source_localized") is True and attrs.get("source_product_id"):
                products.append(p)

        if len(products) != 49:
            raise CommandError(
                f"Expected 49 active localized canonical Awards, found {len(products)}. "
                "Refusing a partial editor configuration."
            )

        configured = 0
        medal = 0
        with transaction.atomic():
            for p in products:
                # The supplied reference video verifies this product as a flat 7 x 9 in
                # full-canvas design. Keep that exact, verified configuration.
                if MEDAL_NAME.lower() in (p.name or "").lower():
                    p.editor_layout_mode = "full_canvas"
                    p.workspace_width_in = Decimal("7.000")
                    p.workspace_height_in = Decimal("9.000")
                    p.print_width_in = Decimal("7.000")
                    p.print_height_in = Decimal("9.000")
                    p.constrain_to_print_area = False
                    p.show_product_reference = False
                    p.save(update_fields=[
                        "editor_layout_mode", "workspace_width_in", "workspace_height_in",
                        "print_width_in", "print_height_in", "constrain_to_print_area",
                        "show_product_reference",
                    ])
                    surface, _ = ProductPrintSurface.objects.update_or_create(
                        product=p, label="Side 1",
                        defaults={
                            "workspace_width_in": Decimal("7.000"),
                            "workspace_height_in": Decimal("9.000"),
                            "print_width_in": Decimal("7.000"),
                            "print_height_in": Decimal("9.000"),
                            "sort_order": 0, "is_active": True,
                        },
                    )
                    ProductPrintArea.objects.update_or_create(
                        product=p, surface=surface, name="Safe zone",
                        defaults={
                            "left": Decimal("4.81"), "top": Decimal("9.80"),
                            "width": Decimal("89.26"), "height": Decimal("80.98"),
                            "print_width_in": Decimal("6.248"),
                            "print_height_in": Decimal("7.288"), "sort_order": 0,
                        },
                    )
                    medal += 1
                    configured += 1
                    continue

                # All other Awards become product-first restricted editors now.
                # We intentionally DO NOT copy the medal's dimensions or invent inches.
                # Their local product image is the locked physical reference and existing
                # product/area geometry is preserved when it already exists.
                p.editor_layout_mode = "print_area"
                p.constrain_to_print_area = True
                p.show_product_reference = True

                # The localised product image is safe as the locked reference until a
                # clean editor-specific reference is uploaded in Admin.
                if not p.editor_reference_image and p.image:
                    p.editor_reference_image.name = p.image.name

                update_fields = [
                    "editor_layout_mode", "constrain_to_print_area",
                    "show_product_reference", "editor_reference_image",
                ]

                # Only promote already-known physical print dimensions to workspace
                # dimensions. Never fabricate measurements.
                if p.workspace_width_in is None and p.print_width_in is not None:
                    p.workspace_width_in = p.print_width_in
                    update_fields.append("workspace_width_in")
                if p.workspace_height_in is None and p.print_height_in is not None:
                    p.workspace_height_in = p.print_height_in
                    update_fields.append("workspace_height_in")

                p.save(update_fields=update_fields)

                # If legacy percentage geometry already exists, materialise it as an
                # Admin print area so the universal guard can enforce it.
                if not p.print_areas.exists():
                    vals = (
                        p.print_left_pct, p.print_top_pct,
                        p.print_width_pct, p.print_height_pct,
                    )
                    if all(v is not None for v in vals):
                        ProductPrintArea.objects.create(
                            product=p, name="Print area",
                            left=p.print_left_pct, top=p.print_top_pct,
                            width=p.print_width_pct, height=p.print_height_pct,
                            print_width_in=p.print_width_in,
                            print_height_in=p.print_height_in,
                            sort_order=0,
                        )
                configured += 1

        self.stdout.write(self.style.SUCCESS(
            f"Awards editor configured: {configured}/49 canonical products. "
            f"Verified 7 x 9 medal profiles: {medal}. "
            "All other Awards now use their LOCAL product image as a locked reference; "
            "existing geometry was preserved and no unverified inch dimensions were invented."
        ))
