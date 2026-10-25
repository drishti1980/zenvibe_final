from collections import Counter
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from designer.models import Product, ProductPrintSurface, ProductSizeVariant, DesignTemplate


WIDTH_FIELDS = ("print_width_in", "physical_width_in", "printWidth")
HEIGHT_FIELDS = ("print_height_in", "physical_height_in", "printHeight")


def positive(value):
    try:
        n = Decimal(str(value))
        return n if n > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def read_dimensions(obj):
    if obj is None:
        return (None, None)
    w = h = None
    for name in WIDTH_FIELDS:
        if hasattr(obj, name):
            w = positive(getattr(obj, name, None))
            if w:
                break
    for name in HEIGHT_FIELDS:
        if hasattr(obj, name):
            h = positive(getattr(obj, name, None))
            if h:
                break
    return (w, h)


def write_dimensions(obj, w, h):
    wf = hf = None
    for name in WIDTH_FIELDS:
        if hasattr(obj, name):
            setattr(obj, name, w)
            wf = name
            break
    for name in HEIGHT_FIELDS:
        if hasattr(obj, name):
            setattr(obj, name, h)
            hf = name
            break
    if not wf or not hf:
        raise RuntimeError(
            f"{obj.__class__.__name__} does not expose Admin print width/height fields."
        )
    return wf, hf


def physical_from_dict(value):
    if not isinstance(value, dict):
        return None
    w = positive(
        value.get("widthIn", value.get("width_in", value.get("width")))
    )
    h = positive(
        value.get("heightIn", value.get("height_in", value.get("height")))
    )
    return (w, h) if w and h else None


def template_pages(data):
    """Return [(label, width, height), ...] only when template metadata is explicit.

    We intentionally do NOT use template pixel width/height and do not parse product
    names. Physical inches must already exist in template metadata.
    """
    if not isinstance(data, dict):
        return []

    pages = data.get("adminPages") or data.get("pages")
    if isinstance(pages, list) and pages:
        out = []
        for i, page in enumerate(pages):
            if not isinstance(page, dict):
                return []
            dims = physical_from_dict(page.get("physical"))
            if not dims:
                return []
            label = str(page.get("name") or page.get("label") or f"Page {i+1}").strip()
            out.append((label, dims[0], dims[1]))
        return out

    doc = data.get("document")
    if isinstance(doc, dict):
        dims = physical_from_dict(doc.get("physical"))
        if dims:
            return [("Print Area", dims[0], dims[1])]

    dims = physical_from_dict(data.get("physical"))
    if dims:
        return [("Print Area", dims[0], dims[1])]

    return []


def signature(rows):
    return tuple(
        (str(label).strip().lower(), str(w.normalize()), str(h.normalize()))
        for label, w, h in rows
    )


