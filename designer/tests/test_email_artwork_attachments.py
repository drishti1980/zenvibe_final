import base64
import io
from types import SimpleNamespace
from PIL import Image
from django.test import TestCase, override_settings
from django.core import mail
from designer.services.order_workflow import order_artwork_attachments
from designer.services.store_email import send_store_email


class ArtworkEmailTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_saved_artwork_png_and_pdf_are_attached(self):
        buffer = io.BytesIO()
        Image.new('RGB', (20, 20), 'red').save(buffer, 'PNG')
        order = SimpleNamespace(pk=17, design=SimpleNamespace(preview_png='data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()))
        attachments = order_artwork_attachments(order)
        self.assertEqual([a[2] for a in attachments], ['image/png', 'application/pdf'])
        self.assertTrue(attachments[1][1].startswith(b'%PDF'))
        send_store_email('Order artwork', '<p>Your artwork</p>', ['customer@example.com'], attachments=attachments)
        self.assertEqual(len(mail.outbox[0].attachments), 2)

    def test_no_preview_does_not_block_email(self):
        self.assertEqual(order_artwork_attachments(SimpleNamespace(design=None)), [])
