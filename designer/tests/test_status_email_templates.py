from types import SimpleNamespace
from unittest.mock import patch
from django.test import TestCase
from designer.models import StoreEmailTemplate
from designer.services.order_workflow import send_status_email


class StatusEmailTemplatesTests(TestCase):
    @patch('designer.services.order_workflow._notify')
    @patch('designer.services.order_workflow.workflow')
    def test_each_status_uses_its_own_template_and_can_be_disabled(self, workflow, notify):
        workflow.return_value = SimpleNamespace(email_customer_on_status_change=True)
        for status in ['new', 'confirmed', 'in_production', 'shipped', 'completed', 'cancelled']:
            with self.subTest(status=status):
                row = StoreEmailTemplate.objects.get(event='order_status_' + status)
                order = SimpleNamespace(status=status, customer_name='Customer', customer_email='test@example.com', order_number='ZV123', design=None, quantity=2, total='20.00', get_status_display=lambda: status)
                notify.reset_mock()
                send_status_email(order, 'new')
                self.assertEqual(notify.call_count, 1)
                self.assertIn('ZV123', notify.call_args.args[0])
                row.enabled = False
                row.save()
                notify.reset_mock()
                send_status_email(order, 'new')
                notify.assert_not_called()
