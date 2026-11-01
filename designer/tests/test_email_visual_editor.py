from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from designer.models import StoreEmailTemplate


class EmailVisualEditorTests(TestCase):
    def test_visual_editor_assets_and_upload_validation(self):
        user = get_user_model().objects.create_superuser('email-editor', 'admin@example.com', 'password')
        self.client.force_login(user)
        template = StoreEmailTemplate.objects.get(event='order_status_new')
        response = self.client.get(reverse('admin:designer_storeemailtemplate_change', args=[template.pk]))
        self.assertContains(response, 'designer/admin/email-editor.js')
        self.assertContains(response, 'Email design')
        self.assertContains(response, 'data-upload-url=')
        response = self.client.post(reverse('admin:designer_email_image_upload'))
        self.assertEqual(response.status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.post(reverse('admin:designer_email_image_upload')).status_code, 302)
