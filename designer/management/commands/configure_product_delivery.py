from copy import deepcopy
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product


KEYS = (
    "fastest_delivery_enabled",
    "fastest_delivery_min_business_days",
    "fastest_delivery_max_business_days",
)

# ----------------------------------------------------------------------
# DELIVERY PROFILES
# ----------------------------------------------------------------------
# These are operational defaults by product family, not scraped/claimed
# zenvibe.ca values. Product-level values always take precedence.
#
# Adjust these defaults once if your production lead times change.
PROFILES = {
    "print": (3, 6),
    "small_promo": (4, 7),
    "drinkware": (5, 8),
    "awards": (5, 8),
    "bags": (5, 9),
    "apparel": (7, 12),
    "gift_sets": (7, 12),
    "display": (5, 9),
    "canopy": (5, 9),
    "default": (5, 9),
}

PROFILE_KEYWORDS = {
    "canopy": (
        "canopy", "tent", "back wall", "side wall", "canopy frame",
    ),
    "display": (
        "banner", "backdrop", "display", "table cover", "table runner",
        "table skirt", "flag", "roll up", "rollup", "a frame", "sign box",
        "door sign", "name plate",
    ),
    "apparel": (
        "t-shirt", "t shirt", "hoodie", "jacket", "jersey", "sportswear",
        "uniform", "cap", "embroidered",
    ),
    "gift_sets": (
        "gift set", "gift box", "gift bundle", "corporate gift",
        "notebook pen set",
    ),
    "bags": (
        "bag", "backpack", "tote", "drawstring", "fanny", "waist bag",
    ),
    "awards": (
        "award", "trophy", "medal", "plaque", "crystal", "champion",
        "certificate",
    ),
    "drinkware": (
        "mug", "bottle", "tumbler", "thermos",
    ),
    "print": (
        "business card", "invitation", "flyer", "brochure", "ticket",
        "calendar", "wristband",
    ),
    "small_promo": (
        "pen", "keychain", "lanyard", "coaster", "bottle opener",
        "mouse pad", "freshener", "golf ball", "badge", "cart token",
        "door hanger", "stress ball",
    ),
}


def _text_for(product):
    category = getattr(product, "category", None)
    parent = getattr(category, "parent", None) if category else None
    return " ".join(
        str(x or "")
        for x in (
            product.name,
            getattr(category, "name", ""),
            getattr(parent, "name", ""),
        )
    ).lower()


def _profile_for(product):
    haystack = _text_for(product)
    # Ordering matters: canopy before display, gift_sets before small promo.
    for profile in (
        "canopy", "gift_sets", "apparel", "display", "bags",
        "awards", "drinkware", "print", "small_promo",
    ):
        if any(word in haystack for word in PROFILE_KEYWORDS[profile]):
            return profile
    return "default"


