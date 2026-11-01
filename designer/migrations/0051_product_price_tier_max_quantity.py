from django.db import migrations, models


def backfill_ranges(apps, schema_editor):
    Tier = apps.get_model("designer", "ProductPriceTier")
    db = schema_editor.connection.alias
    groups = {}
    for tier in Tier.objects.using(db).filter(is_active=True).order_by("min_quantity", "id"):
        groups.setdefault((tier.product_id, tier.variant_id), []).append(tier)
    for tiers in groups.values():
        for index, tier in enumerate(tiers[:-1]):
            next_min = next((t.min_quantity for t in tiers[index + 1:] if t.min_quantity > tier.min_quantity), None)
            if next_min is not None:
                Tier.objects.using(db).filter(pk=tier.pk).update(max_quantity=next_min - 1)


class Migration(migrations.Migration):
    dependencies = [("designer", "0050_coupon_products")]
    operations = [
        migrations.AddField(
            model_name="productpricetier", name="max_quantity",
            field=models.PositiveIntegerField(blank=True, null=True, help_text="Inclusive maximum quantity. Leave blank for no upper limit."),
        ),
        migrations.RunPython(backfill_ranges, migrations.RunPython.noop),
    ]
