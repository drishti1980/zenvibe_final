from django.db import migrations, models


COPY = [
    ('new', 'New', 'We received your order', 'Thank you for choosing ZenVibe. We have received your custom order. Our team will review your order details and artwork, and contact you if anything needs clarification.'),
    ('confirmed', 'Confirmed', 'Your order is confirmed', 'Your order has been confirmed. We will let you know when it moves into production.'),
    ('in_production', 'In production', 'Your order is in production', 'Our team is now preparing your custom products. We will send another update when your order ships.'),
    ('shipped', 'Shipped', 'Your order has shipped', 'Your order has been dispatched. If tracking is available, our team will share the delivery details separately.'),
    ('completed', 'Completed', 'Your order is complete', 'Your order has been marked complete. Thank you for creating with ZenVibe. If you need help with your order, please contact our team and quote your order number.'),
    ('cancelled', 'Cancelled', 'Your order has been cancelled', 'Your order has been cancelled. If you have questions about this cancellation or any applicable refund, please contact our team and quote your order number.'),
]


def seed(apps, schema_editor):
    Template = apps.get_model('designer', 'StoreEmailTemplate')
    for status, label, title, message in COPY:
        body = ('<div style="max-width:640px;margin:auto;font-family:Arial,sans-serif;color:#24364d">'
                '<div style="background:#0d3057;color:#ffffff;padding:24px;font-size:24px">ZenVibe Corporate Gifts</div>'
                '<div style="padding:24px"><h2>' + title + '</h2><p>Hello {customer_name},</p><p>' + message + '</p>'
                '<div style="background:#f3f6fa;padding:18px"><strong>Order:</strong> {order_number}<br>'
                '<strong>Status:</strong> {status}<br><strong>Product:</strong> {product_name}<br>'
                '<strong>Quantity:</strong> {quantity}<br><strong>Total:</strong> CAD ${total}</div>'
                '<p>Kind regards,<br>The ZenVibe Team</p></div></div>')
        Template.objects.get_or_create(event='order_status_' + status, defaults={
            'subject': 'ZenVibe — ' + title + ' | {order_number}', 'body': body, 'enabled': True})


class Migration(migrations.Migration):
    dependencies = [('designer', '0052_product_is_exclusive')]
    operations = [
        migrations.AlterField(model_name='storeemailtemplate', name='event',
            field=models.CharField(max_length=40, unique=True, choices=[
                ('order_customer', 'Customer order confirmation'),
                ('order_admin', 'New order notification to staff'),
                ('order_status', 'Customer order status update (fallback)'),
                *[('order_status_' + status, 'Order status: ' + label) for status, label, _, _ in COPY],
                ('contact_admin', 'Contact Us notification to staff'),
            ])),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
