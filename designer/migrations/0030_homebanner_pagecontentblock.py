from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("designer", "0029_product_max_price_product_min_price_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeBanner",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=180)),
                ("subtitle", models.CharField(blank=True, max_length=255)),
                ("image", models.ImageField(upload_to="home/banners/")),
                ("mobile_image", models.ImageField(blank=True, null=True, upload_to="home/banners/mobile/")),
                ("button_text", models.CharField(blank=True, default="Shop Now", max_length=80)),
                ("button_url", models.CharField(blank=True, help_text="Use a site path such as /shop/ or a full https:// URL.", max_length=500)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Home page banner",
                "verbose_name_plural": "Home page banners",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="PageContentBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page", models.CharField(choices=[("home", "Home Page"), ("about", "About Us")], db_index=True, max_length=20)),
                ("section_key", models.SlugField(help_text="Stable section identifier, e.g. welcome, story, mission.", max_length=80)),
                ("heading", models.CharField(blank=True, max_length=200)),
                ("subheading", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="page-content/")),
                ("button_text", models.CharField(blank=True, max_length=80)),
                ("button_url", models.CharField(blank=True, max_length=500)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Page content block",
                "verbose_name_plural": "Page content blocks",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="pagecontentblock",
            constraint=models.UniqueConstraint(fields=("page", "section_key"), name="unique_page_content_section"),
        ),
    ]
