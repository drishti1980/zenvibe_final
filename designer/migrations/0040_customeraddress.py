from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("designer", "0039_product_editor_reference_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerAddress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(default="Home", max_length=60)),
                ("full_name", models.CharField(max_length=160)),
                ("phone", models.CharField(blank=True, max_length=40)),
                ("company", models.CharField(blank=True, max_length=160)),
                ("address", models.CharField(max_length=255)),
                ("address_line_2", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(max_length=120)),
                ("province", models.CharField(choices=[("AB","Alberta"),("BC","British Columbia"),("MB","Manitoba"),("NB","New Brunswick"),("NL","Newfoundland and Labrador"),("NS","Nova Scotia"),("NT","Northwest Territories"),("NU","Nunavut"),("ON","Ontario"),("PE","Prince Edward Island"),("QC","Quebec"),("SK","Saskatchewan"),("YT","Yukon")],max_length=2)),
                ("postal_code", models.CharField(max_length=7)),
                ("country", models.CharField(default="CA", editable=False, max_length=2)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="zenvibe_addresses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["-is_default","-created_at"]},
        ),
    ]
