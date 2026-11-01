from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from designer.models import Category, Product, ProductPriceTier
from designer.views import _product_unit_price


class PriceTierRangeTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Test", slug="test")
        self.product = Product.objects.create(category=category, name="Trophy", price="20.00")
        for lower, upper, price in [(20, 49, "15.99"), (50, 99, "14.50"), (100, None, "12.99")]:
            ProductPriceTier.objects.create(product=self.product, min_quantity=lower, max_quantity=upper, unit_price=price)

    def test_inclusive_boundaries(self):
        for quantity, price in [(20, "15.99"), (49, "15.99"), (50, "14.50"), (99, "14.50"), (100, "12.99"), (1000, "12.99")]:
            with self.subTest(quantity=quantity):
                self.assertEqual(_product_unit_price(self.product, quantity), Decimal(price))

    def test_expired_tier_not_used_in_gap(self):
        self.product.price_tiers.filter(min_quantity=50).delete()
        self.assertEqual(_product_unit_price(self.product, 70), Decimal("20.00"))

    def test_invalid_range_rejected(self):
        tier = ProductPriceTier(product=self.product, min_quantity=20, max_quantity=19, unit_price="1.00")
        with self.assertRaises(ValidationError):
            tier.full_clean()
