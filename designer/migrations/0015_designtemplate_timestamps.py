import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0014_product_print_area")]
    operations = [
        migrations.AddField(model_name="designtemplate", name="created_at", field=models.DateTimeField(auto_now_add=True, null=True, default=django.utils.timezone.now)),
        migrations.AddField(model_name="designtemplate", name="updated_at", field=models.DateTimeField(auto_now=True, null=True)),
    ]
