import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0015_designtemplate_timestamps")]  # NOTE: if your project has its own 0016 migration, run `python manage.py makemigrations` instead of using this file directly — Django will regenerate it correctly against your actual migration history.
    operations = [
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="product_angles/")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="angle_images", to="designer.product")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
    ]
