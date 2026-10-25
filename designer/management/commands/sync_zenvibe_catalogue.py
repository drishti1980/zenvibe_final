import csv
import re

from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from designer.models import Category, Product


MONEY_RE = re.compile(r"\$[\s]*([0-9,]+(?:\.[0-9]{1,2})?)")


def money(value):
    return Decimal(value.replace(",", "").strip())


def parse_displayed_price(text):
    text = (text or "").strip()
    values = [money(x) for x in MONEY_RE.findall(text)]

    if not values:
        return {
            "price": None,
            "min_price": None,
            "max_price": None,
            "is_on_sale": False,
            "sale_price": None,
        }

    if "was" in text.lower() and len(values) >= 2:
        current, regular = values[0], values[1]
        return {
            "price": regular,
            "min_price": current,
            "max_price": current,
            "is_on_sale": True,
            "sale_price": current,
        }

    lo = min(values)
    hi = max(values)

    return {
        "price": lo,
        "min_price": lo,
        "max_price": hi if len(values) > 1 else lo,
        "is_on_sale": False,
        "sale_price": None,
    }


def normalise(text):
    text = (text or "").strip().lower()
    text = (
        text.replace("×", "x")
        .replace("’", "'")
        .replace("–", "-")
        .replace("—", "-")
    )
    return re.sub(r"[^a-z0-9]+", "", text)


def unique_category_slug(name, parent=None, exclude_pk=None):
    base_slug = slugify(name) or "category"
    candidate = base_slug
    suffix = 2

    while True:
        qs = Category.objects.filter(parent=parent, slug=candidate)

        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)

        if not qs.exists():
            return candidate

        candidate = f"{base_slug}-{suffix}"
        suffix += 1


def get_existing_or_create_category(name, parent=None):
    name = (name or "").strip()

    matches = Category.objects.filter(
        parent=parent,
        name__iexact=name,
    ).order_by("-is_active", "id")

    category = matches.first()

    if category:
        changed = False

        if not category.is_active:
            category.is_active = True
            changed = True

        if category.is_out_of_stock:
            category.is_out_of_stock = False
            changed = True

        if not category.slug:
            category.slug = unique_category_slug(
                name,
                parent=parent,
                exclude_pk=category.pk,
            )
            changed = True

        if changed:
            category.save()

        return category, False

    category = Category.objects.create(
        parent=parent,
        name=name,
        slug=unique_category_slug(name, parent=parent),
        is_active=True,
        is_out_of_stock=False,
    )

    return category, True


def unique_product_slug(product, category, product_name):
    base_slug = slugify(product_name) or "product"
    candidate = base_slug
    suffix = 2

    while True:
        qs = Product.objects.filter(
            category=category,
            slug=candidate,
        )

        if product.pk:
            qs = qs.exclude(pk=product.pk)

        if not qs.exists():
            return candidate

        candidate = f"{base_slug}-{suffix}"
        suffix += 1


class Command(BaseCommand):
    help = (
        "Sync ZenVibe catalogue/categories/prices from the bundled local CSV. "
        "No live website requests are made."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            default="",
            help="Optional path to another catalogue CSV with the same columns.",
        )
        parser.add_argument(
            "--deactivate-extra",
            action="store_true",
            help="Deactivate products that are not present in the supplied catalogue.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change and roll the transaction back.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        if csv_path:
            path = Path(csv_path)
        else:
            path = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "zenvibe_product_catalogue.csv"
            )

        if not path.exists():
            self.stderr.write(
                self.style.ERROR(f"Catalogue file not found: {path}")
            )
            return

        self.stdout.write(f"Using local catalogue: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))

        self.stdout.write(f"Catalogue rows loaded: {len(rows)}")

        expected_ids = set()
        created = 0
        updated = 0
        categories_created = 0

        existing_products = list(
            Product.objects.select_related("category").all()
        )

        by_name = {}

        for existing_product in existing_products:
            key = normalise(existing_product.name)
            by_name.setdefault(key, []).append(existing_product)

        for row_number, row in enumerate(rows, start=2):
            parent_name = (row.get("Category") or "").strip()
            sub_name = (row.get("Subcategory") or "").strip()
            product_name = (row.get("Product") or "").strip()
            display_price = (row.get("Displayed Price (CAD)") or "").strip()
            source_url = (row.get("Source URL") or "").strip()

            if not parent_name or not product_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping row {row_number}: missing category/product."
                    )
                )
                continue

            parent, parent_created = get_existing_or_create_category(
                parent_name,
                parent=None,
            )

            if parent_created:
                categories_created += 1

            category = parent

            if (
                sub_name
                and normalise(sub_name)
                not in {"", normalise(parent_name)}
            ):
                category, sub_created = get_existing_or_create_category(
                    sub_name,
                    parent=parent,
                )

                if sub_created:
                    categories_created += 1

            key = normalise(product_name)
            candidates = by_name.get(key, [])

            product = next(
                (
                    p
                    for p in candidates
                    if p.category_id == category.id
                ),
                None,
            )

            if product is None and len(candidates) == 1:
                product = candidates[0]

                if product.category_id != category.id:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Re-mapping product ID {product.id}: "
                            f"{product_name} -> {category}"
                        )
                    )

                product.category = category

            elif product is None and len(candidates) > 1:
                active_candidates = [
                    p for p in candidates if p.is_active
                ]

                pool = active_candidates or candidates
                product = sorted(pool, key=lambda p: p.id)[0]

                self.stdout.write(
                    self.style.WARNING(
                        f"Duplicate product name found: {product_name}. "
                        f"Using existing product ID {product.id}."
                    )
                )

                product.category = category

            price_data = parse_displayed_price(display_price)

            if product is None:
                product = Product(
                    category=category,
                    name=product_name,
                    slug="",
                    is_active=True,
                    is_out_of_stock=False,
                )
                created += 1
            else:
                updated += 1

            product.name = product_name
            product.category = category
            product.is_active = True
            product.is_out_of_stock = False

            if hasattr(product, "source_url") and source_url:
                product.source_url = source_url

            for field, value in price_data.items():
                if not hasattr(product, field):
                    continue

                if field == "is_on_sale":
                    setattr(product, field, bool(value))
                elif field == "sale_price":
                    setattr(product, field, value)
                elif value is not None:
                    setattr(product, field, value)

            product.slug = unique_product_slug(
                product,
                category,
                product_name,
            )

            product.save()

            expected_ids.add(product.id)

            by_name.setdefault(key, [])
            if product not in by_name[key]:
                by_name[key].append(product)

        deactivated = 0

        if options["deactivate_extra"]:
            qs = (
                Product.objects
                .exclude(id__in=expected_ids)
                .filter(is_active=True)
            )
            deactivated = qs.update(is_active=False)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Catalogue sync complete"))
        self.stdout.write(f"Products created: {created}")
        self.stdout.write(f"Products updated: {updated}")
        self.stdout.write(f"Categories created: {categories_created}")
        self.stdout.write(f"Extra products deactivated: {deactivated}")
        self.stdout.write(
            f"Catalogue product IDs matched: {len(expected_ids)}"
        )
        self.stdout.write("No live ZenVibe website polling was used.")

        if options["dry_run"]:
            transaction.set_rollback(True)
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN ONLY - all database changes were rolled back."
                )
            )