class Command(BaseCommand):
    help = (
        "Configure Fastest Delivery in Product.source_attributes only. "
        "Supports per-product settings and safe catalogue population by product family."
    )

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--min-days", type=int)
        parser.add_argument("--max-days", type=int)
        parser.add_argument("--enable", action="store_true")
        parser.add_argument("--disable", action="store_true")
        parser.add_argument("--only-missing", action="store_true")
        parser.add_argument(
            "--populate-all",
            action="store_true",
            help="Populate missing active products using product-family delivery profiles.",
        )
        parser.add_argument(
            "--overwrite-configured",
            action="store_true",
            help="With --populate-all, also replace products already configured.",
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **o):
        if o["enable"] and o["disable"]:
            raise CommandError("Use either --enable or --disable.")

        for key in ("min_days", "max_days"):
            if o[key] is not None and o[key] < 0:
                raise CommandError(f"--{key.replace('_', '-')} cannot be negative.")

        if (
            o["min_days"] is not None
            and o["max_days"] is not None
            and o["min_days"] > o["max_days"]
        ):
            raise CommandError("--min-days cannot exceed --max-days.")

        if o["populate_all"]:
            return self._populate_all(o)

        requested = (
            o["enable"] or o["disable"]
            or o["min_days"] is not None
            or o["max_days"] is not None
        )

        if requested and not o["product_id"]:
            raise CommandError(
                "Manual delivery values require --product-id. "
                "Use --populate-all for catalogue population."
            )

        qs = Product.objects.all().order_by("id")
        qs = (
            qs.filter(pk=o["product_id"])
            if o["product_id"]
            else qs.filter(is_active=True)
        )

        if not requested:
            for p in qs.iterator():
                a = p.source_attributes if isinstance(p.source_attributes, dict) else {}
                status = (
                    "CONFIGURED"
                    if (
                        a.get(KEYS[0]) is True
                        and a.get(KEYS[1]) is not None
                        and a.get(KEYS[2]) is not None
                    )
                    else "MISSING"
                )
                self.stdout.write(
                    f"{p.id} | {status} | {p.name} | "
                    f"enabled={a.get(KEYS[0])} | "
                    f"days={a.get(KEYS[1])} - {a.get(KEYS[2])}"
                )
            self.stdout.write("Audit only. Nothing changed.")
            return

        changed = skipped = 0
        with transaction.atomic():
            for p in qs.iterator():
                original = deepcopy(p.source_attributes) if isinstance(p.source_attributes, dict) else {}

                if o["only_missing"] and any(k in original for k in KEYS):
                    skipped += 1
                    continue

                new = deepcopy(original)

                if o["enable"]:
                    new[KEYS[0]] = True
                elif o["disable"]:
                    new[KEYS[0]] = False

                if o["min_days"] is not None:
                    new[KEYS[1]] = int(o["min_days"])
                if o["max_days"] is not None:
                    new[KEYS[2]] = int(o["max_days"])

                lo, hi = new.get(KEYS[1]), new.get(KEYS[2])
                if lo is not None and hi is not None and int(lo) > int(hi):
                    raise CommandError(
                        f"Product {p.id}: minimum days exceeds maximum days."
                    )

                if new == original:
                    skipped += 1
                    continue

                self.stdout.write(
                    f"{p.id} | {p.name} | enabled={new.get(KEYS[0])} | "
                    f"days={new.get(KEYS[1])} - {new.get(KEYS[2])}"
                )

                if o["apply"]:
                    Product.objects.filter(pk=p.pk).update(source_attributes=new)
                changed += 1

            if not o["apply"]:
                transaction.set_rollback(True)

        if o["apply"]:
            self.stdout.write(self.style.SUCCESS(
                f"APPLIED: {changed} updated, {skipped} skipped. "
                "Only delivery configuration was changed."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"PREVIEW ONLY: {changed} would change, {skipped} skipped. Nothing saved."
            ))

    def _populate_all(self, o):
        if (
            o["product_id"]
            or o["enable"]
            or o["disable"]
            or o["min_days"] is not None
            or o["max_days"] is not None
        ):
            raise CommandError(
                "--populate-all cannot be combined with --product-id, --enable, "
                "--disable, --min-days or --max-days."
            )

        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category", "category__parent")
            .order_by("id")
        )

        changed = kept = 0
        profile_counts = {}

        with transaction.atomic():
            for p in qs.iterator():
                original = deepcopy(p.source_attributes) if isinstance(p.source_attributes, dict) else {}

                already_configured = (
                    original.get(KEYS[0]) is True
                    and original.get(KEYS[1]) is not None
                    and original.get(KEYS[2]) is not None
                )

                if already_configured and not o["overwrite_configured"]:
                    kept += 1
                    self.stdout.write(
                        f"{p.id} | KEEP | {p.name} | "
                        f"days={original.get(KEYS[1])} - {original.get(KEYS[2])}"
                    )
                    continue

                profile = _profile_for(p)
                lo, hi = PROFILES[profile]

                new = deepcopy(original)
                new[KEYS[0]] = True
                new[KEYS[1]] = int(lo)
                new[KEYS[2]] = int(hi)

                profile_counts[profile] = profile_counts.get(profile, 0) + 1

                self.stdout.write(
                    f"{p.id} | {profile.upper()} | {p.name} | days={lo} - {hi}"
                )

                if new != original:
                    if o["apply"]:
                        # Critical safety guarantee:
                        # no Product field except source_attributes is written.
                        Product.objects.filter(pk=p.pk).update(source_attributes=new)
                    changed += 1
                else:
                    kept += 1

            if not o["apply"]:
                transaction.set_rollback(True)

        summary = ", ".join(
            f"{name}={count}" for name, count in sorted(profile_counts.items())
        )

        if o["apply"]:
            self.stdout.write(self.style.SUCCESS(
                f"APPLIED: {changed} configured, {kept} preserved. "
                f"Profiles: {summary}. Only delivery configuration was changed."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"PREVIEW ONLY: {changed} would be configured, {kept} preserved. "
                f"Profiles: {summary}. Nothing saved."
            ))
