from __future__ import annotations

import copy
import json
from itertools import count

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product, ProductPrintArea, DesignTemplate


VERSION = 1
CANVAS_LONG = 1000

EXCLUDED_PRODUCT_IDS = {259}

STRUCTURE_BY_ID = {
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


def structure_for(product):
    if product.id in STRUCTURE_BY_ID:
        return STRUCTURE_BY_ID[product.id]

    text = f"{product.name} {product.slug}".lower()

    if "medal" in text:
        return "MEDAL"
    if "certificate" in text:
        return "CERTIFICATE"
    if "plaque" in text:
        return "PLAQUE"
    if "diamond" in text:
        return "DIAMOND_CRYSTAL"
    if "star" in text and "crystal" in text:
        return "STAR_CRYSTAL"
    if "resin" in text:
        return "RESIN_PANEL"
    if "cup" in text or "championship" in text:
        return "CUP_PLATE"
    if "trophy" in text and "crystal" not in text:
        return "TROPHY_PLATE"
    if "crystal" in text or "glass" in text:
        return "CRYSTAL_FACE"

    return "IRREGULAR_CRYSTAL"


def canvas_size(product):
    """
    Canvas represents the personalization surface, not the full product photo.
    Preserve the physical print-area aspect ratio.
    """
    try:
        w = float(product.print_width_in or 0)
        h = float(product.print_height_in or 0)
    except (TypeError, ValueError):
        w = h = 0

    if w <= 0 or h <= 0:
        return 800, 1000

    if w >= h:
        width = CANVAS_LONG
        height = max(260, round(CANVAS_LONG * h / w))
    else:
        height = CANVAS_LONG
        width = max(260, round(CANVAS_LONG * w / h))

    return width, height


class Objects:
    def __init__(self):
        self.ids = count(1)

    def _id(self, prefix):
        return f"{prefix}-{next(self.ids):07d}"

    def text(
        self,
        name,
        text,
        left,
        top,
        width,
        size,
        fill="#222222",
        font="Inter",
        weight="400",
        align="center",
        spacing=0,
        line_height=1.1,
        field_type="award-text",
    ):
        return {
            "id": self._id("text"),
            "name": name,
            "type": "textbox",
            "text": text,
            "left": round(left, 2),
            "top": round(top, 2),
            "width": round(width, 2),
            "fontSize": round(size, 2),
            "fill": fill,
            "fontFamily": font,
            "font": font,
            "fontWeight": weight,
            "fontStyle": "normal",
            "textAlign": align,
            "lineHeight": line_height,
            "charSpacing": spacing,
            "scaleX": 1,
            "scaleY": 1,
            "angle": 0,
            "opacity": 1,
            "customerEditable": True,
            "selectable": True,
            "evented": True,
            "locked": False,
            "fieldType": field_type,
        }

    def line(self, name, x1, y1, x2, y2, stroke="#B08D57", sw=2):
        return {
            "id": self._id("line"),
            "name": name,
            "type": "line",
            "x1": round(x1, 2),
            "y1": round(y1, 2),
            "x2": round(x2, 2),
            "y2": round(y2, 2),
            "left": round(min(x1, x2), 2),
            "top": round(min(y1, y2), 2),
            "stroke": stroke,
            "strokeWidth": sw,
            "fill": None,
            "opacity": 1,
            "angle": 0,
            "scaleX": 1,
            "scaleY": 1,
            "selectable": True,
            "evented": True,
            "locked": False,
            "customerEditable": True,
            "fieldType": "award-decoration",
        }

    def rect(
        self,
        name,
        left,
        top,
        width,
        height,
        fill,
        stroke=None,
        sw=0,
        rx=0,
        angle=0,
    ):
        return {
            "id": self._id("rect"),
            "name": name,
            "type": "rect",
            "left": round(left, 2),
            "top": round(top, 2),
            "width": round(width, 2),
            "height": round(height, 2),
            "fill": fill,
            "stroke": stroke,
            "strokeWidth": sw,
            "rx": rx,
            "ry": rx,
            "opacity": 1,
            "angle": angle,
            "scaleX": 1,
            "scaleY": 1,
            "selectable": True,
            "evented": True,
            "locked": False,
            "customerEditable": True,
            "fieldType": "award-decoration",
        }


def plate_layout(w, h, variant=0):
    """
    Trophy/cup plate.
    Keep this deliberately compact because these areas are only
    around 2.5-3 inches wide and less than 1 inch high.
    """
    o = Objects()

    margin = w * 0.06

    palettes = [
        ("#171717", "#A67C32"),
        ("#252525", "#8B6B2E"),
        ("#111111", "#555555"),
    ]
    text_color, accent = palettes[variant % len(palettes)]

    if variant % 3 == 0:
        return [
            o.text(
                "Award Title",
                "AWARD OF EXCELLENCE",
                margin,
                h * .12,
                w - 2 * margin,
                h * .17,
                text_color,
                "Inter",
                "700",
                spacing=60,
                field_type="award-title",
            ),
            o.line(
                "Editable Divider",
                w * .22,
                h * .39,
                w * .78,
                h * .39,
                accent,
                max(1, h * .008),
            ),
            o.text(
                "Recipient Name",
                "ALEXANDER SMITH",
                margin,
                h * .46,
                w - 2 * margin,
                h * .23,
                text_color,
                "Poppins",
                "700",
                field_type="award-recipient",
            ),
            o.text(
                "Award Date",
                "2026",
                margin,
                h * .76,
                w - 2 * margin,
                h * .13,
                "#555555",
                "Inter",
                "500",
                spacing=100,
                field_type="award-date",
            ),
        ]

    if variant % 3 == 1:
        return [
            o.text(
                "Recipient Name",
                "ALEXANDER SMITH",
                margin,
                h * .12,
                w - 2 * margin,
                h * .25,
                text_color,
                "Poppins",
                "700",
                field_type="award-recipient",
            ),
            o.text(
                "Recognition",
                "OUTSTANDING ACHIEVEMENT",
                margin,
                h * .48,
                w - 2 * margin,
                h * .15,
                accent,
                "Inter",
                "600",
                spacing=60,
                field_type="award-title",
            ),
            o.line(
                "Editable Divider",
                w * .34,
                h * .72,
                w * .66,
                h * .72,
                accent,
                max(1, h * .008),
            ),
            o.text(
                "Year",
                "2026",
                margin,
                h * .78,
                w - 2 * margin,
                h * .12,
                "#555555",
                field_type="award-date",
            ),
        ]

    return [
        o.text(
            "Award Title",
            "CHAMPION",
            margin,
            h * .10,
            w - 2 * margin,
            h * .27,
            accent,
            "Poppins",
            "700",
            spacing=80,
            field_type="award-title",
        ),
        o.text(
            "Recipient Name",
            "ALEXANDER SMITH",
            margin,
            h * .45,
            w - 2 * margin,
            h * .22,
            text_color,
            "Inter",
            "700",
            field_type="award-recipient",
        ),
        o.text(
            "Event",
            "ZENVIBE AWARDS • 2026",
            margin,
            h * .76,
            w - 2 * margin,
            h * .12,
            "#555555",
            "Inter",
            "500",
            spacing=45,
            field_type="award-company",
        ),
    ]


def medal_layout(w, h, variant=0):
    o = Objects()

    size = min(w, h)
    cx = w / 2

    if variant % 3 == 0:
        return [
            o.text(
                "Award Initial",
                "★",
                cx - size * .15,
                h * .13,
                size * .30,
                size * .12,
                "#A67C32",
                "Inter",
                "700",
                field_type="award-decoration-text",
            ),
            o.text(
                "Award Title",
                "EXCELLENCE",
                w * .12,
                h * .34,
                w * .76,
                size * .075,
                "#222222",
                "Inter",
                "700",
                spacing=80,
                field_type="award-title",
            ),
            o.text(
                "Recipient",
                "A. SMITH",
                w * .14,
                h * .51,
                w * .72,
                size * .095,
                "#222222",
                "Poppins",
                "600",
                field_type="award-recipient",
            ),
            o.text(
                "Year",
                "2026",
                w * .25,
                h * .70,
                w * .50,
                size * .065,
                "#666666",
                "Inter",
                "500",
                spacing=80,
                field_type="award-date",
            ),
        ]

    if variant % 3 == 1:
        return [
            o.text(
                "Medal Title",
                "WINNER",
                w * .14,
                h * .23,
                w * .72,
                size * .105,
                "#A67C32",
                "Poppins",
                "700",
                spacing=90,
                field_type="award-title",
            ),
            o.line(
                "Divider",
                w * .30,
                h * .44,
                w * .70,
                h * .44,
                "#A67C32",
                2,
            ),
            o.text(
                "Recipient",
                "ALEX SMITH",
                w * .12,
                h * .50,
                w * .76,
                size * .085,
                "#222222",
                "Inter",
                "700",
                field_type="award-recipient",
            ),
            o.text(
                "Year",
                "2026",
                w * .25,
                h * .69,
                w * .50,
                size * .06,
                "#555555",
                field_type="award-date",
            ),
        ]

    return [
        o.text(
            "Award Mark",
            "01",
            w * .25,
            h * .16,
            w * .50,
            size * .16,
            "#A67C32",
            "Poppins",
            "700",
            field_type="award-decoration-text",
        ),
        o.text(
            "Award Title",
            "ACHIEVEMENT",
            w * .10,
            h * .45,
            w * .80,
            size * .072,
            "#222222",
            "Inter",
            "700",
            spacing=55,
            field_type="award-title",
        ),
        o.text(
            "Recipient",
            "A. SMITH",
            w * .15,
            h * .62,
            w * .70,
            size * .078,
            "#555555",
            "Inter",
            "600",
            field_type="award-recipient",
        ),
    ]


def formal_layout(w, h, variant=0, compact=False):
    """
    Crystal / plaque / certificate / resin / irregular surfaces.
    All objects remain inside conservative internal margins.
    """
    o = Objects()

    margin = w * (.10 if compact else .08)
    usable = w - margin * 2

    palettes = [
        ("#222222", "#A67C32", "#555555"),
        ("#182231", "#96733C", "#4D5660"),
        ("#292929", "#6F6F6F", "#555555"),
        ("#1F2933", "#9A7440", "#4A4A4A"),
    ]

    primary, accent, secondary = palettes[variant % len(palettes)]

    if variant % 4 == 0:
        return [
            o.text(
                "Logo",
                "YOUR LOGO",
                w * .30,
                h * .07,
                w * .40,
                h * .035,
                secondary,
                "Inter",
                "600",
                spacing=130,
                field_type="award-logo-text",
            ),
            o.text(
                "Recognition",
                "PRESENTED WITH HONOUR",
                margin,
                h * .18,
                usable,
                h * .025,
                secondary,
                "Inter",
                "600",
                spacing=150,
                field_type="award-text",
            ),
            o.text(
                "Award Title",
                "AWARD OF\nEXCELLENCE",
                margin,
                h * .27,
                usable,
                h * .065,
                primary,
                "Poppins",
                "700",
                line_height=.92,
                field_type="award-title",
            ),
            o.line(
                "Gold Divider",
                w * .28,
                h * .47,
                w * .72,
                h * .47,
                accent,
                2,
            ),
            o.text(
                "Presented To",
                "PRESENTED TO",
                margin,
                h * .52,
                usable,
                h * .022,
                secondary,
                "Inter",
                "500",
                spacing=150,
                field_type="award-text",
            ),
            o.text(
                "Recipient Name",
                "ALEXANDER SMITH",
                margin,
                h * .59,
                usable,
                h * .052,
                accent,
                "Poppins",
                "600",
                field_type="award-recipient",
            ),
            o.text(
                "Message",
                "For outstanding achievement, leadership\nand continued excellence.",
                w * .14,
                h * .70,
                w * .72,
                h * .026,
                secondary,
                "Inter",
                "400",
                line_height=1.25,
                field_type="award-message",
            ),
            o.text(
                "Date",
                "2026",
                w * .30,
                h * .84,
                w * .40,
                h * .024,
                secondary,
                "Inter",
                "500",
                spacing=100,
                field_type="award-date",
            ),
        ]

    if variant % 4 == 1:
        return [
            o.text(
                "Award Eyebrow",
                "RECOGNITION",
                margin,
                h * .10,
                usable,
                h * .025,
                accent,
                "Inter",
                "700",
                spacing=220,
                field_type="award-text",
            ),
            o.text(
                "Award Title",
                "LEADERSHIP\nAWARD",
                margin,
                h * .20,
                usable,
                h * .072,
                primary,
                "Poppins",
                "700",
                line_height=.92,
                field_type="award-title",
            ),
            o.rect(
                "Editable Ornament",
                w * .475,
                h * .43,
                w * .05,
                w * .05,
                accent,
                angle=45,
            ),
            o.text(
                "Recipient Name",
                "ALEXANDER SMITH",
                margin,
                h * .54,
                usable,
                h * .055,
                accent,
                "Poppins",
                "600",
                field_type="award-recipient",
            ),
            o.text(
                "Message",
                "In appreciation of exceptional service\nand inspirational leadership.",
                w * .14,
                h * .67,
                w * .72,
                h * .027,
                secondary,
                "Inter",
                "400",
                line_height=1.3,
                field_type="award-message",
            ),
            o.line(
                "Bottom Divider",
                w * .34,
                h * .82,
                w * .66,
                h * .82,
                accent,
                2,
            ),
            o.text(
                "Company",
                "ZENVIBE AWARDS • 2026",
                margin,
                h * .86,
                usable,
                h * .021,
                secondary,
                "Inter",
                "600",
                spacing=90,
                field_type="award-company",
            ),
        ]

    if variant % 4 == 2:
        return [
            o.text(
                "Award Title",
                "OUTSTANDING\nACHIEVEMENT",
                margin,
                h * .12,
                usable,
                h * .067,
                primary,
                "Poppins",
                "700",
                line_height=.94,
                field_type="award-title",
            ),
            o.line(
                "Divider One",
                w * .22,
                h * .37,
                w * .78,
                h * .37,
                accent,
                3,
            ),
            o.text(
                "Recipient",
                "ALEXANDER SMITH",
                margin,
                h * .46,
                usable,
                h * .058,
                accent,
                "Poppins",
                "600",
                field_type="award-recipient",
            ),
            o.text(
                "Recognition Message",
                "Presented in recognition of dedication,\ncommitment and remarkable performance.",
                w * .14,
                h * .60,
                w * .72,
                h * .027,
                secondary,
                "Inter",
                "400",
                line_height=1.3,
                field_type="award-message",
            ),
            o.text(
                "Event",
                "ANNUAL RECOGNITION",
                margin,
                h * .78,
                usable,
                h * .022,
                secondary,
                "Inter",
                "600",
                spacing=140,
                field_type="award-company",
            ),
            o.text(
                "Year",
                "2026",
                margin,
                h * .85,
                usable,
                h * .027,
                primary,
                "Inter",
                "700",
                spacing=100,
                field_type="award-date",
            ),
        ]

    return [
        o.text(
            "Logo",
            "ZENVIBE",
            margin,
            h * .09,
            usable,
            h * .030,
            accent,
            "Poppins",
            "700",
            spacing=180,
            field_type="award-logo-text",
        ),
        o.line(
            "Top Divider",
            w * .30,
            h * .19,
            w * .70,
            h * .19,
            accent,
            2,
        ),
        o.text(
            "Award Title",
            "SERVICE\nEXCELLENCE",
            margin,
            h * .26,
            usable,
            h * .068,
            primary,
            "Poppins",
            "700",
            line_height=.94,
            field_type="award-title",
        ),
        o.text(
            "Presented To",
            "HONOURING",
            margin,
            h * .49,
            usable,
            h * .022,
            secondary,
            "Inter",
            "600",
            spacing=160,
            field_type="award-text",
        ),
        o.text(
            "Recipient",
            "ALEXANDER SMITH",
            margin,
            h * .56,
            usable,
            h * .055,
            accent,
            "Poppins",
            "600",
            field_type="award-recipient",
        ),
        o.text(
            "Message",
            "With appreciation for your exceptional\ncontribution and commitment.",
            w * .15,
            h * .69,
            w * .70,
            h * .026,
            secondary,
            "Inter",
            "400",
            line_height=1.3,
            field_type="award-message",
        ),
        o.text(
            "Date",
            "SEPTEMBER 2026",
            margin,
            h * .84,
            usable,
            h * .021,
            secondary,
            "Inter",
            "500",
            spacing=80,
            field_type="award-date",
        ),
    ]


def star_diamond_layout(w, h, variant=0):
    """
    Conservative centred layout to avoid star points / diamond edges.
    """
    o = Objects()
    primary = "#222222"
    accent = "#9B763B"

    if variant % 2 == 0:
        return [
            o.text(
                "Award Title",
                "EXCELLENCE",
                w * .18,
                h * .25,
                w * .64,
                h * .055,
                accent,
                "Poppins",
                "700",
                spacing=80,
                field_type="award-title",
            ),
            o.text(
                "Recipient",
                "ALEXANDER\nSMITH",
                w * .20,
                h * .43,
                w * .60,
                h * .065,
                primary,
                "Poppins",
                "600",
                line_height=.95,
                field_type="award-recipient",
            ),
            o.line(
                "Divider",
                w * .34,
                h * .67,
                w * .66,
                h * .67,
                accent,
                2,
            ),
            o.text(
                "Year",
                "2026",
                w * .30,
                h * .73,
                w * .40,
                h * .035,
                "#555555",
                "Inter",
                "500",
                spacing=100,
                field_type="award-date",
            ),
        ]

    return [
        o.text(
            "Award Label",
            "HONOUR",
            w * .25,
            h * .24,
            w * .50,
            h * .042,
            accent,
            "Inter",
            "700",
            spacing=180,
            field_type="award-text",
        ),
        o.text(
            "Recipient",
            "ALEX SMITH",
            w * .17,
            h * .43,
            w * .66,
            h * .060,
            primary,
            "Poppins",
            "700",
            field_type="award-recipient",
        ),
        o.text(
            "Achievement",
            "OUTSTANDING\nACHIEVEMENT",
            w * .22,
            h * .60,
            w * .56,
            h * .035,
            "#555555",
            "Inter",
            "600",
            line_height=1.05,
            field_type="award-title",
        ),
    ]


def build_template(product, structure, variant):
    w, h = canvas_size(product)

    if structure in {"TROPHY_PLATE", "CUP_PLATE"}:
        objects = plate_layout(w, h, variant)

    elif structure == "MEDAL":
        objects = medal_layout(w, h, variant)

    elif structure in {"STAR_CRYSTAL", "DIAMOND_CRYSTAL"}:
        objects = star_diamond_layout(w, h, variant)

    elif structure in {
        "CRYSTAL_FACE",
        "ROUND_CRYSTAL",
        "PLAQUE",
        "CERTIFICATE",
        "RESIN_PANEL",
        "SCULPTURAL",
        "IRREGULAR_CRYSTAL",
    }:
        objects = formal_layout(
            w,
            h,
            variant,
            compact=structure in {
                "ROUND_CRYSTAL",
                "SCULPTURAL",
                "IRREGULAR_CRYSTAL",
            },
        )

    else:
        objects = formal_layout(w, h, variant)

    return {
        "version": 1,
        "templateType": "editable-master",
        "reconstructed": True,
        "editable": True,

        "award_library": True,
        "award_library_version": VERSION,

        "award_code": (
            f"zv-award-v{VERSION}-"
            f"{product.id:04d}-{variant + 1:02d}"
        ),

        "award_product_id": product.id,
        "award_structure": structure,

        "physical": {
            "width_in": float(product.print_width_in or 0),
            "height_in": float(product.print_height_in or 0),
            "safe_margin_in": float(product.safe_margin_in or 0),
            "bleed_in": float(product.bleed_in or 0),
        },

        "canvas": {
            "width": w,
            "height": h,
        },

        "pages": [
            {
                "name": "Award",
                "label": "Award",
                "objects": objects,
            }
        ],
    }


TEMPLATE_NAMES = [
    "Classic Recognition",
    "Executive Excellence",
    "Modern Achievement",
    "Signature Honour",
]


class Command(BaseCommand):
    help = (
        "Generate fully editable Award templates for configured "
        "Zenvibe Award products."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--product-id",
            type=int,
            default=None,
            help="Generate templates for one Award product.",
        )

        parser.add_argument(
            "--templates-per-product",
            type=int,
            default=4,
            help="Number of editable layouts per Award product. Default 4.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and display output without changing database.",
        )

        parser.add_argument(
            "--replace-generated",
            action="store_true",
            help="Delete only previously generated Award library templates.",
        )

    def handle(self, *args, **options):
        product_id = options["product_id"]
        count_per_product = options["templates_per_product"]
        dry_run = options["dry_run"]
        replace_generated = options["replace_generated"]

        if count_per_product < 1 or count_per_product > 12:
            raise CommandError(
                "--templates-per-product must be between 1 and 12."
            )

        qs = (
            Product.objects
            .select_related("category")
            .filter(category__name__icontains="award")
            .exclude(id__in=EXCLUDED_PRODUCT_IDS)
            .order_by("id")
        )

        if product_id:
            qs = qs.filter(id=product_id)

        products = list(qs)

        if not products:
            raise CommandError("No Award products found.")

        total = 0

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"ZENVIBE EDITABLE AWARD TEMPLATES V{VERSION}"
            )
        )
        self.stdout.write("")

        with transaction.atomic():

            for product in products:
                structure = structure_for(product)

                if not product.print_width_in or not product.print_height_in:
                    raise CommandError(
                        f"Product #{product.id} {product.name} has no "
                        f"physical Award print-area dimensions. Run "
                        f"configure_awards_editable first."
                    )

                if replace_generated and not dry_run:
                    # Delete ONLY templates generated by this Awards command.
                    #
                    # Do not touch Business Cards, Flyers, Invitations,
                    # or manually created Award templates.
                    candidates = DesignTemplate.objects.filter(
                        product=product
                    )

                    delete_ids = []

                    for template in candidates:
                        data = template.json_data or {}

                        if (
                            isinstance(data, dict)
                            and data.get("award_library") is True
                        ):
                            delete_ids.append(template.id)

                    if delete_ids:
                        DesignTemplate.objects.filter(
                            id__in=delete_ids
                        ).delete()

                for variant in range(count_per_product):
                    data = build_template(
                        product,
                        structure,
                        variant,
                    )

                    name_base = TEMPLATE_NAMES[
                        variant % len(TEMPLATE_NAMES)
                    ]

                    template_name = (
                        f"ZV Award {variant + 1:02d} · "
                        f"{name_base} · {structure.replace('_', ' ').title()}"
                    )

                    # Basic safety validation.
                    pages = data.get("pages") or []

                    if len(pages) != 1:
                        raise CommandError(
                            f"Invalid page structure for product "
                            f"#{product.id}."
                        )

                    objects = pages[0].get("objects") or []

                    if not objects:
                        raise CommandError(
                            f"No editable objects generated for product "
                            f"#{product.id}."
                        )

                    for obj in objects:
                        if obj.get("selectable") is not True:
                            raise CommandError(
                                f"Non-selectable object generated for "
                                f"product #{product.id}: "
                                f"{obj.get('name')}"
                            )

                        if obj.get("locked") is not False:
                            raise CommandError(
                                f"Locked object generated for "
                                f"product #{product.id}: "
                                f"{obj.get('name')}"
                            )

                    w = data["canvas"]["width"]
                    h = data["canvas"]["height"]

                    self.stdout.write(
                        f"#{product.id:<4} "
                        f"{structure:<20} "
                        f"{variant + 1:02d} "
                        f"{w}x{h} "
                        f"objects={len(objects):<2} "
                        f"| {template_name}"
                    )

                    if not dry_run:
                        DesignTemplate.objects.create(
                            product=product,
                            name=template_name,
                            json_data=data,
                            is_active=True,
                        )

                    total += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"{'DRY RUN ' if dry_run else ''}"
                f"COMPLETE: {total} editable Award templates "
                f"{'validated' if dry_run else 'created'}."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Business Card templates were not modified."
            )
        )