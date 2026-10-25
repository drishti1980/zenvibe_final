from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0041_storeemailaccount")]
    operations = [
        migrations.CreateModel(
            name="StoreEmailTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("event", models.CharField(max_length=40, unique=True, choices=[
                    ("order_customer", "Customer order confirmation"),
                    ("order_admin", "New order notification to staff"),
                    ("order_status", "Customer order status update"),
                    ("contact_admin", "Contact Us notification to staff"),
                ])),
                ("subject", models.CharField(max_length=250)),
                ("body", models.TextField()),
                ("enabled", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "Store email template", "verbose_name_plural": "Email templates"},
        ),
    ]
