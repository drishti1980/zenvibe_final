from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("designer", "0030_homebanner_pagecontentblock")]
    operations = [
        migrations.AddField(model_name="product", name="short_description", field=models.TextField(blank=True, help_text="Short product summary shown beside the product image.")),
        migrations.AddField(model_name="product", name="product_information", field=models.TextField(blank=True, help_text="Additional/product information shown in the Information tab.")),
        migrations.AddField(model_name="product", name="printing_guidelines", field=models.TextField(blank=True, help_text="Product-specific artwork and printing guidance.")),
        migrations.AddField(model_name="product", name="faqs", field=models.TextField(blank=True, help_text="Product-specific FAQs. HTML is supported.")),
        migrations.AddField(model_name="product", name="maximum_quantity", field=models.PositiveIntegerField(blank=True, null=True, help_text="Optional maximum quantity customers may order. Leave blank for no maximum.")),
        migrations.AddField(model_name="product", name="source_url", field=models.URLField(blank=True, max_length=500, help_text="Original ZenVibe.ca product URL used for snapshot import.")),
        migrations.AddField(model_name="product", name="source_synced_at", field=models.DateTimeField(blank=True, null=True, editable=False)),
    ]
