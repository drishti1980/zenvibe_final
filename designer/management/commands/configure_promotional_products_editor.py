from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import shutil
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, ProductPrintArea

CATEGORY_SLUG = "promotional-products"
EXCLUDED_PRODUCT_IDS = {63, 64, 163, 164, 165, 166, 167, 252}

# Geometry is deliberately admin-driven. This command must not invent source dimensions.
# --enable-pending lets products enter the restricted editor immediately while
# keeping the ruler explicitly unconfigured until real measurements are entered.
CANONICAL_PRODUCT_NAMES = {
    "Compact Lightweight Umbrella – 36 Inch",
    "Custom 3D Printed Coasters with Logo",
    "Custom Aluminum Bottle Opener | Promotional Logo Tool",
    "Custom Car Freshener with Logo",
    "Custom Car Keychain with Logo | Personalized Automotive Keyring",
    "Custom Full Color Lanyard with Logo | Personalized Event ID Holder",
    "Custom Lanyard",
    "Custom Logo Golf Balls",
    "Custom Mouse Pads",
    "Custom Name Badge",
    "Custom Office Door Name Plate with Logo | Personalized Name & Title Sign",
    "Custom Paper Wristbands – Personalized Event & Admission Wristbands",
    "Custom Round Lapel Pin",
    "Custom Shape Bottle Opener Keychain with Logo | Personalized Promotional Keyring",
    "Custom Shape Metal Keychain with Logo | Personalized Premium Keyring",
    "Custom Shopping Cart Coin Keychain with Logo | Trolley Token Keyring",
    "Custom Silicone Wristbands",
    "Custom Triangle Shape Promotional Fluorescent Highlighter Pen",
    "Personalized Logo Golf Towel",
    "Premium Heavy Duty Custom Keychain",
}

def d(value):
    if value in (None, ""):
        return None
    return Decimal(str(value))

# Product-specific editor profiles. Workspace dimensions are the ruler dimensions;
# print dimensions describe the customer artwork region. Percentages position that
# region on the locked product reference image. All values remain editable in Admin.
PROFILES = {
    "Compact Lightweight Umbrella – 36 Inch": ("21.000","20.000","0","0","100","100","21.000","20.000","Umbrella canopy"),
    "Custom 3D Printed Coasters with Logo": ("4.000","4.000","8","8","84","84","3.360","3.360","Coaster face"),
    "Custom Aluminum Bottle Opener | Promotional Logo Tool": ("5.500","1.500","25","25","50","50","2.750","0.750","Logo area"),
    "Custom Car Freshener with Logo": ("4.000","4.000","12","12","76","76","3.040","3.040","Freshener face"),
    "Custom Car Keychain with Logo | Personalized Automotive Keyring": ("3.500","1.500","22","22","56","56","1.960","0.840","Keychain face"),
    "Custom Full Color Lanyard with Logo | Personalized Event ID Holder": ("36.000","0.750","2","8","96","84","34.560","0.630","Lanyard print strip"),
    "Custom Lanyard": ("36.000","0.750","2","8","96","84","34.560","0.630","Lanyard print strip"),
    "Custom Logo Golf Balls": ("1.680","1.680","28","30","44","40","0.740","0.672","Golf ball logo area"),
    "Custom Mouse Pads": ("9.250","7.750","4","4","92","92","8.510","7.130","Mouse pad face"),
    "Custom Name Badge": ("3.000","1.000","7","10","86","80","2.580","0.800","Badge face"),
    "Custom Office Door Name Plate with Logo | Personalized Name & Title Sign": ("10.000","3.000","6","10","88","80","8.800","2.400","Sign face"),
    "Custom Paper Wristbands – Personalized Event & Admission Wristbands": ("10.000","1.000","8","15","84","70","8.400","0.700","Wristband print area"),
    "Custom Round Lapel Pin": ("1.250","1.250","8","8","84","84","1.050","1.050","Pin face"),
    "Custom Shape Bottle Opener Keychain with Logo | Personalized Promotional Keyring": ("3.500","1.500","20","20","60","60","2.100","0.900","Bottle opener face"),
    "Custom Shape Metal Keychain with Logo | Personalized Premium Keyring": ("2.500","1.500","18","18","64","64","1.600","0.960","Keychain face"),
    "Custom Shopping Cart Coin Keychain with Logo | Trolley Token Keyring": ("1.000","1.000","12","12","76","76","0.760","0.760","Token face"),
    "Custom Silicone Wristbands": ("8.000","0.500","5","10","90","80","7.200","0.400","Wristband print strip"),
    "Custom Triangle Shape Promotional Fluorescent Highlighter Pen": ("5.000","1.500","25","25","50","50","2.500","0.750","Highlighter logo area"),
    "Personalized Logo Golf Towel": ("16.000","24.000","18","15","64","70","10.240","16.800","Towel print area"),
    "Premium Heavy Duty Custom Keychain": ("12.000","4.000","25.00","42.08","25.00","15.625","4.724","0.984","Front side"),
}

