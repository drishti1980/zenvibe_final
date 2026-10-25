# designer/management/commands/configure_awards_editable.py

from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product, ProductPrintArea


# ============================================================
# ZENVIBE AWARDS EDITOR CONFIGURATION
# ============================================================
#
# IMPORTANT
# ---------
# 1. All physical measurements in this file are INCHES.
#
# 2. Fabric.js can continue using pixels internally.
#
# 3. Product.width / Product.height are used as the physical
#    dimensions displayed by the editor ruler.
#
# 4. print_width_in / print_height_in are the physical
#    personalization/engraving dimensions.
#
# 5. print_left_pct / print_top_pct / print_width_pct /
#    print_height_pct position the editable region over the
#    product image.
#
# 6. Business Card templates are NEVER touched by this command.
#
# 7. DesignTemplate is deliberately NOT imported here.
#
# ============================================================


@dataclass(frozen=True)
class AwardGeometry:
    structure: str

    # Full editor ruler dimensions - INCHES
    ruler_w: float
    ruler_h: float

    # Editable area on product image - PERCENT
    left: float
    top: float
    width: float
    height: float

    # Physical personalization size - INCHES
    print_w: float
    print_h: float

    # Safe margin / bleed - INCHES
    safe_margin: float = 0.08
    bleed: float = 0.00


# ============================================================
# STRUCTURE DEFAULTS
# ============================================================
#
# These are fallback geometry profiles.
#
# Product-specific measurements can override these through
# EXACT_PRODUCT_GEOMETRY below.
#
# ============================================================

STRUCTURE_GEOMETRY = {

    "TROPHY_PLATE": AwardGeometry(
        structure="TROPHY_PLATE",
        ruler_w=40.0,
        ruler_h=28.0,
        left=35.0,
        top=72.0,
        width=30.0,
        height=10.0,
        print_w=2.50,
        print_h=0.80,
    ),

    "CUP_PLATE": AwardGeometry(
        structure="CUP_PLATE",
        ruler_w=40.0,
        ruler_h=28.0,
        left=33.0,
        top=73.0,
        width=34.0,
        height=10.0,
        print_w=3.00,
        print_h=0.85,
    ),

    "CRYSTAL_FACE": AwardGeometry(
        structure="CRYSTAL_FACE",
        ruler_w=20.0,
        ruler_h=20.0,
        left=27.0,
        top=24.0,
        width=46.0,
        height=48.0,
        print_w=3.20,
        print_h=4.20,
    ),

    "IRREGULAR_CRYSTAL": AwardGeometry(
        structure="IRREGULAR_CRYSTAL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=30.0,
        top=30.0,
        width=40.0,
        height=40.0,
        print_w=2.80,
        print_h=3.20,
    ),

    "DIAMOND_CRYSTAL": AwardGeometry(
        structure="DIAMOND_CRYSTAL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=30.0,
        top=30.0,
        width=40.0,
        height=36.0,
        print_w=2.80,
        print_h=2.80,
    ),

    "STAR_CRYSTAL": AwardGeometry(
        structure="STAR_CRYSTAL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=31.0,
        top=34.0,
        width=38.0,
        height=34.0,
        print_w=2.70,
        print_h=2.50,
    ),

    "ROUND_CRYSTAL": AwardGeometry(
        structure="ROUND_CRYSTAL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=27.0,
        top=25.0,
        width=46.0,
        height=43.0,
        print_w=3.20,
        print_h=3.20,
    ),

    "PLAQUE": AwardGeometry(
        structure="PLAQUE",
        ruler_w=17.0,
        ruler_h=15.0,
        left=20.0,
        top=18.0,
        width=60.0,
        height=64.0,
        print_w=4.20,
        print_h=5.40,
    ),

    "CERTIFICATE": AwardGeometry(
        structure="CERTIFICATE",
        ruler_w=17.0,
        ruler_h=15.0,
        left=18.0,
        top=19.0,
        width=64.0,
        height=60.0,
        print_w=6.00,
        print_h=4.20,
    ),

    "MEDAL": AwardGeometry(
        structure="MEDAL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=33.0,
        top=29.0,
        width=34.0,
        height=31.0,
        print_w=1.75,
        print_h=1.75,
    ),

    "RESIN_PANEL": AwardGeometry(
        structure="RESIN_PANEL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=29.0,
        top=47.0,
        width=42.0,
        height=30.0,
        print_w=3.20,
        print_h=2.30,
    ),

    "SCULPTURAL": AwardGeometry(
        structure="SCULPTURAL",
        ruler_w=20.0,
        ruler_h=20.0,
        left=32.0,
        top=42.0,
        width=36.0,
        height=26.0,
        print_w=2.50,
        print_h=2.00,
    ),
}


