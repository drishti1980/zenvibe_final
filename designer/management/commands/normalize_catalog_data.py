from django.core.management.base import BaseCommand
from django.db import transaction
from designer.models import Category, Product, ProductImage, DesignTemplate


EDITABLE_TYPES = {"text", "i-text", "textbox", "rect", "circle", "ellipse", "triangle", "polygon", "line", "path", "image"}


def normalize_template(data):
    if not isinstance(data, dict):
        return data, False
    pages = data.get("pages")
    if not isinstance(pages, list):
        return data, False
    changed = False
    for page in pages:
        objs = page.get("objects") if isinstance(page, dict) else None
        if not isinstance(objs, list):
            continue
        cleaned, seen = [], set()
        for obj in objs:
            if not isinstance(obj, dict):
                changed = True
                continue
            if obj.get("autoInvitationField") or obj.get("autoInvitationCover"):
                changed = True
                continue
            oid = str(obj.get("id") or obj.get("objectId") or "")
            fingerprint = (oid, obj.get("type"), obj.get("x", obj.get("left")), obj.get("y", obj.get("top")), obj.get("text"))
            if oid and fingerprint in seen:
                changed = True
                continue
            seen.add(fingerprint)
            protected = bool(
                obj.get("backgroundAsset")
                or obj.get("exactVisualMaster")
                or obj.get("isBase")
                or (obj.get("id") in {"background", "bg", "bg2"} and obj.get("locked"))
            )
            if obj.get("type") in EDITABLE_TYPES and not protected:
                for key, val in {"customerEditable": True, "selectable": True, "evented": True}.items():
                    if obj.get(key) is not val:
                        obj[key] = val
                        changed = True
                if obj.get("type") in {"text", "i-text", "textbox"} and obj.get("editable") is not True:
                    obj["editable"] = True
                    changed = True
            cleaned.append(obj)
        page["objects"] = cleaned
    return data, changed


def product_default_area(product):
    ancestry = []
    category = product.category
    seen = set()
    while category and category.pk not in seen:
        seen.add(category.pk)
        ancestry.append((category.slug or "").lower())
        category = category.parent
    text = " ".join(ancestry) + " " + (product.name or "").lower()

    if any(k in text for k in ["business-card", "invitation", "flyer", "brochure", "signs-print"]):
        return 0, 0, 100, 100
    if "pen" in text:
        return 20, 38, 60, 22
    if any(k in text for k in ["t-shirt", "shirt", "apparel", "sportswear", "hoodie", "jacket"]):
        return 27, 22, 46, 52
    if any(k in text for k in ["bag", "backpack", "tote", "crossbody"]):
        return 22, 23, 56, 52
    if any(k in text for k in ["drinkware", "mug", "tumbler", "bottle"]):
        return 24, 23, 52, 54
    if any(k in text for k in ["award", "troph", "plaque", "medal"]):
        return 30, 60, 40, 24
    if "cap" in text:
        return 28, 33, 44, 28
    if "notebook" in text:
        return 18, 15, 64, 70
    if any(k in text for k in ["banner", "flag", "table-cover", "canopy", "trade-show"]):
        return 10, 10, 80, 80
    if any(k in text for k in ["gift-set", "promotional", "umbrella", "keychain"]):
        return 22, 25, 56, 50
    return 25, 25, 50, 50


class Command(BaseCommand):
    help = "Normalize ZenVibe catalogue hierarchy, editable template data and per-product 3D print areas without deleting customer designs."

    @transaction.atomic
    def handle(self, *args, **opts):
        updated_templates = 0
        for template in DesignTemplate.objects.all().iterator():
            data, changed = normalize_template(template.json_data or {})
            if changed:
                template.json_data = data
                template.save(update_fields=["json_data", "updated_at"])
                updated_templates += 1

        # Current ZenVibe top-level catalogue structure.
        top_order = [
            ("banners-displays", 10), ("custom-apparel", 20), ("awards", 30),
            ("promotional-products", 40), ("corporate-gift-set", 50), ("drinkware", 60),
            ("custom-notebooks", 70), ("bags", 80), ("marketing-materials", 90), ("pens", 100),
        ]
        for slug, order in top_order:
            Category.objects.filter(slug=slug).update(parent=None, sort_order=order, is_active=True, is_out_of_stock=False)

        marketing = Category.objects.filter(slug="marketing-materials").first()
        business = Category.objects.filter(slug="business-cards").first()
        invitations = Category.objects.filter(slug="invitations").first()
        if marketing:
            Category.objects.filter(slug="business-cards").update(parent=marketing, sort_order=10, is_active=True)
            Category.objects.filter(slug="invitations").update(parent=marketing, sort_order=20, is_active=True)
        if business:
            Category.objects.filter(slug="standard-business-cards").update(parent=business, sort_order=10, is_active=True)
            Category.objects.filter(slug="premium-business-cards").update(parent=business, sort_order=20, is_active=True)
        if invitations:
            invitation_slugs = [
                "event-invitations", "wedding-invitations", "engagement-invitations", "birthday-invitations",
                "baby-shower-invitations", "anniversary-invitations", "graduation-invitations",
                "housewarming-invitations", "corporate-invitations", "festive-invitations", "kids-family-invitations",
            ]
            for index, slug in enumerate(invitation_slugs, 1):
                Category.objects.filter(slug=slug).update(parent=invitations, sort_order=index * 10, is_active=True)

        Product.objects.filter(slug__in=["classic-invitation", "invitation-cards", "demo", "business-card", "luxury-business-card"]).update(is_active=False)
        Product.objects.filter(category__slug__in=[
            "wedding-invitations", "engagement-invitations", "birthday-invitations", "baby-shower-invitations",
            "anniversary-invitations", "graduation-invitations", "housewarming-invitations", "corporate-invitations",
            "festive-invitations", "kids-family-invitations", "standard-business-cards", "premium-business-cards",
        ]).update(customizer_mode="editor")

        area_products = 0
        area_images = 0
        for product in Product.objects.select_related("category__parent").all().iterator():
            values = [product.print_left_pct, product.print_top_pct, product.print_width_pct, product.print_height_pct]
            if any(v is None for v in values):
                left, top, width, height = product_default_area(product)
                product.print_left_pct = left
                product.print_top_pct = top
                product.print_width_pct = width
                product.print_height_pct = height
                product.save(update_fields=["print_left_pct", "print_top_pct", "print_width_pct", "print_height_pct"])
                area_products += 1
            for image in product.angle_images.all():
                image_values = [image.print_left_pct, image.print_top_pct, image.print_width_pct, image.print_height_pct]
                if any(v is None for v in image_values):
                    image.print_left_pct = product.print_left_pct
                    image.print_top_pct = product.print_top_pct
                    image.print_width_pct = product.print_width_pct
                    image.print_height_pct = product.print_height_pct
                    image.save(update_fields=["print_left_pct", "print_top_pct", "print_width_pct", "print_height_pct"])
                    area_images += 1

        self.stdout.write(self.style.SUCCESS(
            f"Catalogue normalized: {updated_templates} template JSON records cleaned, "
            f"{area_products} product and {area_images} angle print areas configured."
        ))
