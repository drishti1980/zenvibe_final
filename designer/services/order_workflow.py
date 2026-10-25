import base64
import io
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone
from PIL import Image

from designer.models import Order, OrderStatusHistory, OrderWorkflowConfig
from designer.services.store_email import send_store_email, active_account, render_store_template
import logging

logger = logging.getLogger(__name__)

def _notify(subject, body, recipients):
    try:
        return send_store_email(subject, body, recipients)
    except Exception:
        logger.exception("ZenVibe email delivery failed")
        return 0


def workflow():
    return OrderWorkflowConfig.current()


def _admin_emails(cfg):
    raw = cfg.admin_notification_emails or getattr(settings, "ZENVIBE_ADMIN_ORDER_EMAILS", "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def send_order_created_emails(order):
    cfg = workflow()
    account = active_account()
    if account and not account.notify_on_order:
        return
    subject_customer = f"ZenVibe order received — {order.order_number}"
    customer_body = (
        f"Hi {order.customer_name},\n\n"
        f"We received your customised order {order.order_number}.\n"
        f"Product: {order.design.product.name if order.design and order.design.product else 'Custom product'}\n"
        f"Quantity: {order.quantity}\n"
        f"Total: ${order.total}\n"
        f"Status: {order.get_status_display()}\n\n"
        "We will email you as your order progresses.\n\n"
        "ZenVibe Corporate Gifts"
    )
    values = {
        "customer_name": order.customer_name, "customer_email": order.customer_email,
        "order_number": order.order_number, "quantity": order.quantity,
        "total": order.total, "status": order.get_status_display(),
        "product_name": order.design.product.name if order.design and order.design.product else "Custom product",
    }
    customer_message = render_store_template("order_customer", subject_customer, customer_body, values)
    if cfg.email_customer_on_order and order.customer_email and customer_message:
        _notify(*customer_message, [order.customer_email])

    admins = _admin_emails(cfg)
    if cfg.email_admin_on_order and admins:
        admin_body = (
            f"New ZenVibe order {order.order_number}\n\n"
            f"Customer: {order.customer_name} <{order.customer_email}>\n"
            f"Product: {order.design.product.name if order.design and order.design.product else 'Custom product'}\n"
            f"Quantity: {order.quantity}\n"
            f"Total: ${order.total}\n"
            f"Payment: {order.get_payment_status_display()}\n"
            f"Status: {order.get_status_display()}\n\n"
            "Open ZenVibe Admin → Orders to review and download the customised artwork."
        )
        admin_message = render_store_template("order_admin", f"New ZenVibe order — {order.order_number}", admin_body, values)
        if admin_message:
            _notify(*admin_message, admins)


def send_status_email(order, old_status):
    cfg = workflow()
    if not cfg.email_customer_on_status_change or not order.customer_email:
        return
    body = (
        f"Hi {order.customer_name},\n\n"
        f"Your ZenVibe order {order.order_number} has been updated.\n\n"
        f"Previous status: {dict(Order.STATUS_CHOICES).get(old_status, old_status)}\n"
        f"New status: {order.get_status_display()}\n\n"
        "ZenVibe Corporate Gifts"
    )
    status_message = render_store_template("order_status", f"Order update — {order.order_number}", body, {
        "customer_name": order.customer_name, "customer_email": order.customer_email,
        "order_number": order.order_number, "status": order.get_status_display(),
        "old_status": dict(Order.STATUS_CHOICES).get(old_status, old_status),
    })
    if status_message:
        _notify(*status_message, [order.customer_email])


@transaction.atomic
def set_order_status(order, new_status, note="", user=None, automatic=False, send_email=True):
    if new_status == order.status:
        return False
    old = order.status
    order.status = new_status
    order.status_changed_at = timezone.now()
    order.save(update_fields=["status", "status_changed_at", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        from_status=old,
        to_status=new_status,
        note=note,
        changed_by=user,
        automatic=automatic,
    )
    if send_email:
        transaction.on_commit(lambda: send_status_email(order, old))
    return True


def sync_order_status(order, now=None):
    if order.status in ("cancelled", "completed"):
        return False
    cfg = workflow()
    now = now or timezone.now()
    if order.payment_status not in ("paid", "bypassed"):
        return False

    age = now - order.created_at
    target = order.status
    note = ""
    if cfg.auto_complete and age >= timedelta(days=cfg.complete_after_days):
        target, note = "completed", "Automatically completed from workflow configuration"
    elif cfg.auto_ship and age >= timedelta(days=cfg.ship_after_days):
        target, note = "shipped", "Automatically marked shipped from workflow configuration"
    elif cfg.auto_start_production and age >= timedelta(hours=cfg.production_after_hours):
        target, note = "in_production", "Automatically moved to production from workflow configuration"
    elif cfg.auto_confirm and age >= timedelta(minutes=cfg.confirm_after_minutes):
        target, note = "confirmed", "Automatically confirmed from workflow configuration"

    rank = {"new": 0, "confirmed": 1, "in_production": 2, "shipped": 3, "completed": 4}
    if rank.get(target, 0) > rank.get(order.status, 0):
        return set_order_status(order, target, note=note, automatic=True)
    return False


def sync_all_orders():
    changed = 0
    for order in Order.objects.exclude(status__in=["cancelled", "completed"]).iterator():
        if sync_order_status(order):
            changed += 1
    return changed


def preview_bytes(design, fmt="png"):
    src = (design.preview_png or "").strip()
    if not src.startswith("data:image/") or "," not in src:
        raise ValueError("This design does not contain an exportable preview yet.")
    _, encoded = src.split(",", 1)
    raw = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(raw))
    fmt = fmt.lower()
    out = io.BytesIO()

    if fmt == "png":
        image.save(out, "PNG")
        return out.getvalue(), "image/png", "png"

    rgb = Image.new("RGB", image.size, "white")
    if image.mode == "RGBA":
        rgb.paste(image, mask=image.getchannel("A"))
    else:
        rgb.paste(image.convert("RGB"))

    if fmt in ("jpg", "jpeg"):
        rgb.save(out, "JPEG", quality=95)
        return out.getvalue(), "image/jpeg", "jpg"
    if fmt == "pdf":
        rgb.save(out, "PDF", resolution=150.0)
        return out.getvalue(), "application/pdf", "pdf"
    raise ValueError("Unsupported format")
