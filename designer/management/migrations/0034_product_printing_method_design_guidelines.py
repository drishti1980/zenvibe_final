from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("designer", "0033_brandlogo_testimonial_alter_pagecontentblock_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="printing_method",
            field=models.TextField(blank=True, help_text="Product-specific printing/decorating method. Leave blank to hide the Printing Method tab."),
        ),
        migrations.AddField(
            model_name="product",
            name="design_guidelines",
            field=models.TextField(blank=True, help_text="Product-specific artwork/design guidelines. Leave blank to hide the Design Guidelines tab."),
        ),
    ]