class Command(BaseCommand):
    help = (
        "Configure/audit Admin-driven inch rulers for every product without hard-coded "
        "category dimensions. Existing Admin surfaces/size variants win. Missing values "
        "are recovered only from explicit, consistent physical metadata already stored in "
        "templates. Product.width/Product.height are NEVER treated as inches."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Persist changes. Without this flag the command is a dry-run audit."
        )
        parser.add_argument(
            "--include-inactive", action="store_true",
            help="Also audit/configure inactive products."
        )
        parser.add_argument(
            "--product-id", type=int,
            help="Restrict to one product while testing."
        )
        parser.add_argument(
            "--no-single-surface", action="store_true",
            help="Do not create a one-page ProductPrintSurface from valid product-level inches."
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        apply = bool(opts["apply"])
        qs = Product.objects.all().order_by("id")
        if not opts["include_inactive"] and hasattr(Product, "is_active"):
            qs = qs.filter(is_active=True)
        if opts.get("product_id"):
            qs = qs.filter(pk=opts["product_id"])

        total = configured = already = unresolved = conflicts = 0
        self.stdout.write(self.style.MIGRATE_HEADING(
            "ZenVibe Admin ruler audit/configuration — inches"
        ))
        self.stdout.write(
            "Priority: existing Admin surfaces -> Admin size variants -> product Admin inches "
            "-> consistent template physical metadata. No pixel-size guessing."
        )

        for product in qs.iterator():
            total += 1
            changed = False

            surfaces = list(
                ProductPrintSurface.objects.filter(product=product, is_active=True)
                .order_by("sort_order", "id")
            )
            valid_surfaces = []
            for surf in surfaces:
                w, h = read_dimensions(surf)
                if w and h:
                    valid_surfaces.append((surf, w, h))

            variants = list(
                ProductSizeVariant.objects.filter(product=product, is_active=True)
                .order_by("sort_order", "id")
            )
            valid_variants = []
            for variant in variants:
                w, h = read_dimensions(variant)
                if w and h:
                    valid_variants.append((variant, w, h))

            pw, ph = read_dimensions(product)

            # 1. Existing valid Admin print surfaces are authoritative.
            if valid_surfaces:
                if (not pw or not ph) and valid_surfaces:
                    _, w, h = valid_surfaces[0]
                    write_dimensions(product, w, h)
                    product.save()
                    changed = True
                status = "UPDATED" if changed else "OK"
                self.stdout.write(
                    f"{status} {product.id}: {product.name} — "
                    f"{len(valid_surfaces)} Admin surface ruler(s)"
                )
                configured += int(changed)
                already += int(not changed)
                continue

            # 2. Existing Admin size variants are authoritative for size-selectable products.
            if valid_variants:
                if not pw or not ph:
                    _, w, h = valid_variants[0]
                    write_dimensions(product, w, h)
                    product.save()
                    changed = True
                self.stdout.write(
                    f"{'UPDATED' if changed else 'OK'} {product.id}: {product.name} — "
                    f"{len(valid_variants)} Admin size ruler(s)"
                )
                configured += int(changed)
                already += int(not changed)
                continue

            # 3. Existing product-level Admin inches: optionally create a one-page surface.
            if pw and ph:
                if not opts["no_single_surface"]:
                    ProductPrintSurface.objects.update_or_create(
                        product=product,
                        label="Print Area",
                        defaults={
                            "print_width_in": pw,
                            "print_height_in": ph,
                            "sort_order": 1,
                            "is_active": True,
                        },
                    )
                    changed = True
                self.stdout.write(
                    f"{'UPDATED' if changed else 'OK'} {product.id}: {product.name} — "
                    f"{pw} x {ph} in"
                )
                configured += int(changed)
                already += int(not changed)
                continue

            # 4. Recover only from explicit physical metadata stored in active templates.
            candidates = []
            template_qs = DesignTemplate.objects.filter(product=product, is_active=True)
            for tpl in template_qs.only("id", "name", "json_data"):
                rows = template_pages(tpl.json_data or {})
                if rows:
                    candidates.append(rows)

            if candidates:
                counts = Counter(signature(rows) for rows in candidates)
                best_sig, best_count = counts.most_common(1)[0]

                # Require all templates that contain physical metadata to agree.
                if len(counts) != 1:
                    conflicts += 1
                    self.stdout.write(self.style.WARNING(
                        f"CONFLICT {product.id}: {product.name} — "
                        f"{len(counts)} different template physical configurations; unchanged."
                    ))
                    continue

                rows = candidates[0]
                ProductPrintSurface.objects.filter(product=product).update(is_active=False)
                for order, (label, w, h) in enumerate(rows, 1):
                    ProductPrintSurface.objects.update_or_create(
                        product=product,
                        label=label,
                        defaults={
                            "print_width_in": w,
                            "print_height_in": h,
                            "sort_order": order,
                            "is_active": True,
                        },
                    )
                write_dimensions(product, rows[0][1], rows[0][2])
                product.save()
                changed = True
                configured += 1
                self.stdout.write(self.style.SUCCESS(
                    f"RECOVERED {product.id}: {product.name} — "
                    f"{len(rows)} page ruler(s) from consistent template physical metadata."
                ))
                continue

            unresolved += 1
            self.stdout.write(self.style.WARNING(
                f"UNRESOLVED {product.id}: {product.name} — "
                "no Admin inches and no trustworthy template physical metadata. "
                "No dimensions were guessed."
            ))

        if not apply:
            transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Products checked: {total} | changed/recovered: {configured} | "
            f"already configured: {already} | conflicts: {conflicts} | unresolved: {unresolved}"
        ))
        if apply:
            self.stdout.write(self.style.SUCCESS(
                "APPLIED. Django Admin/database remains the ruler source of truth."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "DRY RUN ONLY. Run again with --apply after reviewing the output."
            ))
