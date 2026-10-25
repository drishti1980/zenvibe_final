import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Category, Product, DesignTemplate


class Command(BaseCommand):
    help = "Install/update the 200 editable ZenVibe invitation templates. Safe to rerun."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete templates belonging to the generated invitation products before reseeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        library_file = Path(__file__).resolve().parents[2] / "invitation_templates_200.json"
        if not library_file.exists():
            raise CommandError(f"Missing invitation library: {library_file}")

        data = json.loads(library_file.read_text(encoding="utf-8"))
        if len(data) < 200:
            raise CommandError(f"Invitation library contains only {len(data)} templates; expected at least 200.")

        marketing, _ = Category.objects.update_or_create(
            slug="marketing-materials",
            defaults={
                "name": "Marketing Materials",
                "icon": "▤",
                "description": "Business cards, invitations, flyers, brochures and printed marketing materials.",
                "is_active": True,
                "is_out_of_stock": False,
                "sort_order": 90,
                "parent": None,
            },
        )
        parent, _ = Category.objects.update_or_create(
            slug="invitations",
            defaults={
                "name": "Invitations",
                "icon": "✉️",
                "description": "Elegant editable invitations for celebrations, family events and corporate occasions.",
                "is_active": True,
                "is_out_of_stock": False,
                "sort_order": 20,
                "parent": marketing,
            },
        )

        product_ids = set()
        created_or_updated = 0
        for item in data:
            c = item["category"]
            category, _ = Category.objects.update_or_create(
                slug=c["slug"],
                defaults={
                    "name": c["name"],
                    "icon": c.get("icon", "✉️"),
                    "description": c.get("description", ""),
                    "is_active": True,
                    "is_out_of_stock": False,
                    "sort_order": c.get("sort_order", 30),
                    "parent": parent,
                },
            )

            p = item["product"]
            product, _ = Product.objects.update_or_create(
                category=category,
                slug=p["slug"],
                defaults={
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "price": p.get("price", "29.00"),
                    "width": p.get("width", 700),
                    "height": p.get("height", 1000),
                    "orientation": p.get("orientation", "portrait"),
                    "customizer_mode": "editor",
                    "bleed_mm": 3,
                    "safe_margin_mm": 5,
                    "min_dpi": 300,
                    "is_active": True,
                    "is_out_of_stock": False,
                },
            )
            product_ids.add(product.id)

            # Use a generated preview as the product card image when none exists.
            if not product.image and item["template"].get("preview"):
                product.image = item["template"]["preview"]
                product.save(update_fields=["image"])

            t = item["template"]
            DesignTemplate.objects.update_or_create(
                product=product,
                name=t["name"],
                defaults={
                    "preview": t.get("preview") or None,
                    "json_data": t.get("json_data") or {},
                    "is_active": True,
                },
            )
            created_or_updated += 1

        if options["replace"]:
            # Keep exactly the generated names for our generated products; unrelated
            # user/admin templates elsewhere are untouched.
            keep = {}
            for item in data:
                keep.setdefault(item["product"]["slug"], set()).add(item["template"]["name"])
            for product in Product.objects.filter(id__in=product_ids):
                names = keep.get(product.slug, set())
                product.templates.exclude(name__in=names).delete()

        # Hide legacy flattened/generic invitation products so the storefront does
        # not mix uneditable photo-only flows with the new layered template library.
        Product.objects.filter(slug__in=["classic-invitation", "invitation-cards"]).update(is_active=False)

        self.stdout.write(self.style.SUCCESS(
            f"{created_or_updated} editable invitation templates are ready across 10 invitation categories."
        ))