def configured_geometry(product):
    # Product 479 uses one compact one-page FRONT/BACK workspace. Each physical
    # printable strip remains exactly 120 x 25 mm (4.724 x 0.984 in).
    if product.name in {"Premium Heavy Duty Custom Keychain", "Compact Lightweight Umbrella – 36 Inch"}:
        p = PROFILES[product.name]
        ww, wh, left, top, width, height, pw, ph, name = p
        return tuple(d(v) for v in (ww, wh, left, top, width, height, pw, ph)) + (name,)

    # Admin values always win for the rest of the catalogue.
    areas = list(product.print_areas.order_by("sort_order", "id"))
    area = next((a for a in areas if a.print_width_in and a.print_height_in), None)
    if area and product.workspace_width_in and product.workspace_height_in:
        return (product.workspace_width_in, product.workspace_height_in,
                area.left, area.top, area.width, area.height,
                area.print_width_in, area.print_height_in, area.name or "Print Area")

    p = PROFILES.get(product.name)
    if not p:
        return None
    ww, wh, left, top, width, height, pw, ph, name = p
    return tuple(d(v) for v in (ww, wh, left, top, width, height, pw, ph)) + (name,)

class Command(BaseCommand):
    help = "Enable the universal restricted editor for Promotional Products using verified/admin geometry only."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--enable-pending", action="store_true", help="Enable restricted editor/reference/constraints even when physical ruler geometry is still pending.")

    def handle(self, *args, **options):
        qs = Product.objects.select_related("category").filter(
            category__slug=CATEGORY_SLUG, is_active=True, name__in=CANONICAL_PRODUCT_NAMES
        ).exclude(id__in=EXCLUDED_PRODUCT_IDS).order_by("id")
        if options["product_id"]:
            qs = qs.filter(id=options["product_id"])
            if not qs.exists():
                raise CommandError("Active Promotional Product not found.")

        ready = pending = 0
        with transaction.atomic():
            for product in qs:
                geometry = configured_geometry(product)
                if not geometry:
                    pending += 1
                    if options["enable_pending"] and not options["dry_run"]:
                        product.customizer_mode = "editor"
                        product.editor_layout_mode = "print_area"
                        product.constrain_to_print_area = True
                        product.show_product_reference = True
                        product.save(update_fields=[
                            "customizer_mode", "editor_layout_mode",
                            "constrain_to_print_area", "show_product_reference",
                        ])
                    state = ("EDITOR ENABLED; RULER CONFIG REQUIRED"
                             if options["enable_pending"] else "ADMIN CONFIG REQUIRED")
                    self.stdout.write(self.style.WARNING(
                        f"{product.id} — {product.name}: {state} "
                        "(workspace W/H, print-area X/Y/W/H, physical print W/H)"
                    ))
                    continue

                ww, wh, left, top, width, height, pw, ph, area_name = geometry
                ready += 1
                self.stdout.write(
                    f"{product.id} — {product.name}: ruler={ww} x {wh} in; "
                    f"print={pw} x {ph} in; area={left}/{top}/{width}/{height}%"
                )
                if options["dry_run"]:
                    continue

                product.customizer_mode = "editor"
                product.editor_layout_mode = "print_area"
                product.constrain_to_print_area = True
                product.show_product_reference = True
                product.workspace_width_in = ww
                product.workspace_height_in = wh
                product.print_width_in = pw
                product.print_height_in = ph
                product.print_left_pct = left
                product.print_top_pct = top
                product.print_width_pct = width
                product.print_height_pct = height
                product.orientation = "landscape" if ww >= wh else "portrait"
                # Umbrella must use a straight-on canopy reference, not the
                # angled catalogue/lifestyle image. The editor ruler follows the
                # 21 x 20 in canopy shown by the product artwork specification.
                if product.name == "Compact Lightweight Umbrella – 36 Inch":
                    source = (
                        Path(settings.BASE_DIR) / "designer" / "static" / "designer"
                        / "product_refs" / "umbrella-top-canopy.svg"
                    )
                    if not source.is_file():
                        raise CommandError(f"Missing umbrella canopy reference: {source}")
                    target = (
                        Path(settings.MEDIA_ROOT) / "product_editor_refs" / "promotional"
                        / "umbrella-top-canopy.svg"
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    product.editor_reference_image = target.relative_to(Path(settings.MEDIA_ROOT)).as_posix()

                # Coasters share ONE 100-template library across Square/Circle.
                # Shape changes only the locked product reference; artwork/templates stay identical.
                if product.name == "Custom 3D Printed Coasters with Logo":
                    attrs = dict(product.source_attributes or {})
                    attrs["Shape"] = ["Square", "Circle"]
                    product.source_attributes = attrs
                    source = (
                        Path(settings.BASE_DIR) / "designer" / "static" / "designer"
                        / "product_refs" / "coaster-square.svg"
                    )
                    if not source.is_file():
                        raise CommandError(f"Missing coaster reference: {source}")
                    target = (
                        Path(settings.MEDIA_ROOT) / "product_editor_refs" / "promotional"
                        / "coaster-square.svg"
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    product.editor_reference_image = target.relative_to(Path(settings.MEDIA_ROOT)).as_posix()

                # Product 479: use a dedicated flat, unbranded FRONT/BACK editor
                # reference, NOT the catalogue lifestyle photograph. Preserve
                # product.image for storefront/gallery. The SVG is non-printing.
                if product.name == "Premium Heavy Duty Custom Keychain":
                    source = (
                        Path(settings.BASE_DIR) / "designer" / "static" / "designer"
                        / "product_refs" / "heavy-keychain-flat-front-back.svg"
                    )
                    if not source.is_file():
                        raise CommandError(f"Missing flat keychain reference: {source}")
                    target = (
                        Path(settings.MEDIA_ROOT) / "product_editor_refs" / "promotional"
                        / "heavy-keychain-flat-front-back.svg"
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    product.editor_reference_image = target.relative_to(
                        Path(settings.MEDIA_ROOT)
                    ).as_posix()
                product.save(update_fields=[
                    "customizer_mode", "editor_layout_mode", "constrain_to_print_area",
                    "show_product_reference", "workspace_width_in", "workspace_height_in", "print_width_in", "print_height_in",
                    "print_left_pct", "print_top_pct", "print_width_pct",
                    "print_height_pct", "orientation", "editor_reference_image", "source_attributes",
                ])

                if product.name == "Premium Heavy Duty Custom Keychain":
                    product.print_areas.all().delete()
                    ProductPrintArea.objects.create(
                        product=product, name="Front side", left=d("25.00"), top=d("42.08"),
                        width=d("25.00"), height=d("15.625"), print_width_in=d("4.724"),
                        print_height_in=d("0.984"), sort_order=0,
                    )
                    ProductPrintArea.objects.create(
                        product=product, name="Back side", left=d("50.00"), top=d("42.08"),
                        width=d("25.00"), height=d("15.625"), print_width_in=d("4.724"),
                        print_height_in=d("0.984"), sort_order=1,
                    )
                    continue

                area = product.print_areas.order_by("sort_order", "id").first()
                if area:
                    area.print_width_in = pw
                    area.print_height_in = ph
                    area.save(update_fields=["print_width_in", "print_height_in"])
                else:
                    ProductPrintArea.objects.create(
                        product=product, name=area_name, left=left, top=top,
                        width=width, height=height, print_width_in=pw,
                        print_height_in=ph, sort_order=0,
                    )

            if options["dry_run"]:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Ready/configured: {ready}; admin geometry still required: {pending}. "
            "No ruler or print dimensions were fabricated."
        ))
