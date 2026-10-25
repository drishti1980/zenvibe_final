from django.core.management.base import BaseCommand
from designer.models import BrandLogo

BRANDS = [
    {
        "name": "Precision Fabrication & Laser Cut",
        "image": "brand_logos/logo1.webp",
        "sort_order": 1,
    },
    {
        "name": "CARSTAR Collision & Glass Service",
        "image": "brand_logos/Carstar-3-1.webp",
        "sort_order": 2,
    },
    {
        "name": "BAPS Charities",
        "image": "brand_logos/BAPS-2-1-1536x1536.webp",
        "sort_order": 3,
    },
    {
        "name": "APTECH Technical Services",
        "image": "brand_logos/Aptech-tech.png",
        "sort_order": 4,
    },
    {
        "name": "Super 8 by Wyndham",
        "image": "brand_logos/Super-8-2-1-1536x1536.webp",
        "sort_order": 5,
    },
    {
        "name": "Tahini's",
        "image": "brand_logos/Tahini.webp",
        "sort_order": 6,
    },
]


class Command(BaseCommand):
    help = "Add/update the six ZenVibe trusted brand logos in the BrandLogo database table."

    def handle(self, *args, **options):
        for brand in BRANDS:
            obj, created = BrandLogo.objects.update_or_create(
                name=brand["name"],
                defaults={
                    "image": brand["image"],
                    "sort_order": brand["sort_order"],
                    "is_active": True,
                },
            )
            action = "CREATED" if created else "UPDATED"
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action}: {obj.name} -> {obj.image.name}'
                )
            )

        self.stdout.write(self.style.SUCCESS("Brand logo database sync complete."))
