from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("designer", "0047_payment_setup_proxy")]
    operations = [migrations.AddField(model_name="storeemailaccount", name="encrypted_app_password", field=models.TextField(blank=True, default="", editable=False))]
