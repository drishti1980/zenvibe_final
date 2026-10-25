from pathlib import Path
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Category, Product, DesignTemplate


class Command(BaseCommand):
    help = "Install/update 200 original editable ZenVibe business-card templates. Safe to rerun."

    def add_arguments(self, parser):
        parser.add_argument("--replace", action="store_true", help="Remove other templates from the two generated business-card products.")

    @transaction.atomic
    def handle(self, *args, **options):
        lib = Path(__file__).resolve().parents[2] / "business_card_templates_200.json"
        if not lib.exists():
            raise CommandError(f"Missing business-card library: {lib}")
        data = json.loads(lib.read_text(encoding="utf-8"))
        if len(data) < 200:
            raise CommandError(f"Business-card library has only {len(data)} designs; expected 200.")

        marketing, _ = Category.objects.update_or_create(
            slug="marketing-materials",
            defaults={"name":"Marketing Materials","icon":"▤","description":"Business cards, invitations, flyers, brochures and printed marketing materials.","is_active":True,"is_out_of_stock":False,"sort_order":90,"parent":None},
        )
        parent, _ = Category.objects.update_or_create(
            slug="business-cards",
            defaults={"name":"Business Cards","icon":"▣","description":"Professional custom business cards with editable front and back designs.","is_active":True,"is_out_of_stock":False,"sort_order":10,"parent":marketing},
        )
        standard_cat, _ = Category.objects.update_or_create(
            slug="standard-business-cards", defaults={"name":"Standard Business Cards","icon":"▤","description":"Editable standard business-card designs.","is_active":True,"is_out_of_stock":False,"sort_order":21,"parent":parent}
        )
        premium_cat, _ = Category.objects.update_or_create(
            slug="premium-business-cards", defaults={"name":"Premium Business Cards","icon":"◆","description":"Editable premium business-card designs for luxury finishes.","is_active":True,"is_out_of_stock":False,"sort_order":22,"parent":parent}
        )
        products={}
        for tier, cat, name, slug, price in [
            ("standard",standard_cat,"Standard Business Cards","standard-business-card-designer","0.14"),
            ("premium",premium_cat,"Premium Business Cards","premium-business-card-designer","0.18"),
        ]:
            product,_=Product.objects.update_or_create(
                category=cat,slug=slug,
                defaults={"name":name,"description":"Choose from modern two-sided editable business-card templates, then personalise text, logo, colours, QR and graphics.","price":price,"width":1125,"height":675,"orientation":"landscape","customizer_mode":"editor","bleed_mm":3,"safe_margin_mm":5,"min_dpi":300,"is_active":True,"is_out_of_stock":False},
            )
            products[tier]=product

        keep={"standard":set(),"premium":set()}
        for item in data:
            tier=item.get("tier","standard");product=products[tier];t=item["template"]
            keep[tier].add(t["name"])
            DesignTemplate.objects.update_or_create(product=product,name=t["name"],defaults={"preview":t.get("preview") or None,"json_data":t.get("json_data") or {},"is_active":True})
        if options["replace"]:
            for tier,p in products.items():p.templates.exclude(name__in=keep[tier]).delete()

        # Hide obsolete/demo business-card products so customers see one consistent,
        # editable standard/premium workflow. Existing saved designs remain intact.
        Product.objects.filter(category__slug__in=["business-cards","luxury-business-cards"],name__in=["Demo Business Card","Business Card","Luxury Business Card","Premium Business Card"]).update(is_active=False)
        self.stdout.write(self.style.SUCCESS("200 editable two-sided business-card templates are ready (100 standard, 100 premium)."))
