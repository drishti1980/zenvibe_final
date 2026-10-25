"""Encrypted mailbox secrets; never return decrypted values to admin forms."""
import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings


def _cipher():
    # Stable deployment secret; changing SECRET_KEY invalidates existing encrypted passwords.
    material = ("zenvibe-mail-credential-v1:" + settings.SECRET_KEY).encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
    return Fernet(key)


def encrypt_password(value):
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_password(value):
    return _cipher().decrypt(value.encode("ascii")).decode("utf-8") if value else ""
