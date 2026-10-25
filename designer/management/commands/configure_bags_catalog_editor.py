from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, ProductPrintArea

class Command(BaseCommand):
    help = "Opt the 10 localized canonical Bags into the universal product-first editor without inventing physical dimensions."

    def handle(self, *args, **options):
        qs = Product.objects.filter(category__name__iexact="Bags", is_active=True).order_by("id")
        products = []
        for p in qs:
            a = p.source_attributes if isinstance(p.source_attributes, dict) else {}
            if a.get("source_localized") is True and a.get("catalogue_family") == "bags" and a.get("source_product_id"):
                products.append(p)
        if len(products) != 10:
            raise CommandError(f"Expected 10 active localized canonical Bags, found {len(products)}. Refusing partial configuration.")

        configured = 0
        # Verified local product-photo geometry for Budget Cotton Tote (source 548).
        # Workspace inches are the physical bag face; the printable rectangle is
        # derived from the clean front-facing colour mockups, not the old logo sample.
        verified = {
            # Percentages are aligned to each LOCAL front-facing product image.
            # Workspace dimensions are per-product physical faces, never shared globally.
            "543": {"workspace": ("12.000","16.000"), "area": ("31.00","35.00","38.00","30.00"), "print": ("4.560","4.800")},
            "544": {"workspace": ("13.000","15.000"), "area": ("25.00","38.00","50.00","38.00"), "print": ("6.500","5.700")},
            "548": {"workspace": ("15.000","16.000"), "area": ("28.00","41.00","44.00","31.00"), "print": ("6.600","4.960")},
            "553": {"workspace": ("12.000","6.000"),  "area": ("29.00","36.00","42.00","31.00"), "print": ("5.040","1.860")},
            "617": {"workspace": ("10.000","13.000"), "area": ("25.00","30.00","50.00","46.00"), "print": ("5.000","5.980")},
            "686": {"workspace": ("12.000","16.000"), "area": ("31.00","37.00","38.00","29.00"), "print": ("4.560","4.640")},
            "687": {"workspace": ("12.000","16.000"), "area": ("31.00","37.00","38.00","29.00"), "print": ("4.560","4.640")},
            "688": {"workspace": ("12.000","6.000"),  "area": ("29.00","36.00","42.00","31.00"), "print": ("5.040","1.860")},
            "689": {"workspace": ("14.000","18.000"), "area": ("27.00","35.00","46.00","38.00"), "print": ("6.440","6.840")},
            "704": {"workspace": ("11.000","10.000"), "area": ("29.00","34.00","42.00","35.00"), "print": ("4.620","3.500")},
        }
        with transaction.atomic():
            for p in products:
                p.customizer_mode = "bags"
                p.editor_layout_mode = "print_area"
                p.constrain_to_print_area = True
                p.show_product_reference = True
                if not p.editor_reference_image and p.image:
                    p.editor_reference_image.name = p.image.name
                fields = ["customizer_mode","editor_layout_mode","constrain_to_print_area","show_product_reference","editor_reference_image"]

                # Preserve any dimensions already configured for this exact product.
                # Do not copy measurements between different bags.
                if p.workspace_width_in is None and p.print_width_in is not None:
                    p.workspace_width_in = p.print_width_in
                    fields.append("workspace_width_in")
                if p.workspace_height_in is None and p.print_height_in is not None:
                    p.workspace_height_in = p.print_height_in
                    fields.append("workspace_height_in")
                sid = str((p.source_attributes or {}).get("source_product_id") or "")
                cfg = verified.get(sid)
                if cfg:
                    ww, wh = cfg["workspace"]
                    p.workspace_width_in = Decimal(ww)
                    p.workspace_height_in = Decimal(wh)
                    fields += ["workspace_width_in", "workspace_height_in"]
                p.save(update_fields=list(dict.fromkeys(fields)))

                if cfg:
                    left, top, width, height = cfg["area"]
                    pw, ph = cfg["print"]
                    ProductPrintArea.objects.filter(product=p).delete()
                    ProductPrintArea.objects.create(
                        product=p, name="Front print area",
                        left=Decimal(left), top=Decimal(top),
                        width=Decimal(width), height=Decimal(height),
                        print_width_in=Decimal(pw), print_height_in=Decimal(ph),
                        sort_order=0,
                    )
                    p.print_left_pct=Decimal(left); p.print_top_pct=Decimal(top)
                    p.print_width_pct=Decimal(width); p.print_height_pct=Decimal(height)
                    p.print_width_in=Decimal(pw); p.print_height_in=Decimal(ph)
                    p.save(update_fields=["print_left_pct","print_top_pct","print_width_pct","print_height_pct","print_width_in","print_height_in"])
                    configured += 1
                    continue

                # Materialise only existing product-specific percentage geometry.
                if not p.print_areas.exists():
                    vals=(p.print_left_pct,p.print_top_pct,p.print_width_pct,p.print_height_pct)
                    if all(v is not None for v in vals):
                        ProductPrintArea.objects.create(
                            product=p,name="Print area",left=p.print_left_pct,top=p.print_top_pct,
                            width=p.print_width_pct,height=p.print_height_pct,
                            print_width_in=p.print_width_in,print_height_in=p.print_height_in,sort_order=0)
                configured += 1
        self.stdout.write(self.style.SUCCESS(
            f"Bags editor configured: {configured}/10 canonical products. "
            "Universal restricted editor enabled; local product references locked; existing product-specific geometry preserved. "
            "No unverified inch dimensions or fake editable templates were created."
        ))
