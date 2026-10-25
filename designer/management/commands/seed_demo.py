
from django.core.management.base import BaseCommand
from designer.models import Category, Product, DesignTemplate

class Command(BaseCommand):
    help = "Seed demo categories/products/templates"

    def handle(self, *args, **kwargs):
        business, _ = Category.objects.update_or_create(
            slug="business-cards",
            defaults={
                "name":"Business Cards",
                "icon":"💼",
                "description":"Create premium business cards from editable templates or blank canvas.",
                "is_active":True,
                "is_out_of_stock":False,
                "sort_order":1,
            }
        )
        invites, _ = Category.objects.update_or_create(
            slug="invitations",
            defaults={
                "name":"Invitations",
                "icon":"💌",
                "description":"Design beautiful invitations for weddings, birthdays, and events.",
                "is_active":True,
                "is_out_of_stock":False,
                "sort_order":2,
            }
        )

        bc, _ = Product.objects.update_or_create(
            category=business,
            slug="premium-business-card",
            defaults={
                "name":"Premium Business Card",
                "description":"Front/back editable business card design with premium print-ready layout.",
                "price":49,
                "width":1050,
                "height":600,
                "is_active":True,
                "is_out_of_stock":False,
            }
        )
        inv, _ = Product.objects.update_or_create(
            category=invites,
            slug="classic-invitation",
            defaults={
                "name":"Classic Invitation",
                "description":"Editable invitation card template.",
                "price":69,
                "width":800,
                "height":1000,
                "is_active":True,
                "is_out_of_stock":False,
            }
        )

        DesignTemplate.objects.update_or_create(
            product=bc,
            name="Luxury Navy Gold Business Card",
            defaults={"json_data": {"pages": [{"background": "#0b1230", "objects": [{"type": "rect", "x": 0, "y": 0, "w": 1050, "h": 600, "fill": "#0b1230", "locked": True}, {"type": "rect", "x": 40, "y": 40, "w": 970, "h": 520, "fill": "transparent", "stroke": "#c8a45d", "strokeWidth": 4}, {"type": "circle", "x": 145, "y": 140, "r": 54, "fill": "#c8a45d"}, {"type": "text", "x": 230, "y": 115, "text": "ZENVIBE", "fontSize": 56, "font": "Arial", "fill": "#ffffff", "bold": True}, {"type": "text", "x": 232, "y": 180, "text": "Premium Printing & Design", "fontSize": 24, "font": "Arial", "fill": "#c8a45d"}, {"type": "text", "x": 230, "y": 330, "text": "Phone: 457815486464", "fontSize": 28, "font": "Arial", "fill": "#ffffff"}, {"type": "text", "x": 230, "y": 375, "text": "Email: zenvibe@example.com", "fontSize": 28, "font": "Arial", "fill": "#ffffff"}, {"type": "text", "x": 230, "y": 420, "text": "Timing: 9 AM - 5 PM", "fontSize": 28, "font": "Arial", "fill": "#ffffff"}]}, {"background": "#ffffff", "objects": [{"type": "rect", "x": 0, "y": 0, "w": 1050, "h": 600, "fill": "#ffffff", "locked": True}, {"type": "rect", "x": 60, "y": 60, "w": 930, "h": 480, "fill": "#f5f7fb", "stroke": "#c8a45d", "strokeWidth": 3}, {"type": "text", "x": 330, "y": 230, "text": "www.zenvibe.ca", "fontSize": 44, "font": "Arial", "fill": "#0b1230", "bold": True}, {"type": "text", "x": 360, "y": 300, "text": "Scan \u2022 Print \u2022 Customize", "fontSize": 26, "font": "Arial", "fill": "#6b7280"}]}]}, "is_active": True}
        )
        DesignTemplate.objects.update_or_create(
            product=inv,
            name="Warm Minimal Invitation",
            defaults={"json_data": {"pages": [{"background": "#fff7ed", "objects": [{"type": "rect", "x": 0, "y": 0, "w": 800, "h": 1000, "fill": "#fff7ed", "locked": True}, {"type": "text", "x": 210, "y": 130, "text": "You're Invited", "fontSize": 58, "font": "Georgia", "fill": "#9a3412", "bold": True}, {"type": "text", "x": 255, "y": 245, "text": "To Celebrate With Us", "fontSize": 32, "font": "Arial", "fill": "#7c2d12"}, {"type": "text", "x": 215, "y": 430, "text": "Saturday, 7 PM", "fontSize": 42, "font": "Arial", "fill": "#111827"}, {"type": "text", "x": 175, "y": 500, "text": "Zenvibe Event Hall", "fontSize": 36, "font": "Arial", "fill": "#111827"}]}]}, "is_active": True}
        )

        self.stdout.write(self.style.SUCCESS("Demo data added successfully."))
