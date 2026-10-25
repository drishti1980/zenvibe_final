from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from designer.models import Product, DesignTemplate

CATEGORY_SLUG = "promotional-products"
BAD_IDS = {63, 64, 163, 164, 165, 166, 167, 252}
GENERATORS = {
    "zenvibe-promotional-editable-v1",
    "zenvibe-promotional-editable-v2",
    "zenvibe-promotional-luxury-v3",
    "zenvibe-promotional-luxury-v4",
}

CANONICAL = {
    "Custom Aluminum Bottle Opener | Promotional Logo Tool",
    "Custom Car Keychain with Logo | Personalized Automotive Keyring",
    "Custom Shopping Cart Coin Keychain with Logo | Trolley Token Keyring",
    "Custom Shape Metal Keychain with Logo | Personalized Premium Keyring",
    "Custom Full Color Lanyard with Logo | Personalized Event ID Holder",
    "Custom Shape Bottle Opener Keychain with Logo | Personalized Promotional Keyring",
    "Custom Car Freshener with Logo",
    "Custom 3D Printed Coasters with Logo",
    "Premium Heavy Duty Custom Keychain",
    "Custom Name Badge",
    "Custom Silicone Wristbands",
    "Custom Lanyard",
    "Custom Round Lapel Pin",
    "Custom Logo Golf Balls",
    "Compact Lightweight Umbrella – 36 Inch",
    "Custom Mouse Pads",
    "Custom Triangle Shape Promotional Fluorescent Highlighter Pen",
    "Custom Paper Wristbands – Personalized Event & Admission Wristbands",
    "Personalized Logo Golf Towel",
    "Custom Office Door Name Plate with Logo | Personalized Name & Title Sign",
}

class Command(BaseCommand):
    help = "Remove corrupted/legacy Promotional catalogue records from customer flow and purge obsolete generated promotional templates."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        bad = Product.objects.filter(pk__in=BAD_IDS)
        canonical = Product.objects.filter(
            category__slug=CATEGORY_SLUG,
            is_active=True,
            name__in=CANONICAL,
        ).exclude(pk__in=BAD_IDS)

        self.stdout.write("Legacy/corrupt records:")
        for p in bad.order_by("id"):
            self.stdout.write(f"  {p.id} — {p.name}")

        self.stdout.write("Canonical Promotional records:")
        for p in canonical.order_by("id"):
            self.stdout.write(f"  {p.id} — {p.name}")

        old = DesignTemplate.objects.filter(
            json_data__generator__in=GENERATORS
        ).filter(product__category__slug=CATEGORY_SLUG)
        self.stdout.write(f"Obsolete generated templates: {old.count()}")

        if opts["dry_run"]:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY RUN — no database changes made."))
            return

        # These IDs are known legacy/import artefacts. Do not rename them into real
        # products: that would retain wrong pricing/options/media. Remove them from
        # customer discovery/editor routing instead.
        changed = bad.update(is_active=False, is_out_of_stock=True)
        deleted, _ = old.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Done. Disabled {changed} legacy/corrupt records; deleted {deleted} obsolete template rows. "
            "Run configure_promotional_products_editor, then seed_promotional_product_templates."
        ))
