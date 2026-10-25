from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("designer", "0018_alter_designtemplate_created_at_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_number", models.CharField(blank=True, max_length=24, unique=True)),
                ("customer_name", models.CharField(max_length=160)), ("customer_email", models.EmailField(max_length=254)),
                ("customer_phone", models.CharField(blank=True, max_length=40)), ("company", models.CharField(blank=True, max_length=160)),
                ("address", models.CharField(max_length=255)), ("city", models.CharField(max_length=120)), ("province", models.CharField(max_length=120)),
                ("postal_code", models.CharField(max_length=20)), ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=10)), ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("new","New"),("confirmed","Confirmed"),("in_production","In production"),("shipped","Shipped"),("completed","Completed"),("cancelled","Cancelled")], db_index=True, default="new", max_length=30)),
                ("customer_notes", models.TextField(blank=True)), ("admin_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("design", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="designer.saveddesign")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="zenvibe_orders", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering":["-created_at"]},
        )
    ]
