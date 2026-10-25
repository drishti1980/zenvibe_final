from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, ProductPrintArea, ProductPrintSurface

class Command(BaseCommand):
    help = "Configure an Award product for the universal inch-ruler + locked-reference + restricted-print-area editor."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument("--workspace-width", type=Decimal, required=True, help="Outer editor/ruler width in inches.")
        parser.add_argument("--workspace-height", type=Decimal, required=True, help="Outer editor/ruler height in inches.")
        parser.add_argument("--left", type=Decimal, required=True, help="Print-area left position as percentage of workspace.")
        parser.add_argument("--top", type=Decimal, required=True, help="Print-area top position as percentage of workspace.")
        parser.add_argument("--width", type=Decimal, required=True, help="Print-area width as percentage of workspace.")
        parser.add_argument("--height", type=Decimal, required=True, help="Print-area height as percentage of workspace.")
        parser.add_argument("--print-width", type=Decimal, default=None, help="Physical printable width in inches.")
        parser.add_argument("--print-height", type=Decimal, default=None, help="Physical printable height in inches.")
        parser.add_argument("--surface-label", default="Award")
        parser.add_argument("--area-name", default="Personalisation Area")

    def handle(self, *args, **opts):
        try:
            product = Product.objects.select_related("category").get(pk=opts["product_id"])
        except Product.DoesNotExist as exc:
            raise CommandError(f'Product {opts["product_id"]} does not exist.') from exc

        category_name = (getattr(product.category, "name", "") or "").lower()
        if "award" not in category_name:
            raise CommandError(f'Product {product.id} is not in the Awards category ({product.category}).')

        for key in ("workspace_width", "workspace_height", "width", "height"):
            if opts[key] <= 0:
                raise CommandError(f"--{key.replace('_','-')} must be greater than zero.")
        for key in ("left", "top"):
            if opts[key] < 0:
                raise CommandError(f"--{key} cannot be negative.")
        if opts["left"] + opts["width"] > 100 or opts["top"] + opts["height"] > 100:
            raise CommandError("Print area must remain inside the 0-100% workspace.")

        print_w = opts["print_width"] or product.print_width_in
        print_h = opts["print_height"] or product.print_height_in
        if not print_w or not print_h:
            raise CommandError("Provide --print-width and --print-height; no verified printable dimensions exist on this product.")

        # Opt-in only. Existing non-Award products/templates are untouched.
        product.editor_layout_mode = "print_area"
        product.workspace_width_in = opts["workspace_width"]
        product.workspace_height_in = opts["workspace_height"]
        product.constrain_to_print_area = True
        product.show_product_reference = True
        product.save(update_fields=[
            "editor_layout_mode", "workspace_width_in", "workspace_height_in",
            "constrain_to_print_area", "show_product_reference",
        ])

        surface, _ = ProductPrintSurface.objects.update_or_create(
            product=product,
            label=opts["surface_label"],
            defaults={
                "workspace_width_in": opts["workspace_width"],
                "workspace_height_in": opts["workspace_height"],
                "print_width_in": print_w,
                "print_height_in": print_h,
                "sort_order": 0,
                "is_active": True,
            },
        )

        # Do not destroy any existing print areas. Update/create the named universal area.
        area, _ = ProductPrintArea.objects.update_or_create(
            product=product,
            surface=surface,
            name=opts["area_name"],
            defaults={
                "left": opts["left"], "top": opts["top"],
                "width": opts["width"], "height": opts["height"],
                "print_width_in": print_w, "print_height_in": print_h,
                "sort_order": 0,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"{product.id} — {product.name}: Awards editor configured | "
            f"ruler {opts['workspace_width']} × {opts['workspace_height']} in | "
            f"area {area.left}%/{area.top}%/{area.width}%/{area.height}% | "
            f"print {print_w} × {print_h} in"
        ))
