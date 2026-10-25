from django.core.management.base import BaseCommand
from designer.models import PageContentBlock

# About-page content and LOCAL media only.
# All records remain editable from Django Admin after this command runs.
DATA = [
    ("hero", 1, "", "About ZenVibe Corporate Gifts",
     "Your Trusted Canadian Partner for Custom Promotional Products, Corporate Gifts, Apparel, Awards & Event Branding",
     "page-content/about/hero.webp"),

    ("why-heading", 10, "", "Why Choose ZenVibe?", "", ""),

    ("why-01", 11, "", "Free Mockups",
     "Preview your design before production on eligible bulk orders.",
     "page-content/about/free-mockups.webp"),

    ("why-02", 12, "", "Bulk Discounts",
     "Save more on corporate, team, event, and promotional orders.",
     "page-content/about/bulk-discounts.webp"),

    ("why-03", 13, "", "Canada-Wide Delivery",
     "Reliable shipping for customers and businesses across Canada.",
     "page-content/about/canada-delivery.webp"),

    ("why-04", 14, "", "Quality Products",
     "Professional printing, engraving, embroidery, and customization.",
     "page-content/about/quality-products.webp"),

    ("who-we-are", 20, "ABOUT ZENVIBE", "Who We Are",
     "At ZenVibe Corporate Gifts, we help businesses, organizations, schools, sports teams, and event planners create memorable brand experiences through high-quality custom promotional products and corporate gifts.\n\n"
     "Based in Edmonton, Alberta, we proudly serve customers across Canada with custom apparel, awards and trophies, drinkware, banners and displays, marketing materials, corporate gift sets, and promotional merchandise designed to increase brand visibility and leave a lasting impression.\n\n"
     "Whether you need branded products for trade shows, employee recognition programs, corporate events, sports tournaments, or marketing campaigns, our team provides personalized service, quality products, competitive pricing, and reliable nationwide delivery.",
     "page-content/about/who-we-are.webp"),

    ("offer-heading", 30, "OUR PRODUCTS", "What We Offer", "", ""),

    ("offer-01", 31, "", "Banners & Displays",
     "Roll-up banners, flags, canopy tents, table covers, and trade show displays.",
     "page-content/about/banners-displays.webp"),

    ("offer-02", 32, "", "Custom Apparel",
     "Sublimated jerseys, DTF T-shirts, hoodies, jackets and caps.",
     "page-content/about/custom-apparel.webp"),

    ("offer-03", 33, "", "Awards & Medals",
     "Trophies, crystal awards, plaques, medals, and recognition products.",
     "page-content/about/awards-medals.webp"),

    ("offer-04", 34, "", "Marketing Materials",
     "Business cards, flyers, brochures, tickets, invitation cards, and door hangers.",
     "page-content/about/marketing-materials.webp"),

    ("offer-05", 35, "", "Drinkware & Gifts",
     "Mugs, tumblers, water bottles, thermos bottles, and corporate gift sets.",
     "page-content/about/drinkware-gifts.webp"),

    ("offer-06", 36, "", "Promotional Products",
     "Keychains, lanyards, badges, pens, notebooks, coasters, and giveaways.",
     "page-content/about/promotional-products.webp"),

    ("contact", 50, "LET'S CREATE SOMETHING GREAT", "Get In Touch With Us",
     "Have a product, artwork or bulk-order question? Our team is ready to help you find the right branded solution.",
     ""),
]

class Command(BaseCommand):
    help = "Create/update the Admin-managed About page using local media."

    def handle(self, *args, **options):
        for key, order, subheading, heading, body, image in DATA:
            obj, _ = PageContentBlock.objects.update_or_create(
                page="about",
                section_key=key,
                defaults={
                    "sort_order": order,
                    "subheading": subheading,
                    "heading": heading,
                    "body": body,
                    "is_active": True,
                },
            )
            if image:
                obj.image.name = image
                obj.save(update_fields=["image"])

        self.stdout.write(
            self.style.SUCCESS(
                f"About page updated: {len(DATA)} Admin-managed content blocks."
            )
        )
