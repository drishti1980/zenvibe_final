from django.core.management.base import BaseCommand
from designer.models import Category, Product, DesignTemplate


def txt(id, x, y, text, size, color, font="Arial", bold=False, opacity=1):
    return {
        "id": id, "type": "text", "x": x, "y": y, "text": text,
        "fontSize": size, "font": font, "fill": color, "bold": bold,
        "opacity": opacity, "locked": False, "selectable": True, "editable": True,
    }


def rect(id, x, y, w, h, fill, opacity=1, locked=False, stroke=None, strokeWidth=2, rx=0):
    obj = {"id": id, "type": "rect", "x": x, "y": y, "w": w, "h": h,
           "fill": fill, "opacity": opacity, "locked": locked, "rx": rx, "ry": rx}
    if stroke:
        obj["stroke"] = stroke
        obj["strokeWidth"] = strokeWidth
    return obj


def circle(id, x, y, r, fill, opacity=1):
    return {"id": id, "type": "circle", "x": x, "y": y, "r": r, "fill": fill, "opacity": opacity}


# ---------------------------------------------------------------------------
# NOTEBOOK template — portrait cover design
# ---------------------------------------------------------------------------
def notebook_template(bg, accent, dark, brand, subtitle, W, H):
    cx = W / 2
    objects = [
        rect("bg", 0, 0, W, H, bg, locked=True),
        rect("spine-shadow", 0, 0, 26, H, "#000000", 0.12, True),
        rect("accent-strip", 40, 60, 10, H - 120, accent, 1),
        txt("brand-name", 90, H * 0.42, brand, 50, dark, "Georgia", True),
        txt("subtitle", 92, H * 0.42 + 66, subtitle, 22, "#6b7280", "Arial", False),
        circle("corner-mark", W - 110, 110, 46, accent, 0.9),
        txt("corner-text", W - 132, 92, "N", 40, "#ffffff", "Georgia", True),
        rect("bottom-line", 90, H - 100, W - 180, 3, accent),
        txt("bottom-text", 90, H - 80, "DOT GRID • 120 PAGES", 16, "#8a93a3", "Arial", False),
    ]
    return {"pages": [{"background": bg, "objects": objects}]}


def logo_placeholder_template(bg, panel, accent, W, H, product_label):
    """Mirrors the real product-photo mockups: a dashed logo box centered on the bag colour."""
    box_w, box_h = min(W * 0.62, 520), min(H * 0.22, 220)
    bx, by = (W - box_w) / 2, H * 0.42
    objects = [
        rect("bg", 0, 0, W, H, bg, locked=True),
        rect("panel", W * 0.08, H * 0.08, W * 0.84, H * 0.84, panel, 1),
        rect("logo-box", bx, by, box_w, box_h, "#ffffff", 1, False, "#b7c0cc", 3),
        txt("logo-line1", bx + box_w * 0.18, by + box_h * 0.28, "YOUR", 30, "#6b7280", "Arial", True),
        txt("logo-line2", bx + box_w * 0.18, by + box_h * 0.58, "LOGO HERE", 30, "#6b7280", "Arial", True),
        rect("accent-tab", 0, H - 46, W, 46, accent, 1),
        txt("accent-text", W * 0.06, H - 34, product_label.upper(), 16, "#ffffff", "Arial", True),
    ]
    return {"pages": [{"background": bg, "objects": objects}]}


