from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path

from .models import StoreEmailAccount
from .services.store_email import test_store_email


class StoreEmailAccountForm(forms.ModelForm):
    class Meta:
        model = StoreEmailAccount
        fields = "__all__"
        help_texts = {
            "email_address": "Gmail requires ZV_GMAIL_APP_PASSWORD on the server. Outlook requires Microsoft Graph application credentials and Mail.Send permission.",
        }


@admin.register(StoreEmailAccount)
class StoreEmailAccountAdmin(admin.ModelAdmin):
    form = StoreEmailAccountForm
    list_display = ("email_address", "provider", "is_active", "updated_at")
    list_filter = ("provider", "is_active")
    actions = ["activate_selected", "send_test"]
    fieldsets = (
        ("Mailbox", {"fields": ("provider", "email_address", "is_active")}),
        ("Notifications", {"fields": ("notify_on_order", "notify_on_contact")}),
    )
    change_form_template = "admin/designer/storeemailaccount/change_form.html"

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if obj.is_active:
                StoreEmailAccount.objects.select_for_update().filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
            super().save_model(request, obj, form, change)

    @admin.action(description="Set selected mailbox as active (select exactly one)")
    def activate_selected(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one mailbox.", level=messages.ERROR)
            return
        with transaction.atomic():
            StoreEmailAccount.objects.select_for_update().filter(is_active=True).update(is_active=False)
            queryset.update(is_active=True)
        self.message_user(request, "Active mailbox updated.")

    @admin.action(description="Send a test email using the active mailbox")
    def send_test(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one mailbox.", messages.ERROR)
            return
        account = queryset.first()
        try:
            test_store_email(account, account.email_address)
        except Exception as exc:
            self.message_user(request, "Test failed: " + str(exc), messages.ERROR)
        else:
            self.message_user(request, "Test email sent.", messages.SUCCESS)

    def get_urls(self):
        return [path("<path:object_id>/test/", self.admin_site.admin_view(self.test_connection),
                     name="designer_storeemailaccount_test")] + super().get_urls()

    def test_connection(self, request, object_id):
        if request.method != "POST":
            return redirect("admin:designer_storeemailaccount_change", object_id)
        obj = self.get_object(request, object_id)
        if obj is None:
            self.message_user(request, "Mailbox not found.", messages.ERROR)
        else:
            try:
                test_store_email(obj, obj.email_address)
            except Exception as exc:
                self.message_user(request, "Email test failed: " + str(exc), messages.ERROR)
            else:
                self.message_user(request, "Test email sent to " + obj.email_address, messages.SUCCESS)
        return redirect("admin:designer_storeemailaccount_change", object_id)

from .models import StoreEmailTemplate


@admin.register(StoreEmailTemplate)
class StoreEmailTemplateAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("designer/admin/zenvibe-richtext.css",)}
        js = ("designer/admin/zenvibe-richtext.js",)

    list_display = ("event", "subject", "enabled")
    list_editable = ("enabled",)
    search_fields = ("subject", "body")
    def get_readonly_fields(self, request, obj=None):
        return ("event",) if obj else ()

    def has_add_permission(self, request):
        from .models import StoreEmailTemplate
        return StoreEmailTemplate.objects.count() < len(StoreEmailTemplate.EVENT_CHOICES)

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ("Notification", {"fields": ("event", "enabled")}),
        ("Email content", {"fields": ("subject", "body")}),
    )

from .models import DiscountCoupon

@admin.register(DiscountCoupon)
class DiscountCouponAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "discount_type", "value", "minimum_subtotal", "is_active", "show_at_checkout", "expires_at")
    list_editable = ("is_active", "show_at_checkout")
    search_fields = ("code", "title")
    list_filter = ("is_active", "discount_type")
