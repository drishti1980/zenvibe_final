from django.test import TestCase
from designer.models import Product, Category
from designer.admin import ProductAdmin


class ProductExclusiveTests(TestCase):
    def test_badge_is_opt_in_and_persists(self):
        category = Category.objects.create(name='Test', slug='exclusive-test')
        product = Product.objects.create(name='Exclusive test', category=category)
        self.assertFalse(product.is_exclusive)
        product.is_exclusive = True
        product.save(update_fields=['is_exclusive'])
        product.refresh_from_db()
        self.assertTrue(product.is_exclusive)
        fields = [field for _, options in ProductAdmin.fieldsets for field in options['fields']]
        self.assertIn('is_exclusive', fields)

    def test_home_badges_follow_product_setting(self):
        from pathlib import Path
        from django.conf import settings
        source = (Path(settings.BASE_DIR) / 'templates/designer/home.html').read_text()
        self.assertNotIn('if forloop.counter <= 2', source)
        self.assertNotIn('if product.is_featured', source)
        self.assertIn('if product.is_exclusive', source)
