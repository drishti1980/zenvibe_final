from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("designer", "0046_discount_coupon")]
    operations = [
        migrations.CreateModel(
            name="PaymentSetup",
            fields=[],
            options={"proxy": True, "verbose_name": "Payment setup", "verbose_name_plural": "Payment setup"},
            bases=("designer.orderworkflowconfig",),
        ),
    ]
