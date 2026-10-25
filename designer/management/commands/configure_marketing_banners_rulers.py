from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from designer.models import Product, ProductSizeVariant, ProductPrintSurface


def D(v):
    return Decimal(str(v))


# VERIFIED/APPROVED PHYSICAL PRINT DIMENSIONS IN INCHES.
# Keep dimensions here as DATA only. The editor must never hard-code them.
PRODUCTS = {
    # Marketing Materials
    1:   (3.75, 2.25),   # Premium Business Cards
    62:  (8.5, 11),      # Custom Flyers
    170: (4.5, 11),      # Custom Door Hangers

    # Banners & Displays
    233: (33, 81),       # Standard Base Roll Up Banner
    238: (24, 36),       # Sandwich Board - White
    199: (117, 80),      # Canopy Tent Full Back Wall - default 10x10
    391: (120, 120),     # 10x10 Canopy combo - page 1/top
    182: (240, 160),     # 10x20 Canopy combo - page 1/top
}

SIZE_VARIANTS = {
    62: [
        ("8.5 x 11", 8.5, 11),
    ],
    269: [  # Custom Mesh Banners
        ("2.5 x 4 FT", 30, 48),
        ("2.5 x 8 FT", 30, 96),
        ("2.5 x 10 FT", 30, 120),
        ("4 x 4 FT", 48, 48),
        ("4 x 8 FT", 48, 96),
        ("4 x 10 FT", 48, 120),
    ],
    433: [  # Custom Vinyl Banners
        ("2.5 x 4 FT", 30, 48),
        ("2.5 x 8 FT", 30, 96),
        ("2.5 x 10 FT", 30, 120),
        ("4 x 4 FT", 48, 48),
        ("4 x 8 FT", 48, 96),
        ("4 x 10 FT", 48, 120),
    ],
    319: [  # Tension Fabric Displays
        ("10 x 7.5 FT", 120, 90),
        ("10 x 8 FT", 120, 96),
        ("20 x 8 FT", 240, 96),
        ("6 x 9 FT", 72, 108),
    ],
    313: [  # Custom Table Runners
        ("2 x 7.5 FT", 24, 90),
        ("3 x 7.5 FT", 36, 90),
        ("4 x 7.5 FT", 48, 90),
    ],
    298: [  # Round Table Throws
        ("31.5 x 29 IN", 31.5, 29),
        ("31.5 x 43 IN", 31.5, 43),
    ],
    430: [  # Round Fitted Table Covers
        ("31.5 x 29 IN", 31.5, 29),
        ("31.5 x 43 IN", 31.5, 43),
    ],
    199: [
        ("10 x 10 FT", 117, 80),
        ("10 x 20 FT", 233, 80),
    ],
}

SURFACES = {
    199: [
        ("Inside Back Wall", 117, 80, 1),
        ("Outside Back Wall", 117, 80, 2),
    ],
    391: [
        ("Canopy Top", 120, 120, 1),
        ("Full Back Wall - Outside", 117, 80, 2),
        ("Full Back Wall - Inside", 117, 80, 3),
        ("Left Half Wall - Outside", 117, 38, 4),
        ("Left Half Wall - Inside", 117, 38, 5),
        ("Right Half Wall - Outside", 117, 38, 6),
        ("Right Half Wall - Inside", 117, 38, 7),
    ],
    182: [
        ("Canopy Tent Top", 240, 160, 1),
        ("Inside Back Wall", 233, 80, 2),
        ("Outside Back Wall", 233, 80, 3),
        ("Inside Right Side Wall", 118, 38, 4),
        ("Outside Right Side Wall", 118, 38, 5),
        ("Inside Left Side Wall", 118, 38, 6),
        ("Outside Left Side Wall", 118, 38, 7),
    ],
}


def set_first(obj, names, value):
    """Set the first field that exists. Makes the command tolerant of model naming."""
    for name in names:
        if hasattr(obj, name):
            setattr(obj, name, value)
            return name
    return None


def dimensions(obj, w, h):
    fw = set_first(obj, ("print_width_in", "physical_width_in", "printWidth"), D(w))
    fh = set_first(obj, ("print_height_in", "physical_height_in", "printHeight"), D(h))
    if not fw or not fh:
        raise RuntimeError(
            f"{obj.__class__.__name__} is missing print width/height fields. "
            "Expected print_width_in/print_height_in (or compatible aliases)."
        )


def variant_label(v):
    for name in ("label", "name", "size", "size_name", "display_name", "key", "size_key"):
        if hasattr(v, name):
            return str(getattr(v, name) or "").strip()
    return ""


def set_variant_label(v, label):
    for name in ("label", "name", "size", "size_name", "display_name", "key", "size_key"):
        if hasattr(v, name):
            setattr(v, name, label)
            return


