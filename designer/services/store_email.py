"""Single active store mailbox. Gmail secrets are encrypted in DB or read from environment."""
import base64
import json
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

from django.conf import settings
from django.utils.html import escape, strip_tags
import re
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.exceptions import ImproperlyConfigured

from designer.models import StoreEmailAccount


def active_account():
    return StoreEmailAccount.objects.filter(is_active=True).first()


def _outlook_token(account=None):
    from designer.services.mail_credentials import decrypt_password
    tenant = (account.ms_tenant_id if account else "") or os.environ.get("ZV_MS_TENANT_ID", "")
    client = (account.ms_client_id if account else "") or os.environ.get("ZV_MS_CLIENT_ID", "")
    secret = (decrypt_password(account.encrypted_ms_client_secret) if account and account.encrypted_ms_client_secret else os.environ.get("ZV_MS_CLIENT_SECRET", ""))
    if not all((tenant, client, secret)):
        raise ImproperlyConfigured("Set ZV_MS_TENANT_ID, ZV_MS_CLIENT_ID and ZV_MS_CLIENT_SECRET.")
    data = urllib.parse.urlencode({
        "client_id": client, "client_secret": secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode()
    req = urllib.request.Request(
        "https://login.microsoftonline.com/" + urllib.parse.quote(tenant, safe="") + "/oauth2/v2.0/token",
        data=data, method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)["access_token"]


def _graph_request(method, path, payload=None, account=None):
    token = _outlook_token(account)
    req = urllib.request.Request(
        "https://graph.microsoft.com/v1.0/" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else {}


def send_store_email(subject, body, recipients, reply_to=None):
    is_html = bool(re.search(r'<(?:p|h[1-6]|div|table|br|img|ul|ol|strong)\b', body, re.I))
    plain_body = strip_tags(body) if is_html else body
    recipients = [r for r in recipients if r]
    if not recipients:
        return 0
    account = active_account()
    if account is None:
        # Preserve existing configured Django mail delivery until a mailbox is activated.
        msg = EmailMultiAlternatives(subject, plain_body, settings.DEFAULT_FROM_EMAIL, recipients,
                                      reply_to=[reply_to] if reply_to else None)
        if is_html:
            msg.attach_alternative(body, "text/html")
        return msg.send()
    if account.provider == "gmail":
        from designer.services.mail_credentials import decrypt_password
        password = (decrypt_password(account.encrypted_app_password)
                    if account.encrypted_app_password else os.environ.get("ZV_GMAIL_APP_PASSWORD", ""))
        if not password:
            raise ImproperlyConfigured("ZV_GMAIL_APP_PASSWORD is missing.")
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host="smtp.gmail.com", port=587, use_tls=True, use_ssl=False,
            username=account.email_address, password=password, timeout=25,
        )
        msg = EmailMultiAlternatives(subject, plain_body, account.email_address, recipients,
                                      reply_to=[reply_to] if reply_to else None,
                                      connection=connection)
        if is_html:
            msg.attach_alternative(body, "text/html")
        return msg.send()
    if account.provider == "outlook":
        mailbox = urllib.parse.quote(account.email_address, safe="")
        message = {
            "subject": subject,
            "body": {"contentType": "HTML" if is_html else "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": recipient}} for recipient in recipients],
        }
        if reply_to:
            message["replyTo"] = [{"emailAddress": {"address": reply_to}}]
        _graph_request("POST", "users/" + mailbox + "/sendMail",
                       {"message": message, "saveToSentItems": True}, account=account)
        return 1
    raise ImproperlyConfigured("Unknown store email provider.")


def test_store_email(account, recipient):
    if not account.is_active:
        raise ValueError("Activate this mailbox before testing.")
    return send_store_email("ZenVibe email connection test",
                            "Your ZenVibe store email connection is working.", [recipient])


def render_store_template(event, default_subject, default_body, values):
    """Use editable notification copy; unknown placeholders remain visible."""
    from designer.models import StoreEmailTemplate
    record = StoreEmailTemplate.objects.filter(event=event).first()
    if record and not record.enabled:
        return None
    class SafeValues(dict):
        def __missing__(self, key):
            return "{" + key + "}"
    safe = SafeValues({k: str(v if v is not None else "") for k, v in values.items()})
    subject = (record.subject if record else default_subject).format_map(safe)
    html_safe = SafeValues({k: escape(v) for k, v in safe.items()})
    body = (record.body if record else default_body).format_map(html_safe if record else safe)
    return subject, body
