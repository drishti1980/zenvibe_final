import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Category, Product, ProductImage


TOP_LEVEL = [
    ("Business Cards", "business-cards", 1, "Professional custom business cards for Canadian companies, teams and events."),
    ("Invitations", "invitations", 2, "Custom invitations and event stationery for business and personal occasions."),
    ("Pens", "pens", 10, "Branded writing instruments for offices, events, giveaways and corporate gifts."),
    ("Bags", "bags", 30, "Custom bags for promotions, travel, events, retail and employee programs."),
    ("Drinkware", "drinkware", 35, "Custom mugs, tumblers and bottles for branded giveaways and corporate programs."),
    ("Awards", "awards", 40, "Custom trophies, crystal awards, medals and plaques for recognition and events."),
    ("Custom notebooks", "custom-notebooks", 45, "Branded notebooks and stationery for offices, schools and promotional campaigns."),
    ("Banners & Displays", "banners-displays", 50, "Custom event displays including flags, banners, tents, table covers and trade show systems."),
    ("Corporate Gift Set", "corporate-gift-set", 60, "Curated branded gift sets for clients, employees, events and onboarding."),
    ("Custom Apparel", "custom-apparel", 70, "Custom apparel including DTF printing, sublimation, jackets, hoodies and embroidered caps."),
    ("Marketing Materials", "marketing-materials", 80, "Printed marketing material and branded business collateral."),
    ("Promotional Products", "promotional-products", 90, "Custom branded merchandise for giveaways, events and everyday promotion."),
]

CHILDREN = {
    "business-cards": [
        ("Standard Business Cards", "standard-business-cards", 10),
        ("Luxury Business Cards", "luxury-business-cards", 20),
    ],
    "invitations": [
        ("Corporate Invitations", "corporate-invitations", 10),
        ("Event Invitations", "event-invitations", 20),
    ],
    "pens": [
        ("Metal Pens", "metal-pens", 10),
        ("Stylus Pens", "stylus-pens", 20),
        ("Executive Pens", "executive-pens", 30),
        ("Pen & Notebook Sets", "pen-notebook-sets", 40),
    ],
    "bags": [
        ("Tote Bags", "tote-bags", 10),
        ("Backpacks", "backpacks", 20),
        ("Lunch Bags", "lunch-bags", 30),
        ("Waist & Crossbody Bags", "waist-crossbody-bags", 40),
    ],
    "drinkware": [
        ("Mugs", "mugs", 10),
        ("Tumblers & Travel Mugs", "tumblers", 20),
        ("Water Bottles", "water-bottles", 30),
        ("Kids Drinkware", "kids-drinkware", 40),
    ],
    "awards": [
        ("Trophies", "trophies", 10),
        ("Crystal Awards", "crystal-awards", 20),
        ("Medals", "medals", 30),
        ("Plaques", "plaques", 40),
    ],
    "custom-notebooks": [
        ("Spiral Notebooks", "spiral-notebooks", 10),
        ("Executive Notebooks", "executive-notebooks", 20),
    ],
    "banners-displays": [
        ("Custom Flags", "custom-flags", 10),
        ("Canopy Tent", "canopy-tent", 20),
        ("Custom Banners", "custom-banners", 30),
        ("Custom Table Covers", "custom-table-covers", 40),
        ("Standing Banners", "standing-banners", 50),
        ("Trade Show Displays", "trade-show-displays", 60),
    ],
    "corporate-gift-set": [
        ("Executive Gift Sets", "executive-gift-sets", 10),
        ("Bamboo Gift Sets", "bamboo-gift-sets", 20),
        ("Welcome Kits", "welcome-kits", 30),
    ],
    "custom-apparel": [
        ("Custom Caps", "custom-caps", 10),
        ("Custom DTF T-shirt", "custom-dtf-t-shirt", 20),
        ("Custom Jackets", "custom-jackets", 30),
        ("Custom Sublimated Sportswear", "custom-sublimated-sportswear", 40),
        ("Hoodie", "hoodie", 50),
    ],
    "marketing-materials": [
        ("Flyers & Brochures", "flyers-brochures", 10),
        ("Signs & Print Materials", "signs-print-materials", 20),
    ],
    "promotional-products": [
        ("Keychains", "keychains", 10),
        ("Umbrellas", "umbrellas", 20),
        ("Custom Plates & Signs", "custom-plates-signs", 30),
        ("General Promotional Products", "general-promotional-products", 40),
        # This stores reference/support assets imported from the supplied site archive.
        # It stays hidden from the public menu while preserving the files in the database.
        ("Original Site Asset Library", "original-site-assets", 99),
    ],
}

