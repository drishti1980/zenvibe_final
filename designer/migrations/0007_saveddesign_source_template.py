from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("designer", "0006_advanced_editor")]
    operations = [
        migrations.AddField(
            model_name="saveddesign",
            name="source_template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="customer_designs",
                to="designer.designtemplate",
            ),
        ),
    ]
