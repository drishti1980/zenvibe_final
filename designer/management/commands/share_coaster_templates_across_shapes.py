"""Keep exactly 100 editable coaster designs shared by Circle and Square.

Shapes are presentation/print masks, NOT separate template sets. This command
never replaces artwork or thumbnails and never creates a second set of 100.
"""
from __future__ import annotations
import copy
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product

class Command(BaseCommand):
    help = "Configure one shared 100-design coaster library for square/circle."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **opts):
        if opts["product_id"] != 415:
            raise CommandError("Restricted to coaster product 415.")
        product = Product.objects.filter(pk=415).first()
        if product is None or "coaster" not in product.name.lower():
            raise CommandError("Product 415 is missing or not a coaster.")
        templates = list(DesignTemplate.objects.filter(product_id=415, is_active=True).order_by("id"))
        if len(templates) != 100:
            raise CommandError(f"Expected 100 active coaster designs, found {len(templates)}. No changes.")
        for template in templates:
            data = template.json_data
            if not isinstance(data, dict) or not isinstance(data.get("pages"), list) or not data["pages"]:
                raise CommandError(f"Template {template.id} has invalid page data.")
        self.stdout.write("Validated 100 designs. Both shapes will reference these same template IDs.")
        if not opts["apply"]:
            self.stdout.write("Dry-run only. Pass --apply to set shared-shape metadata.")
            return
        with transaction.atomic():
            attrs = copy.deepcopy(product.source_attributes or {})
            attrs["Shape"] = ["Circle", "Square"]
            product.source_attributes = attrs
            product.save(update_fields=["source_attributes"])
            for template in templates:
                data = copy.deepcopy(template.json_data)
                data["availableShapes"] = ["Circle", "Square"]
                data["shapeIndependentArtwork"] = True
                data["constrainToPrintArea"] = True
                # Preserve all original editable objects, their page order, and previews.
                template.json_data = data
                template.save(update_fields=["json_data"])
        self.stdout.write(self.style.SUCCESS("Updated shape metadata for 100 existing templates; no duplicate templates or artwork replacement."))
