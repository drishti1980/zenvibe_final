from django.db import migrations


DEFAULTS = [
    ("order_customer", "ZenVibe order received - {order_number}",
     "<h2>Thank you for your order, {customer_name}!</h2><p>We've received your customised order <strong>{order_number}</strong>.</p><p><strong>Product:</strong> {product_name}<br><strong>Quantity:</strong> {quantity}<br><strong>Total:</strong> ${total}<br><strong>Status:</strong> {status}</p><p>We'll email you as your order progresses.</p><p>Kind regards,<br><strong>ZenVibe Corporate Gifts</strong></p>"),
    ("order_admin", "New ZenVibe order - {order_number}",
     "<h2>New order: {order_number}</h2><p><strong>Customer:</strong> {customer_name} ({customer_email})</p><p><strong>Product:</strong> {product_name}<br><strong>Quantity:</strong> {quantity}<br><strong>Total:</strong> ${total}<br><strong>Status:</strong> {status}</p><p>Open ZenVibe Admin to review the order and customised artwork.</p>"),
    ("order_status", "ZenVibe order update - {order_number}",
     "<h2>Order update</h2><p>Hi {customer_name},</p><p>Your order <strong>{order_number}</strong> has changed from {old_status} to <strong>{status}</strong>.</p><p>Thank you,<br>ZenVibe Corporate Gifts</p>"),
    ("contact_admin", "ZenVibe enquiry: {subject}",
     "<h2>New website enquiry</h2><p><strong>From:</strong> {customer_name} ({customer_email})<br><strong>Phone:</strong> {phone}<br><strong>Subject:</strong> {subject}</p><p>{message}</p><p>Reply to this message to contact the customer.</p>"),
]


def seed_defaults(apps, schema_editor):
    Template = apps.get_model("designer", "StoreEmailTemplate")
    for event, subject, body in DEFAULTS:
        Template.objects.get_or_create(event=event, defaults={"subject": subject, "body": body, "enabled": True})


class Migration(migrations.Migration):
    dependencies = [("designer", "0042_storeemailtemplate")]
    operations = [migrations.RunPython(seed_defaults, migrations.RunPython.noop)]
