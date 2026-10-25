from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0022_alter_category_options_category_parent")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="customizer_mode",
            field=models.CharField(
                choices=[
                    ("auto", "Automatic"), ("photo", "Product photo studio"),
                    ("editor", "Layout editor"), ("tshirt", "Apparel studio"),
                    ("pen", "Pen studio"), ("drinkware", "Drinkware studio"),
                    ("awards", "Awards studio"), ("bags", "Bags studio"),
                ],
                default="auto",
                help_text="Choose a specific design studio, or leave Automatic for the existing product-based routing.",
                max_length=20,
            ),
        ),
        migrations.AddField(model_name="productimage", name="label", field=models.CharField(blank=True, help_text="Optional label such as Black, Front, Back or Side view.", max_length=120)),
        migrations.AddField(model_name="productimage", name="print_left_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
        migrations.AddField(model_name="productimage", name="print_top_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
        migrations.AddField(model_name="productimage", name="print_width_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
        migrations.AddField(model_name="productimage", name="print_height_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
    ]