CHILD_DESCRIPTIONS = {
    "custom-flags": "Custom feather, teardrop and rectangle flags for storefronts, events, exhibitions and outdoor promotions.",
    "canopy-tent": "Custom canopy tents for trade shows, festivals, outdoor events and branded activations.",
    "custom-banners": "Custom vinyl, mesh and promotional banners for events, retail spaces and outdoor advertising.",
    "custom-table-covers": "Branded table covers for trade shows, exhibitions, presentations and event displays.",
    "standing-banners": "Portable retractable and standing banner displays for recurring promotions and events.",
    "trade-show-displays": "Coordinated branded display systems for exhibitions, conferences and trade shows.",
    "custom-caps": "Custom embroidered and printed caps for businesses, teams, schools, uniforms and events.",
    "custom-dtf-t-shirt": "Custom DTF printed T-shirts for staff, events, teams, promotions and branded apparel programs.",
    "custom-jackets": "Custom softshell and weather-resistant jackets for staff uniforms, teams and outdoor branding.",
    "custom-sublimated-sportswear": "Custom sublimated jerseys and sportswear for clubs, schools, teams and branded programs.",
    "hoodie": "Custom printed hoodies for businesses, schools, teams, clubs and promotional branding.",
    "trophies": "Custom trophies for sports, ceremonies, corporate recognition and special achievements.",
    "crystal-awards": "Premium crystal and glass recognition awards for corporate, team and event presentations.",
    "medals": "Custom medals and recognition pieces for competitions, ceremonies and achievements.",
    "plaques": "Custom plaques and recognition displays for awards, service milestones and corporate presentations.",
    "mugs": "Custom branded mugs for offices, events, gifts and promotional campaigns.",
    "tumblers": "Custom tumblers and travel mugs for reusable branded drinkware programs.",
    "water-bottles": "Custom reusable water bottles for teams, workplaces, schools, events and giveaways.",
    "kids-drinkware": "Custom drinkware sized for children, schools, clubs and family-focused promotions.",
    "tote-bags": "Custom tote bags for retail, events, giveaways, conferences and everyday brand visibility.",
    "backpacks": "Custom backpacks for staff, students, travel, events and promotional programs.",
    "lunch-bags": "Custom lunch and cooler bags for workplaces, schools, events and branded gifts.",
    "waist-crossbody-bags": "Custom waist and crossbody bags for events, travel and lifestyle promotions.",
    "metal-pens": "Custom metal pens for offices, events, giveaways and everyday business branding.",
    "stylus-pens": "Custom stylus pens combining writing and touch-screen use for modern promotional programs.",
    "executive-pens": "Premium branded pens for executive gifts, client programs and corporate presentations.",
    "pen-notebook-sets": "Coordinated branded pen and notebook sets for onboarding, meetings and corporate gifts.",
    "keychains": "Custom branded keychains and useful everyday promotional accessories.",
    "umbrellas": "Custom branded umbrellas for corporate gifts, events, staff programs and outdoor promotions.",
    "custom-plates-signs": "Custom plates, desk signs and compact branded signage for workplaces and events.",
    "general-promotional-products": "A broad selection of custom promotional merchandise for giveaways, events and campaigns.",
    "executive-gift-sets": "Curated corporate gift sets for clients, staff recognition, events and executive programs.",
    "bamboo-gift-sets": "Branded bamboo-themed gift sets for premium, practical and presentation-ready gifting.",
    "welcome-kits": "Custom employee and client welcome kits combining coordinated branded products.",
    "spiral-notebooks": "Custom spiral notebooks for meetings, schools, events, training and promotional use.",
    "executive-notebooks": "Premium branded notebooks for offices, client gifts and employee programs.",
    "flyers-brochures": "Custom printed flyers and brochures for business information, promotions and events.",
    "signs-print-materials": "Custom signs and printed collateral for retail, offices, events and local promotions.",
    "standard-business-cards": "Professional custom business cards for everyday networking and company branding.",
    "luxury-business-cards": "Premium business cards with elevated finishes and presentation for high-impact networking.",
    "corporate-invitations": "Custom invitations for corporate events, launches, openings and professional occasions.",
    "event-invitations": "Custom invitations and stationery for celebrations, community events and special occasions.",
}