# ============================================================
# PRODUCT -> STRUCTURE
# ============================================================

PRODUCT_STRUCTURE = {

    19: "TROPHY_PLATE",
    20: "CRYSTAL_FACE",
    21: "RESIN_PANEL",
    22: "CRYSTAL_FACE",
    23: "MEDAL",
    24: "MEDAL",
    25: "CERTIFICATE",
    26: "TROPHY_PLATE",
    27: "CRYSTAL_FACE",
    28: "IRREGULAR_CRYSTAL",
    29: "CRYSTAL_FACE",
    30: "MEDAL",
    31: "MEDAL",
    32: "DIAMOND_CRYSTAL",
    33: "STAR_CRYSTAL",
    34: "PLAQUE",
    35: "PLAQUE",
    36: "STAR_CRYSTAL",
    37: "TROPHY_PLATE",

    105: "SCULPTURAL",
    106: "CRYSTAL_FACE",
    107: "PLAQUE",
    111: "CERTIFICATE",
    113: "CRYSTAL_FACE",
    114: "SCULPTURAL",
    115: "CRYSTAL_FACE",
    116: "CRYSTAL_FACE",
    117: "STAR_CRYSTAL",
    118: "STAR_CRYSTAL",
    119: "MEDAL",
    121: "MEDAL",
    122: "CERTIFICATE",
    123: "IRREGULAR_CRYSTAL",
    124: "MEDAL",
    125: "TROPHY_PLATE",
    126: "TROPHY_PLATE",
    129: "CUP_PLATE",
    131: "CUP_PLATE",
    132: "TROPHY_PLATE",
    133: "SCULPTURAL",
    134: "TROPHY_PLATE",
    139: "TROPHY_PLATE",
    140: "MEDAL",
    141: "TROPHY_PLATE",
    142: "IRREGULAR_CRYSTAL",
    143: "CUP_PLATE",

    184: "RESIN_PANEL",
    190: "IRREGULAR_CRYSTAL",
    202: "CUP_PLATE",
    214: "IRREGULAR_CRYSTAL",
    240: "DIAMOND_CRYSTAL",
    243: "IRREGULAR_CRYSTAL",
    246: "TROPHY_PLATE",
    254: "TROPHY_PLATE",

    275: "TROPHY_PLATE",
    279: "RESIN_PANEL",
    282: "CRYSTAL_FACE",
    295: "ROUND_CRYSTAL",
    331: "CRYSTAL_FACE",
    341: "IRREGULAR_CRYSTAL",
    443: "CUP_PLATE",
}


# ============================================================
# EXACT PRODUCT OVERRIDES
# ============================================================
#
# This is where an Award can have completely independent
# dimensions from other Awards of the same structural family.
#
# Therefore:
#
#   trophy A != trophy B
#   crystal A != crystal B
#
# whenever exact dimensions are available.
#
# ============================================================

EXACT_PRODUCT_GEOMETRY = {

    # --------------------------------------------------------
    # 3 Star Gold Plastic trophy (28 Cm)
    # --------------------------------------------------------
    26: AwardGeometry(
        structure="TROPHY_PLATE",

        # Customer-facing ruler in INCHES
        ruler_w=40.0,
        ruler_h=28.0,

        # Personalization/nameplate region
        left=35.0,
        top=72.0,
        width=30.0,
        height=10.0,

        # Physical engraving area in INCHES
        print_w=2.50,
        print_h=0.80,

        safe_margin=0.08,
        bleed=0.00,
    ),
}


# Blog/content record - not an Award product.
EXCLUDED_PRODUCT_IDS = {
    259,
}


# ============================================================
# HELPERS
# ============================================================

