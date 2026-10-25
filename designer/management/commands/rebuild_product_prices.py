from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Min, Max

from designer.models import Product


class Command(BaseCommand):
    help = (
        "Rebuild Product price/min_price/max_price from existing "
        "local ProductPriceTier records. No external website requests."
    )

    def handle(self, *args, **options):
        products = (
            Product.objects
            .filter(
                price_tiers__is_active=True,
                price_tiers__unit_price__isnull=False,
            )
            .distinct()
            .order_by("id")
        )

        self.stdout.write(
            f"PRODUCTS WITH LOCAL PRICE TIERS: {products.count()}"
        )

        updated = 0
        unchanged = 0
        skipped = 0

        with transaction.atomic():

            for product in products:

                tiers = (
                    product.price_tiers
                    .filter(
                        is_active=True,
                        unit_price__isnull=False,
                        unit_price__gt=0,
                    )
                    .order_by(
                        "variant__sort_order",
                        "min_quantity",
                        "id",
                    )
                )

                first_tier = tiers.first()

                if first_tier is None:
                    skipped += 1
                    continue

                values = tiers.aggregate(
                    minimum=Min("unit_price"),
                    maximum=Max("unit_price"),
                )

                new_price = first_tier.unit_price
                new_min = values["minimum"]
                new_max = values["maximum"]

                if (
                    new_price is None
                    or new_min is None
                    or new_max is None
                ):
                    skipped += 1
                    continue

                old_price = product.price
                old_min = product.min_price
                old_max = product.max_price

                if (
                    old_price == new_price
                    and old_min == new_min
                    and old_max == new_max
                ):
                    unchanged += 1
                    continue

                product.price = new_price
                product.min_price = new_min
                product.max_price = new_max

                product.save(
                    update_fields=[
                        "price",
                        "min_price",
                        "max_price",
                    ]
                )

                updated += 1

                self.stdout.write(
                    "{} | {} | "
                    "OLD: {} / {} - {} | "
                    "NEW: {} / {} - {}".format(
                        product.id,
                        product.name,
                        old_price,
                        old_min,
                        old_max,
                        new_price,
                        new_min,
                        new_max,
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "PRICE REBUILD COMPLETE"
            )
        )

        self.stdout.write(
            f"Updated: {updated}"
        )

        self.stdout.write(
            f"Unchanged: {unchanged}"
        )

        self.stdout.write(
            f"Skipped: {skipped}"
        )