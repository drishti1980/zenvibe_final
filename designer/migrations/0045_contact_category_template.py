from django.db import migrations


def update_contact_template(apps, schema_editor):
    Template = apps.get_model("designer", "StoreEmailTemplate")
    row = Template.objects.filter(event="contact_admin").first()
    if row and "{product_category}" not in row.body:
        # Preserve existing customised wording and layout.
        anchor = "<strong>Subject:</strong> {subject}"
        addition = "<strong>Product category:</strong> {product_category}<br>"
        if anchor in row.body:
            row.body = row.body.replace(anchor, addition + anchor, 1)
        else:
            row.body += "<p><strong>Product category:</strong> {product_category}</p>"
        row.save(update_fields=["body"])


class Migration(migrations.Migration):
    dependencies = [("designer", "0044_branded_custom_order_emails")]
    operations = [migrations.RunPython(update_contact_template, migrations.RunPython.noop)]