def detect_structure(product: Product) -> str:
    """
    Return the Award structural family.

    Explicit product mappings always take priority.
    """

    if product.id in PRODUCT_STRUCTURE:
        return PRODUCT_STRUCTURE[product.id]

    text = " ".join([
        product.name or "",
        product.slug or "",
    ]).lower()

    if "medal" in text:
        return "MEDAL"

    if "certificate" in text:
        return "CERTIFICATE"

    if "plaque" in text:
        return "PLAQUE"

    if "diamond" in text and (
        "crystal" in text or "glass" in text
    ):
        return "DIAMOND_CRYSTAL"

    if "star" in text and (
        "crystal" in text or "glass" in text
    ):
        return "STAR_CRYSTAL"

    if "round" in text and (
        "crystal" in text or "glass" in text
    ):
        return "ROUND_CRYSTAL"

    if "resin" in text:
        return "RESIN_PANEL"

    if any(word in text for word in [
        "ball in hand",
        "unity hand",
    ]):
        return "SCULPTURAL"

    if any(word in text for word in [
        "championship",
        "champion cup",
        "trophy cup",
        "grand trophy",
    ]):
        return "CUP_PLATE"

    if "trophy" in text and not any(
        word in text
        for word in ["crystal", "glass"]
    ):
        return "TROPHY_PLATE"

    if any(word in text for word in [
        "crystal",
        "glass",
        "award",
    ]):
        return "CRYSTAL_FACE"

    return "IRREGULAR_CRYSTAL"


def get_geometry(product: Product):
    """
    Exact per-product configuration wins.

    Otherwise use the Award's structural fallback.
    """

    exact = EXACT_PRODUCT_GEOMETRY.get(product.id)

    if exact:
        return exact, "EXACT"

    structure = detect_structure(product)

    geometry = STRUCTURE_GEOMETRY.get(
        structure,
        STRUCTURE_GEOMETRY["IRREGULAR_CRYSTAL"],
    )

    return geometry, "STRUCTURE"


def get_orientation(geometry: AwardGeometry) -> str:

    if geometry.ruler_w > geometry.ruler_h:
        return "landscape"

    if geometry.ruler_h > geometry.ruler_w:
        return "portrait"

    return "square"


def validate_geometry(product, geometry):

    errors = []

    if geometry.ruler_w <= 0:
        errors.append("ruler_w must be > 0")

    if geometry.ruler_h <= 0:
        errors.append("ruler_h must be > 0")

    if geometry.print_w <= 0:
        errors.append("print_w must be > 0")

    if geometry.print_h <= 0:
        errors.append("print_h must be > 0")

    if not 0 <= geometry.left <= 100:
        errors.append("left outside 0-100")

    if not 0 <= geometry.top <= 100:
        errors.append("top outside 0-100")

    if geometry.width <= 0:
        errors.append("width must be > 0")

    if geometry.height <= 0:
        errors.append("height must be > 0")

    if geometry.left + geometry.width > 100.01:
        errors.append(
            "print area extends beyond image horizontally"
        )

    if geometry.top + geometry.height > 100.01:
        errors.append(
            "print area extends beyond image vertically"
        )

    if errors:
        raise CommandError(
            f"Invalid Award geometry for "
            f"#{product.id} {product.name}: "
            + "; ".join(errors)
        )


# ============================================================
# COMMAND
# ============================================================

