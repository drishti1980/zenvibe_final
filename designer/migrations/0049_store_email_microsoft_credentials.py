from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("designer", "0048_store_email_encrypted_password")]
    operations = [
        migrations.AddField(model_name="storeemailaccount", name="ms_tenant_id", field=models.CharField(max_length=255, blank=True, default="")),
        migrations.AddField(model_name="storeemailaccount", name="ms_client_id", field=models.CharField(max_length=255, blank=True, default="")),
        migrations.AddField(model_name="storeemailaccount", name="encrypted_ms_client_secret", field=models.TextField(blank=True, default="", editable=False)),
    ]
