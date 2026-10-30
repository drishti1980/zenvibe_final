"""ZenVibe product design-surface profiles.

These profiles control the logical customer artwork canvas, not the physical
product-photo print area.  ProductPrintArea remains authoritative for mapping
artwork onto product photographs / 3D views.

The mapping follows ZenVibe's storefront families and keeps a product-specific
width/height as the final fallback so existing catalogue records continue to
work.
"""
from __future__ import annotations


def _ancestry(product):
    slugs, names = [], []
    category = getattr(product, "category", None)
    seen = set()
    while category is not None and getattr(category, "id", None) not in seen:
        seen.add(getattr(category, "id", None))
        slugs.append((getattr(category, "slug", "") or "").lower())
        names.append((getattr(category, "name", "") or "").lower())
        category = getattr(category, "parent", None)
    return slugs, names


def _profile(key, width, height, label, physical=None):
    return {
        "key": key,
        "width": int(width),
        "height": int(height),
        "label": label,
        "physical": physical or "",
    }


CATEGORY_PROFILES = {
    # Banners & Displays
    "custom-banners": _profile("banner-wide", 1500, 500, "Custom banner", "wide-format"),
    "custom-flags": _profile("flag-portrait", 600, 1500, "Custom flag", "portrait-display"),
    "standing-banners": _profile("standing-banner", 650, 1500, "Standing banner", "portrait-display"),
    "canopy-tent": _profile("canopy", 1500, 750, "Canopy / tent panel", "wide-format"),
    "custom-table-covers": _profile("table-cover", 1400, 850, "Table cover", "fabric-panel"),
    "trade-show-displays": _profile("trade-show", 1600, 900, "Trade-show display", "wide-format"),
    "banners-displays": _profile("display-generic", 1400, 800, "Banner / display", "wide-format"),

    # Marketing materials
    "business-cards": _profile("business-card", 1050, 600, "Business card", "3.5 x 2 in"),
    "standard-business-cards": _profile("business-card", 1050, 600, "Standard business card", "3.5 x 2 in"),
    "premium-business-cards": _profile("business-card", 1125, 675, "Premium business card", "3.75 x 2.25 in incl. bleed"),
    "luxury-business-cards": _profile("business-card", 1050, 600, "Luxury business card", "3.5 x 2 in"),
    "invitations": _profile("invitation", 700, 1000, "Invitation", "portrait card"),
    "anniversary-invitations": _profile("invitation", 700, 1000, "Anniversary invitation", "portrait card"),
    "baby-shower-invitations": _profile("invitation", 700, 1000, "Baby shower invitation", "portrait card"),
    "birthday-invitations": _profile("invitation", 700, 1000, "Birthday invitation", "portrait card"),
    "corporate-invitations": _profile("invitation", 700, 1000, "Corporate invitation", "portrait card"),
    "engagement-invitations": _profile("invitation", 700, 1000, "Engagement invitation", "portrait card"),
    "event-invitations": _profile("invitation", 700, 1000, "Event invitation", "portrait card"),
    "festive-invitations": _profile("invitation", 700, 1000, "Festive invitation", "portrait card"),
    "graduation-invitations": _profile("invitation", 700, 1000, "Graduation invitation", "portrait card"),
    "housewarming-invitations": _profile("invitation", 700, 1000, "Housewarming invitation", "portrait card"),
    "kids-family-invitations": _profile("invitation", 700, 1000, "Kids & family invitation", "portrait card"),
    "wedding-invitations": _profile("invitation", 700, 1000, "Wedding invitation", "portrait card"),
    "flyers-brochures": _profile("flyer", 850, 1100, "Flyer / brochure", "portrait print"),
    "signs-print-materials": _profile("sign", 1200, 800, "Sign / print material", "landscape print"),
    "marketing-materials": _profile("marketing", 1000, 800, "Marketing material", "print"),

    # Apparel – dedicated studios still use their own garment coordinates.
    "custom-caps": _profile("cap", 1000, 700, "Cap decoration area", "front panel"),
    "t-shirt": _profile("shirt", 900, 1100, "T-shirt decoration area", "front/back garment"),
    "custom-jackets": _profile("jacket", 900, 1100, "Jacket decoration area", "front/back garment"),
    "custom-sublimated-sportswear": _profile("sportswear", 900, 1100, "Sportswear decoration area", "garment panel"),
    "hoodie": _profile("hoodie", 900, 1100, "Hoodie decoration area", "front/back garment"),
    "custom-apparel": _profile("apparel", 900, 1100, "Apparel decoration area", "garment"),

    # Drinkware – product-photo/side mapping is still handled by drinkware customizer.
    "mugs": _profile("mug", 1200, 500, "Mug wrap", "wrap"),
    "tumblers": _profile("tumbler", 1200, 550, "Tumbler wrap", "wrap"),
    "water-bottles": _profile("bottle", 1100, 600, "Bottle wrap", "wrap"),
    "kids-drinkware": _profile("kids-drinkware", 1000, 600, "Kids drinkware", "wrap/front"),
    "drinkware": _profile("drinkware", 1100, 600, "Drinkware", "wrap/front"),

    # Pens
    "pens": _profile("pen", 1200, 300, "Pen imprint", "barrel imprint"),
    "executive-pens": _profile("pen", 1200, 300, "Executive pen imprint", "barrel imprint"),
    "metal-pens": _profile("pen", 1200, 300, "Metal pen imprint", "barrel imprint"),
    "stylus-pens": _profile("pen", 1200, 300, "Stylus pen imprint", "barrel imprint"),
    "pen-notebook-sets": _profile("pen-set", 1100, 750, "Pen & notebook set", "gift set"),

    # Bags
    "backpacks": _profile("backpack", 850, 1100, "Backpack decoration area", "front panel"),
    "lunch-bags": _profile("lunch-bag", 900, 850, "Lunch bag decoration area", "front panel"),
    "tote-bags": _profile("tote", 900, 1100, "Tote bag decoration area", "front panel"),
    "waist-crossbody-bags": _profile("crossbody", 1200, 750, "Waist / crossbody bag", "front panel"),
    "bags": _profile("bag", 900, 1000, "Bag decoration area", "front panel"),

    # Awards
    "crystal-awards": _profile("award", 800, 1000, "Crystal award", "engraving face"),
    "medals": _profile("medal", 800, 800, "Medal", "medal face"),
    "plaques": _profile("plaque", 850, 1100, "Plaque", "engraving face"),
    "trophies": _profile("trophy", 800, 1000, "Trophy", "plate / face"),
    "awards": _profile("award", 800, 1000, "Award", "engraving face"),

    # Notebooks
    "executive-notebooks": _profile("notebook", 850, 1100, "Executive notebook", "cover"),
    "spiral-notebooks": _profile("notebook", 850, 1100, "Spiral notebook", "cover"),
    "custom-notebooks": _profile("notebook", 850, 1100, "Notebook", "cover"),

    # Corporate gifts
    "bamboo-gift-sets": _profile("gift-set", 1100, 800, "Bamboo gift set", "presentation area"),
    "executive-gift-sets": _profile("gift-set", 1100, 800, "Executive gift set", "presentation area"),
    "welcome-kits": _profile("gift-set", 1100, 800, "Welcome kit", "presentation area"),
    "corporate-gift-set": _profile("gift-set", 1100, 800, "Corporate gift set", "presentation area"),

    # Promotional products
    "keychains": _profile("keychain", 800, 800, "Keychain", "face"),
    "umbrellas": _profile("umbrella", 1000, 850, "Umbrella", "panel"),
    "custom-plates-signs": _profile("plate-sign", 1200, 800, "Plate / sign", "face"),
    "general-promotional-products": _profile("promo", 900, 900, "Promotional product", "print face"),
    "original-site-assets": _profile("promo", 900, 900, "Promotional product", "print face"),
    "promotional-products": _profile("promo", 900, 900, "Promotional product", "print face"),
}