class Command(BaseCommand):

    help = (
        "Configure Zenvibe Award products with "
        "structure-aware editable print areas and "
        "customer-facing inch rulers."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate without modifying database.",
        )

        parser.add_argument(
            "--replace-print-areas",
            action="store_true",
            help=(
                "Replace existing Award Personalization "
                "print areas."
            ),
        )

        parser.add_argument(
            "--product-id",
            type=int,
            default=None,
            help="Configure only one Award product.",
        )

    def handle(self, *args, **options):

        dry_run = options["dry_run"]

        replace_print_areas = options[
            "replace_print_areas"
        ]

        product_id = options["product_id"]

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "ZENVIBE AWARDS EDITOR CONFIGURATION V3"
            )
        )

        self.stdout.write(
            "Measurement system: INCHES"
        )

        self.stdout.write(
            "Business Card templates: UNTOUCHED"
        )

        self.stdout.write("")

        # ----------------------------------------------------
        # ONLY AWARD CATEGORIES
        # ----------------------------------------------------

        qs = (
            Product.objects
            .select_related("category")
            .filter(
                category__name__icontains="award"
            )
            .order_by("id")
        )

        if product_id is not None:

            qs = qs.filter(id=product_id)

            if not qs.exists():
                raise CommandError(
                    f"Award product #{product_id} "
                    f"was not found."
                )

        configured = 0
        excluded = 0
        exact_count = 0
        structural_count = 0

        with transaction.atomic():

            for product in qs:

                if product.id in EXCLUDED_PRODUCT_IDS:

                    excluded += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"SKIP #{product.id}: "
                            f"{product.name} "
                            f"(non-product/content record)"
                        )
                    )

                    continue

                geometry, source = get_geometry(product)

                validate_geometry(
                    product,
                    geometry,
                )

                if source == "EXACT":
                    exact_count += 1
                else:
                    structural_count += 1

                configured += 1

                self.stdout.write(
                    f"#{product.id:<4} "
                    f"{geometry.structure:<20} "
                    f"{source:<9} "
                    f"RULER "
                    f"{geometry.ruler_w:g} x "
                    f"{geometry.ruler_h:g} in | "
                    f"PRINT "
                    f"{geometry.print_w:g} x "
                    f"{geometry.print_h:g} in | "
                    f"L={geometry.left:.1f}% "
                    f"T={geometry.top:.1f}% "
                    f"W={geometry.width:.1f}% "
                    f"H={geometry.height:.1f}% | "
                    f"{product.name}"
                )

                if dry_run:
                    continue

                # ==================================================
                # PRODUCT PHYSICAL CONFIGURATION
                # ==================================================
                #
                # IMPORTANT:
                # width and height are INCHES here.
                #
                # Fabric canvas remains pixels internally.
                #
                # ==================================================

                product.width = geometry.ruler_w
                product.height = geometry.ruler_h

                product.print_width_in = geometry.print_w
                product.print_height_in = geometry.print_h

                product.safe_margin_in = (
                    geometry.safe_margin
                )

                product.bleed_in = geometry.bleed

                # Keep legacy mm values from controlling
                # the Award editor.
                #
                # We don't need to delete them because other
                # parts of the project may still reference them.
                #
                # Customer-facing Award editor must use *_in.

                product.print_left_pct = geometry.left
                product.print_top_pct = geometry.top
                product.print_width_pct = geometry.width
                product.print_height_pct = geometry.height

                product.orientation = get_orientation(
                    geometry
                )

                product.customizer_mode = "editor"

                product.save(
                    update_fields=[
                        "width",
                        "height",

                        "print_width_in",
                        "print_height_in",

                        "safe_margin_in",
                        "bleed_in",

                        "print_left_pct",
                        "print_top_pct",
                        "print_width_pct",
                        "print_height_pct",

                        "orientation",
                        "customizer_mode",
                    ]
                )

                # ==================================================
                # PRODUCT PRINT AREA
                # ==================================================

                area_name = "Award Personalization"

                if replace_print_areas:

                    ProductPrintArea.objects.filter(
                        product=product,
                    ).delete()

                existing = (
                    ProductPrintArea.objects
                    .filter(
                        product=product,
                        name=area_name,
                    )
                    .first()
                )

                values = {
                    "left": geometry.left,
                    "top": geometry.top,
                    "width": geometry.width,
                    "height": geometry.height,
                    "sort_order": 0,
                }

                if existing:

                    existing.left = values["left"]
                    existing.top = values["top"]
                    existing.width = values["width"]
                    existing.height = values["height"]
                    existing.sort_order = 0

                    existing.save(
                        update_fields=[
                            "left",
                            "top",
                            "width",
                            "height",
                            "sort_order",
                        ]
                    )

                else:

                    # IMPORTANT
                    # ---------
                    # ProductPrintArea.product_image is a
                    # ForeignKey to ProductImage.
                    #
                    # NEVER do:
                    #
                    # product_image=product.image
                    #
                    # because product.image is ImageFieldFile.
                    #

                    ProductPrintArea.objects.create(
                        product=product,
                        product_image=None,
                        name=area_name,
                        left=geometry.left,
                        top=geometry.top,
                        width=geometry.width,
                        height=geometry.height,
                        sort_order=0,
                    )

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")

        prefix = (
            "DRY RUN COMPLETE"
            if dry_run
            else "COMPLETE"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}: "
                f"{configured} Award products configured; "
                f"{excluded} excluded."
            )
        )

        self.stdout.write(
            f"Exact product configurations: "
            f"{exact_count}"
        )

        self.stdout.write(
            f"Structure fallback configurations: "
            f"{structural_count}"
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Award ruler measurement unit: INCHES"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Award print-area measurement unit: INCHES"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Business Card templates were not modified."
            )
        )