from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("designer", "0005_product_orientation"),
    ]

    operations = [
        migrations.AddField(model_name="product", name="bleed_mm", field=models.DecimalField(decimal_places=2, default=3, max_digits=5)),
        migrations.AddField(model_name="product", name="safe_margin_mm", field=models.DecimalField(decimal_places=2, default=5, max_digits=5)),
        migrations.AddField(model_name="product", name="min_dpi", field=models.PositiveIntegerField(default=150)),
        migrations.AddField(model_name="saveddesign", name="is_autosave", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="saveddesign", name="session_key", field=models.CharField(blank=True, db_index=True, max_length=40)),
        migrations.AddField(model_name="saveddesign", name="status", field=models.CharField(choices=[("draft", "Draft"), ("cart", "In cart"), ("ordered", "Ordered")], default="draft", max_length=20)),
        migrations.AddField(model_name="saveddesign", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name="saveddesign", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="zenvibe_designs", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="saveddesign", name="version", field=models.PositiveIntegerField(default=1)),
        migrations.CreateModel(
            name="DesignVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("design_json", models.JSONField(default=dict)),
                ("preview_png", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("design", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="designer.saveddesign")),
            ],
            options={"ordering": ["-version"], "unique_together": {("design", "version")}},
        ),
        migrations.AlterModelOptions(name="saveddesign", options={"ordering": ["-updated_at"]}),
    ]