class Command(BaseCommand):
    help = "Seed the REAL ZenVibe Bags catalogue and Custom Notebooks, each with editable Business-Card-style templates."

    def handle(self, *args, **kwargs):
        # ---------------- BAGS (matches zenvibe.ca/product-category/bags/) ----------------
        bags_cat, _ = Category.objects.get_or_create(
            name="Bags",
            defaults={
                "slug": "bags",
                "icon": "🛍️",
                "description": "Custom bags in Canada — waist bags, backpacks, drawstring bags and promotional logo bags.",
                "is_active": True,
                "is_out_of_stock": False,
                "sort_order": 30,
            },
        )

        # (name, price, width, height, bg, panel, accent, description)
        real_bags = [
            ("Budget Cotton Tote Bag", 7.11, 900, 1100, "#f2ece1", "#ffffff", "#c9a227",
             "Affordable cotton tote bag, printed with your logo."),
            ("Classic Backpack – Durable, Lightweight & Multi-Purpose Travel & School Bag", 19.99, 900, 1150, "#f4c9d6", "#ffffff", "#0f172a",
             "Durable, lightweight backpack for travel and school."),
            ("Crossbody Waist Bag for Men & Women – Stylish Unisex Fanny Pack", 14.99, 1100, 700, "#1f2a44", "#ffffff", "#f36f21",
             "Stylish unisex crossbody waist bag / fanny pack."),
            ("Custom Drawstring Backpack with Logo – Lightweight Promotional Cinch Bag", 3.07, 850, 1100, "#101010", "#ffffff", "#f36f21",
             "Lightweight promotional cinch/drawstring backpack."),
            ("Custom Insulated Lunch Bag with Multiple Pockets", 20.99, 850, 950, "#c22326", "#ffffff", "#0f172a",
             "Insulated lunch bag with multiple pockets."),
            ("Multi-Functional Baby Diaper Bag Backpack – Large Capacity Travel Bag", 99.99, 950, 1150, "#6d8f87", "#ffffff", "#c96b52",
             "Large-capacity multi-functional baby diaper bag backpack."),
            ("Non-Woven Shopper Tote Bag", 2.90, 900, 1100, "#111111", "#ffffff", "#f36f21",
             "Budget-friendly non-woven shopper tote bag."),
            ("Outdoor Leisure Backpack – Multi-Purpose Travel & Hiking Bag", 12.99, 900, 1150, "#8a3b46", "#ffffff", "#1f2937",
             "Multi-purpose travel and hiking backpack."),
            ("Personalized Foil Stamped Paper Bags", 3.99, 800, 1000, "#1f4d3d", "#e9dcb8", "#c9a227",
             "Foil-stamped personalized paper gift bags."),
            ("Unisex Belt Waist Bag- Stylish Fanny Pack", 16.99, 1100, 700, "#151515", "#ffffff", "#f36f21",
             "Stylish unisex belt waist bag / fanny pack."),
        ]

        bag_products_created = []
        for name, price, w, h, bg, panel, accent, desc in real_bags:
            orientation = "landscape" if w > h else "portrait"
            p, _ = Product.objects.get_or_create(
                category=bags_cat, name=name,
                defaults={"description": desc, "price": price, "width": w, "height": h,
                          "orientation": orientation, "is_active": True, "is_out_of_stock": False},
            )
            DesignTemplate.objects.update_or_create(
                product=p, name="Logo Placement — Standard",
                defaults={"json_data": logo_placeholder_template(bg, panel, accent, w, h, name.split("–")[0].split("-")[0][:24]),
                          "is_active": True},
            )
            bag_products_created.append(p)

        # ---------------- CUSTOM NOTEBOOKS ----------------
        notebooks_cat, _ = Category.objects.get_or_create(
            name="Custom notebooks",
            defaults={
                "slug": "custom-notebooks",
                "icon": "📓",
                "description": "Branded hardcover and spiral notebooks for teams, schools and corporate gifting.",
                "is_active": True,
                "is_out_of_stock": False,
                "sort_order": 40,
            },
        )

        notebook_products = [
            ("Custom Hardcover Notebook", "Premium hardcover journal with custom cover design.", 14.99, 900, 1200),
            ("Custom Spiral Notebook", "Spiral-bound notebook, printed front cover.", 9.99, 850, 1100),
        ]
        notebook_products_created = []
        for name, desc, price, w, h in notebook_products:
            p, _ = Product.objects.get_or_create(
                category=notebooks_cat, name=name,
                defaults={"description": desc, "price": price, "width": w, "height": h,
                          "orientation": "portrait", "is_active": True, "is_out_of_stock": False},
            )
            notebook_products_created.append(p)

        notebook_designs = [
            ("Classic Kraft Journal", "#e9dfc9", "#8a5a2b", "#3d2b17", "Borcelle Notes", "Journal & Planner"),
            ("Modern Gradient Cover", "#eef2ff", "#4338ca", "#1e1b4b", "Wardiere Inc.", "Meeting Notebook"),
            ("Minimalist Line Cover", "#ffffff", "#111827", "#111827", "Studio Line", "Ideas & Sketches"),
        ]
        for product in notebook_products_created:
            for title, bg, accent, dark, brand, subtitle in notebook_designs:
                DesignTemplate.objects.update_or_create(
                    product=product, name=title,
                    defaults={"json_data": notebook_template(bg, accent, dark, brand, subtitle, product.width, product.height),
                              "is_active": True},
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(bag_products_created)} real bag products (matching zenvibe.ca) and "
            f"{len(notebook_products_created)} notebook products, each with editable templates "
            f"using the Business Card-style editor."
        ))
