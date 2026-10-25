from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0049_store_email_microsoft_credentials")]
    operations = [
        migrations.AddField(
            model_name="discountcoupon",
            name="products",
            field=models.ManyToManyField(
                to="designer.product", related_name="discount_coupons",
                help_text="This code applies only to these products. Select at least one product.",
            ),
        ),
    ]