class Command(BaseCommand):
    help = "Build the ZenVibe parent/child catalogue and restore imported product images from the packaged manifest."

    @transaction.atomic
    def handle(self, *args, **options):
        app_dir = Path(__file__).resolve().parents[2]
        manifest_path = app_dir / "catalog_import_manifest.json"
        if not manifest_path.exists():
            raise CommandError(f"Missing catalogue manifest: {manifest_path}")

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CommandError(f"Could not read catalogue manifest: {exc}") from exc

        categories = self._ensure_categories()
        created_products = 0
        linked_images = 0

        for row in manifest:
            if row.get("status") not in {"main-image", "product-image"}:
                continue
            category = categories.get(row.get("category"))
            product_name = (row.get("product") or "").strip()
            image_path = (row.get("path") or "").strip()
            if not category or not product_name or not image_path:
                continue

            product, made = Product.objects.get_or_create(
                category=category,
                name=product_name,
                defaults={
                    "description": f"Customisable {product_name}.",
                    "price": 39.00,
                    "is_active": category.slug != "original-site-assets",
                    "customizer_mode": "photo",
                },
            )
            if made:
                created_products += 1
            elif product.customizer_mode == "auto" and product.pk >= 67:
                product.customizer_mode = "photo"
                product.save(update_fields=["customizer_mode"])

            if row["status"] == "main-image":
                if not product.image:
                    product.image.name = image_path
                    product.save(update_fields=["image"])
                    linked_images += 1
            else:
                _, made_image = ProductImage.objects.get_or_create(
                    product=product,
                    image=image_path,
                    defaults={
                        "label": Path(image_path).stem.replace("-", " ").title()[:120],
                        "sort_order": product.angle_images.count(),
                    },
                )
                if made_image:
                    linked_images += 1

        self._hide_reference_assets()
        self.stdout.write(self.style.SUCCESS(
            f"Catalogue ready: {Category.objects.count()} categories, "
            f"{Product.objects.count()} products, {ProductImage.objects.count()} extra product images. "
            f"Created {created_products} missing products and linked {linked_images} missing images."
        ))

    def _ensure_categories(self):
        result = {}
        for name, slug, sort_order, description in TOP_LEVEL:
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "parent": None,
                    "sort_order": sort_order,
                    "description": description,
                    "is_active": True,
                    "is_out_of_stock": False,
                },
            )
            result[slug] = category

        for parent_slug, children in CHILDREN.items():
            parent = result[parent_slug]
            for name, slug, sort_order in children:
                # Preserve the legacy t-shirt route when it already exists.
                if slug == "custom-dtf-t-shirt":
                    category = Category.objects.filter(slug="t-shirt").first()
                    if category:
                        category.name = name
                        category.parent = parent
                        category.sort_order = sort_order
                        if not category.description:
                            category.description = CHILD_DESCRIPTIONS.get(slug, "")
                        category.is_active = True
                        category.is_out_of_stock = False
                        category.save()
                        result[slug] = category
                        continue
                category, _ = Category.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "parent": parent,
                        "sort_order": sort_order,
                        "description": CHILD_DESCRIPTIONS.get(slug, ""),
                        "is_active": slug != "original-site-assets",
                        "is_out_of_stock": False,
                    },
                )
                result[slug] = category
        return result

    def _hide_reference_assets(self):
        category = Category.objects.filter(slug="original-site-assets").first()
        if not category:
            return
        category.is_active = False
        category.save(update_fields=["is_active"])
        Product.objects.filter(category=category).update(is_active=False)
