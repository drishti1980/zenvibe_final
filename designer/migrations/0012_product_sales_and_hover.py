from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("designer", "0011_update_awards_real_products")]
    operations = [
        migrations.AddField(model_name="product", name="hover_image", field=models.ImageField(blank=True, help_text="Optional alternate image shown on hover.", null=True, upload_to="products/hover/")),
        migrations.AddField(model_name="product", name="is_on_sale", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="product", name="sale_price", field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
        migrations.AddField(model_name="product", name="sale_badge", field=models.CharField(blank=True, default="Sale!", max_length=40)),
        migrations.AddField(model_name="product", name="sale_priority", field=models.PositiveIntegerField(default=100)),
    ]
