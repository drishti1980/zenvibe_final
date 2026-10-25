from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("designer", "0037_sitesettings")]

    operations = [
        migrations.AddField(
            model_name="product", name="editor_layout_mode",
            field=models.CharField(choices=[("legacy","Existing / legacy behaviour"),("full_canvas","Full canvas editable"),("print_area","Restricted print area")], default="legacy", max_length=20, help_text="Legacy preserves all existing template behaviour. New products can opt into full-canvas or restricted print-area mode."),
        ),
        migrations.AddField(model_name="product", name="workspace_width_in", field=models.DecimalField(blank=True, decimal_places=3, help_text="Outer editor workspace/ruler width in inches. Separate from printable width.", max_digits=8, null=True)),
        migrations.AddField(model_name="product", name="workspace_height_in", field=models.DecimalField(blank=True, decimal_places=3, help_text="Outer editor workspace/ruler height in inches. Separate from printable height.", max_digits=8, null=True)),
        migrations.AddField(model_name="product", name="constrain_to_print_area", field=models.BooleanField(default=False, help_text="Prevent customer-editable objects from leaving configured print areas.")),
        migrations.AddField(model_name="product", name="show_product_reference", field=models.BooleanField(default=False, help_text="Show the product/mockup as a locked reference layer in the universal editor.")),
        migrations.AddField(model_name="productprintsurface", name="workspace_width_in", field=models.DecimalField(blank=True, decimal_places=3, help_text="Optional outer ruler/workspace width for this surface. Falls back to the Product workspace.", max_digits=8, null=True)),
        migrations.AddField(model_name="productprintsurface", name="workspace_height_in", field=models.DecimalField(blank=True, decimal_places=3, help_text="Optional outer ruler/workspace height for this surface. Falls back to the Product workspace.", max_digits=8, null=True)),
        migrations.AddField(model_name="productprintarea", name="surface", field=models.ForeignKey(blank=True, help_text="Optional editor surface/page this print area belongs to.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="print_areas", to="designer.productprintsurface")),
        migrations.AddField(model_name="productprintarea", name="print_width_in", field=models.DecimalField(blank=True, decimal_places=3, help_text="Physical printable width of this area in inches.", max_digits=8, null=True)),
        migrations.AddField(model_name="productprintarea", name="print_height_in", field=models.DecimalField(blank=True, decimal_places=3, help_text="Physical printable height of this area in inches.", max_digits=8, null=True)),
    ]
