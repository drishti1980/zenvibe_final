from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("designer", "0045_contact_category_template")]
    operations = [
        migrations.CreateModel(name="DiscountCoupon", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False)),
            ("code", models.CharField(max_length=50, unique=True)),
            ("title", models.CharField(max_length=100)),
            ("discount_type", models.CharField(max_length=10, choices=[("percent", "Percentage"), ("fixed", "Fixed CAD amount")], default="percent")),
            ("value", models.DecimalField(max_digits=10, decimal_places=2)),
            ("minimum_subtotal", models.DecimalField(max_digits=12, decimal_places=2, default=0)),
            ("starts_at", models.DateTimeField(null=True, blank=True)),
            ("expires_at", models.DateTimeField(null=True, blank=True)),
            ("is_active", models.BooleanField(default=True)),
            ("show_at_checkout", models.BooleanField(default=True)),
        ], options={"ordering": ["title", "code"]}),
        migrations.AddField(model_name="order", name="coupon_code", field=models.CharField(max_length=50, blank=True)),
        migrations.AddField(model_name="order", name="discount_amount", field=models.DecimalField(max_digits=12, decimal_places=2, default=0)),
    ]
