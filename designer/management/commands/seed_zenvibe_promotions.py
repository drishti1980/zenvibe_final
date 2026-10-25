"""Seed confirmed promotions advertised by zenvibe.ca without touching other coupons."""
from decimal import Decimal

from django.core.management.base import BaseCommand
from designer.models import DiscountCoupon


class Command(BaseCommand):
    help = "Create the WELCOME10 promotion advertised on zenvibe.ca (idempotent)."

    def handle(self, *args, **options):
        coupon, created = DiscountCoupon.objects.get_or_create(
            code="WELCOME10",
            defaults={
                "title": "Welcome offer — 10% off",
                "discount_type": "percent",
                "value": Decimal("10.00"),
                "minimum_subtotal": Decimal("0.00"),
                "is_active": True,
                "show_at_checkout": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created WELCOME10 (10% off)."))
        else:
            self.stdout.write(self.style.WARNING(
                "WELCOME10 already exists; preserved admin settings. "
                "Check Active, Show at checkout and validity dates in admin."
            ))
