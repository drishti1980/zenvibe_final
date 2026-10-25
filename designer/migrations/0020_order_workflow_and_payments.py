from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[("designer","0019_order"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AddField(model_name="order", name="payment_status", field=models.CharField(choices=[("pending","Pending"),("bypassed","Bypassed / test"),("paid","Paid"),("failed","Failed"),("refunded","Refunded")], db_index=True, default="pending", max_length=20)),
        migrations.AddField(model_name="order", name="payment_provider", field=models.CharField(default="bypass", max_length=30)),
        migrations.AddField(model_name="order", name="stripe_checkout_session_id", field=models.CharField(blank=True, db_index=True, max_length=255)),
        migrations.AddField(model_name="order", name="paid_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="order", name="status_changed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(name="OrderWorkflowConfig", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("name",models.CharField(default="Default workflow",max_length=80)),("is_active",models.BooleanField(default=True)),
            ("payment_mode",models.CharField(choices=[("bypass","Bypass / test mode"),("stripe","Stripe Checkout")],default="bypass",max_length=20)),("currency",models.CharField(default="cad",max_length=3)),
            ("admin_notification_emails",models.TextField(blank=True,help_text="Comma-separated admin notification email addresses")),
            ("auto_confirm",models.BooleanField(default=True)),("confirm_after_minutes",models.PositiveIntegerField(default=0)),
            ("auto_start_production",models.BooleanField(default=True)),("production_after_hours",models.PositiveIntegerField(default=24)),
            ("auto_ship",models.BooleanField(default=False)),("ship_after_days",models.PositiveIntegerField(default=5)),
            ("auto_complete",models.BooleanField(default=False)),("complete_after_days",models.PositiveIntegerField(default=10)),
            ("email_customer_on_order",models.BooleanField(default=True)),("email_customer_on_status_change",models.BooleanField(default=True)),("email_admin_on_order",models.BooleanField(default=True)),("updated_at",models.DateTimeField(auto_now=True)),
        ],options={"verbose_name":"Order workflow configuration","verbose_name_plural":"Order workflow configuration"}),
        migrations.CreateModel(name="OrderStatusHistory", fields=[
            ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
            ("from_status",models.CharField(blank=True,max_length=30)),("to_status",models.CharField(max_length=30)),("note",models.CharField(blank=True,max_length=255)),("automatic",models.BooleanField(default=False)),("created_at",models.DateTimeField(auto_now_add=True)),
            ("changed_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
            ("order",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="status_history",to="designer.order")),
        ],options={"ordering":["-created_at"]}),
    ]