def design_profile_for(product):
    """Return the closest category profile, with sensible product-name overrides."""
    slugs, names = _ancestry(product)
    product_name = (getattr(product, "name", "") or "").lower()

    # Product-name overrides for mixed ZenVibe categories.
    if "feather flag" in product_name or "teardrop flag" in product_name:
        base = _profile("flag-portrait", 600, 1500, "Custom flag", "portrait-display")
    elif "x banner" in product_name or "roll up" in product_name or "roll-up" in product_name:
        base = _profile("standing-banner", 650, 1500, "Standing banner", "portrait-display")
    elif "table runner" in product_name:
        base = _profile("table-runner", 700, 1400, "Table runner", "fabric-panel")
    elif "table cover" in product_name or "table throw" in product_name or "table skirt" in product_name:
        base = _profile("table-cover", 1400, 850, "Table cover", "fabric-panel")
    elif "canopy" in product_name or "tent" in product_name:
        base = _profile("canopy", 1500, 750, "Canopy / tent panel", "wide-format")
    elif "business card" in product_name:
        base = CATEGORY_PROFILES["business-cards"]
    else:
        base = next((CATEGORY_PROFILES[s] for s in slugs if s in CATEGORY_PROFILES), None)

    if base is None:
        width = max(200, int(getattr(product, "width", 1050) or 1050))
        height = max(200, int(getattr(product, "height", 600) or 600))
        base = _profile("product", width, height, "Product artwork", "")

    result = dict(base)
    # Flag die is independent of its rectangular artwork workspace and rulers.
    # The customer editor / exporter use this metadata for the printable clip.
    if "teardrop flag" in product_name or "tear drop flag" in product_name:
        result["print_shape"] = "teardrop"
    result["base_width"] = int(getattr(product, "width", result["width"]) or result["width"])
    result["base_height"] = int(getattr(product, "height", result["height"]) or result["height"])
    result["category_slugs"] = slugs
    result["category_names"] = names
    return result