class Command(BaseCommand):
    help = (
        "Configure Admin-driven physical ruler dimensions for verified Marketing "
        "Materials and Banners & Displays products. Does not hard-code editor JS."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show intended changes and roll the transaction back."
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        updated_products = updated_variants = updated_surfaces = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            "ZenVibe Admin ruler configuration (inches)"
        ))

        # Product-level fallback dimensions.
        for product_id, (w, h) in PRODUCTS.items():
            p = Product.objects.filter(pk=product_id).first()
            if not p:
                self.stdout.write(self.style.WARNING(f"SKIP product {product_id}: not found"))
                continue
            dimensions(p, w, h)
            p.save()
            updated_products += 1
            self.stdout.write(f"PRODUCT {p.id}: {p.name} -> {w} x {h} in")

        # Size-selectable products.
        # IMPORTANT: ProductSizeVariant has UNIQUE(product_id, size_key).
        # Therefore update existing rows by size_key/label instead of blindly creating.
        import re

        def norm_key(value):
            s = str(value or "").strip().lower()
            s = s.replace("×", "x").replace('"', " in").replace("'", " ft")
            s = re.sub(r"[^a-z0-9.]+", "-", s).strip("-")
            return s

        def candidate_keys(label):
            raw = str(label or "").strip()
            vals = {
                norm_key(raw),
                norm_key(raw.replace(" FT", "").replace(" ft", "")),
                norm_key(raw.replace(" IN", "").replace(" in", "")),
                norm_key(raw.replace(" x ", "x")),
            }
            return {v for v in vals if v}

        for product_id, rows in SIZE_VARIANTS.items():
            p = Product.objects.filter(pk=product_id).first()
            if not p:
                self.stdout.write(self.style.WARNING(
                    f"SKIP variants product {product_id}: not found"
                ))
                continue

            existing = list(ProductSizeVariant.objects.filter(product=p))

            for label, w, h in rows:
                wanted = candidate_keys(label)

                # 1) Exact visible-label match.
                target = next(
                    (v for v in existing
                     if variant_label(v).strip().lower() == label.strip().lower()),
                    None
                )

                # 2) Existing unique size_key match.
                if target is None:
                    target = next(
                        (v for v in existing
                         if norm_key(getattr(v, "size_key", "")) in wanted),
                        None
                    )

                # 3) Normalized label match (handles × vs x / FT / IN formatting).
                if target is None:
                    target = next(
                        (v for v in existing
                         if norm_key(variant_label(v)) in wanted),
                        None
                    )

                if target is None:
                    target = ProductSizeVariant(product=p)

                    # size_key is unique per product, so assign a deterministic
                    # non-conflicting key BEFORE save.
                    if hasattr(target, "size_key"):
                        base = norm_key(label) or f"size-{w}x{h}"
                        key = base
                        n = 2
                        while ProductSizeVariant.objects.filter(
                            product=p, size_key=key
                        ).exists():
                            key = f"{base}-{n}"
                            n += 1
                        target.size_key = key

                    set_variant_label(target, label)

                dimensions(target, w, h)

                if hasattr(target, "is_active"):
                    target.is_active = True

                target.save()

                if all(getattr(v, "pk", None) != target.pk for v in existing):
                    existing.append(target)

                updated_variants += 1
                self.stdout.write(
                    f"  SIZE {p.id}: {label} -> {w} x {h} in "
                    f"[key={getattr(target, 'size_key', '')}]"
                )

        # Multi-page / multi-surface products.
        # Surface order is Admin source of truth for page ruler selection.
        for product_id, rows in SURFACES.items():
            p = Product.objects.filter(pk=product_id).first()
            if not p:
                self.stdout.write(self.style.WARNING(f"SKIP surfaces product {product_id}: not found"))
                continue

            existing = list(ProductPrintSurface.objects.filter(product=p))
            for label, w, h, order in rows:
                target = next(
                    (s for s in existing if str(getattr(s, "label", "")).strip().lower() == label.lower()),
                    None
                )
                if target is None:
                    target = ProductPrintSurface(product=p, label=label)

                target.label = label
                dimensions(target, w, h)
                if hasattr(target, "sort_order"):
                    target.sort_order = order
                if hasattr(target, "is_active"):
                    target.is_active = True
                target.save()
                if target not in existing:
                    existing.append(target)

                updated_surfaces += 1
                self.stdout.write(f"  PAGE {order}: {label} -> {w} x {h} in")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Configured {updated_products} products, "
            f"{updated_variants} size rulers, {updated_surfaces} page/surface rulers."
        ))

        if dry:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY RUN: database changes rolled back."))
        else:
            self.stdout.write(self.style.SUCCESS(
                "DONE. Admin/database is now the ruler source of truth for these configured products."
            ))
