from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0040_customeraddress")]

    operations = [
        migrations.CreateModel(
            name="StoreEmailAccount",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=20, choices=[("gmail", "Gmail / Google Workspace"), ("outlook", "Outlook / Microsoft 365")])),
                ("email_address", models.EmailField(max_length=254, unique=True)),
                ("is_active", models.BooleanField(default=False)),
                ("notify_on_order", models.BooleanField(default=True)),
                ("notify_on_contact", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Store email account", "verbose_name_plural": "Email configuration"},
        ),
        migrations.AddConstraint(
            model_name="storeemailaccount",
            constraint=models.UniqueConstraint(fields=["is_active"], condition=models.Q(is_active=True), name="zv_single_active_mailbox"),
        ),
    ]
