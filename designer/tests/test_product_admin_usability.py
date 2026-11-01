from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from designer.models import Category, Product


class ProductAdminUsabilityTests(TestCase):
    def test_product_form_renders_toolbar_and_separate_sections(self):
        user = get_user_model().objects.create_superuser('admin-ui', 'ui@example.com', 'password')
        self.client.force_login(user)
        category = Category.objects.create(name='Test', slug='admin-ui')
        product = Product.objects.create(name='Test product', category=category)
        response = self.client.get(reverse('admin:designer_product_change', args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        for text in ['id="zv-discard"', 'id="zv-discard-dialog"', 'Keep editing', 'Discard changes', 'id="zv-product-search"', 'Product information', 'Product variants — shapes', 'Product variants — materials', 'Delivery methods (per product)', 'max_quantity', 'Adding products — setup guide', 'Raw product metadata (usually leave unchanged)', 'Artwork and design guidelines']:
            with self.subTest(control=text):
                self.assertContains(response, text)
