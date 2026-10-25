from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0013_merge_20260727_2257")]
    operations = [
        migrations.AddField(model_name="product", name="print_left_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, help_text="Left edge of the editable area, as % of photo width.")),
        migrations.AddField(model_name="product", name="print_top_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, help_text="Top edge of the editable area, as % of photo height.")),
        migrations.AddField(model_name="product", name="print_width_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, help_text="Width of the editable area, as % of photo width.")),
        migrations.AddField(model_name="product", name="print_height_pct", field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, help_text="Height of the editable area, as % of photo height.")),
    ]
