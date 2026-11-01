from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('designer', '0051_product_price_tier_max_quantity')]
    operations = [
        migrations.AddField(
            model_name='product', name='is_exclusive',
            field=models.BooleanField(default=False, db_index=True,
                help_text='Show an Exclusive badge on this product on the website.'),
        ),
    ]
