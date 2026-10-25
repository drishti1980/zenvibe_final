from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("designer", "0038_admin_driven_editor_geometry"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="editor_reference_image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="products/editor_reference/",
                help_text="Clean/blank product image used only as the locked reference in restricted print-area editor mode. Do not upload a promotional image with sample artwork baked in.",
            ),
        ),
    ]
