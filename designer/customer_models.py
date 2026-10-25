from django.conf import settings
from django.db import models


class CustomerAddress(models.Model):
    PROVINCES = [
        ("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
        ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
        ("NS", "Nova Scotia"), ("NT", "Northwest Territories"),
        ("NU", "Nunavut"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
        ("QC", "Quebec"), ("SK", "Saskatchewan"), ("YT", "Yukon"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="zenvibe_addresses")
    label = models.CharField(max_length=60, default="Home")
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=160, blank=True)
    address = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    province = models.CharField(max_length=2, choices=PROVINCES)
    postal_code = models.CharField(max_length=7)
    country = models.CharField(max_length=2, default="CA", editable=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.label}: {self.address}, {self.city}, {self.province}"
