import re
import zipfile
from pathlib import Path
from difflib import SequenceMatcher

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
BAD_WORDS = {
    "gallery": 35, "side": 45, "back": 55, "view": 12, "box": 18,
    "scaled": 6, "size": 20, "banner": 60,
}
ALIASES = {
    # Canonical product name -> preferred clean/front asset basename.
    "custom design crystal glass award plaque": "Custom-Design-Crystal-Glass-Award-Plaque.png",
    "achievement crystal award custom engraved recognition trophy": "Achievement-Crystal-Award.png",
    "blue white artistic crystal award premium custom engraved glass trophy": "Blue-trophy-768x768-1.jpg",
    "crystal appreciation trophy": "Crystal-Appreciation-Trophy-1.webp",
    "custom crystal diamond award premium engraved awards": "Crystal-Diamond-Award.png",
    "custom crystal star award premium engraved crystal awards": "Custom-Crystal-Star-Award-Trophy.png",
    "custom engraved wooden plaque": "Custom-Engraved-Wooden-Plaque.png",
    "custom five pointed star crystal award": "Blue-Five-point-star-award.png",
    "custom gold plastic trophy": "Custom-Gold-Plastic-Trophy.png",
    "custom square wooden certificate plaque": "Custom-Square-Wooden-Certificate-Plaque.png",
    "customized creative crystal award": "Customized-Creative-Crystal-Trophy.png",
    "diamond cut crystal award": "Diamond-Cut-Crystal-Award-1.webp",
    "elegant gold finished plastic trophy 31 cm": "Elegant-Gold-finished-Plastic-Award-31-cm.png",
    "gold metal champion cup trophy": "Gold-Metal-Champion-Cup-Trophy-design.png",
    "gold plated metal grand trophy cup for sports competitions": "Gold-Plated-Metal-Grand-Trophy-Cup.png",
    "golden plastic award trophy": "Golden-Plastic-Award-Trophy.png",
    "golden unity hand trophy canada": "Golden-Unity-Hand-Trophy-1.png",
    "plastic recognition trophy 31 cm": "Plastic-Recognition-Trophy.png",
    "premium amber crystal apex trophy": "Premium-Amber-Crystal-Apex-Trophy.png",
    "premium crystal ball trophy": "Premium-Crystal-Ball-Trophy.png",
    "premium crystal star blade trophy modern recognition award": "Premium-Crystal-Star-Blade-Trophy-2.png",
    "crystal diamond cut silver medal premium custom engraved award": "Silver-diamond-cut.png",
    "crystal diamond cut sports medal premium custom engraved award": "Medal-gold.png",
    "custom engraved wooden plaque personalized recognition appreciation award": "Custom-Engraved-Wooden-Plaque.png",
    "custom five pointed star crystal award premium engraved award": "Blue-Five-point-star-award.png",
    "custom gold plastic trophy personalized trophy": "Custom-Gold-Plastic-Trophy.png",
    "premium crystal award trophy with marble base": "crystal-award-trophy-marble-base-1.png",
    "custom metal crown crystal glass medal with ribbon": "Custom-Gold-Metal-Crown-Crystal-Glass-Medals-with-Ribbon.png",
    "round metal glass medal": "Custom-Round-Metal-Glass-Medal-Gold.png",
    "custom square wooden certificate plaque with 16cm round gold plate": "Custom-Square-Wooden-Certificate-Plaque.png",
    "customized creative crystal award premium engraved award": "Customized-Creative-Crystal-Trophy.png",
    "elegant gold victory trophy": "elegant-gold-victory-trophy-1.webp",
    "golden unity hand trophy canada resin crystal leadership award": "Golden-Unity-Hand-Trophy-1.png",
    "golf swing trophy on crystal base": "Modern-Gold-Golf-Swing-Trophy-on-Crystal-Base.png",
    "personalized star border glass medal": "Personalized-Star-Border-Glass-Medals-Gold.png",
    "premium amber crystal apex trophy custom engraved award": "Premium-Amber-Crystal-Apex-Trophy.png",
    "silver plated metal championship trophy 63cm": "Gold-Silver-Metal-Championship-Trophy63cm-1.webp",
    "gold star glass crystal award": "gold-star-glass-crystal-award-1.webp",
    "plastic trophy awards for ceremonies sports competitions personalized trophy": "Plastic-Trophy-Awards-for-Ceremonies-Sports-Competitions.png",
    "gold silver metal championship trophy 63cm": "Gold-Silver-Metal-Championship-Trophy63cm-1.webp",
    "wooden rectangle plaque with blue diamond crystal custom engraved trophy": "Wooden-Rectangle-with-Multi-Color-Diamond-Plaque.png",
    "gold education trophy 37 cm premium school academic award": "Gold-Education-Award.png",
    "premium crystal creative engraved award modern custom recognition trophy": "Premium-Crystal-Creative-Engraved-Awards.png",
    "premium gold finished plaque custom engraved recognition plaque": "Gold-Metal-Plaque.png",
    "premium gold championship trophy cup": "Premium-Gold-Championship-Trophy-Cup.png",
}


def norm(value):
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def stem_norm(path):
    return norm(Path(path).stem)


def score(product_name, filename):
    p = norm(product_name)
    f = stem_norm(filename)
    ratio = SequenceMatcher(None, p, f).ratio() * 100
    pt = set(p.split())
    ft = set(f.split())
    overlap = (len(pt & ft) / max(1, len(pt))) * 100
    value = ratio * 0.62 + overlap * 0.38
    low = norm(filename)
    for word, penalty in BAD_WORDS.items():
        if word in low.split():
            value -= penalty
    # Prefer PNG clean artwork where otherwise comparable.
    if str(filename).lower().endswith(".png"):
        value += 3
    return value


class Command(BaseCommand):
    help = "Import clean/front-facing Award editor references from the supplied Awards ZIP. Store them locally; never replace storefront Product.image."

    def add_arguments(self, parser):
        parser.add_argument("--zip", dest="zip_path", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--min-score", type=float, default=48.0)
        parser.add_argument("--repair-storefront-images", action="store_true")

    def handle(self, *args, **opts):
        zip_path = Path(opts["zip_path"]).expanduser()
        if not zip_path.exists():
            raise CommandError(f"ZIP not found: {zip_path}")

        products = []
        qs = Product.objects.filter(category__name__icontains="award", is_active=True).order_by("id")
        for p in qs:
            attrs = p.source_attributes if isinstance(p.source_attributes, dict) else {}
            if attrs.get("source_localized") is True and attrs.get("source_product_id"):
                products.append(p)
        if len(products) != 49:
            raise CommandError(f"Expected 49 active canonical Awards; found {len(products)}.")

        with zipfile.ZipFile(zip_path) as zf:
            members = [
                n for n in zf.namelist()
                if not n.endswith("/") and Path(n).suffix.lower() in IMAGE_EXTS
            ]
            by_base = {Path(n).name.lower(): n for n in members}

            choices = []
            for p in products:
                alias = ALIASES.get(norm(p.name))
                chosen = None
                chosen_score = -999.0
                if alias and alias.lower() in by_base:
                    chosen = by_base[alias.lower()]
                    chosen_score = 1000.0
                else:
                    # Never guess an editor reference. Only accept an exact
                    # normalized filename/product-name match. Angled/wrong
                    # product photography is worse than leaving it unconfigured.
                    exact = [
                        n for n in members
                        if stem_norm(n) == norm(p.name)
                    ]
                    if exact:
                        chosen = sorted(exact, key=lambda n: (
                            any(w in stem_norm(n).split() for w in BAD_WORDS),
                            Path(n).suffix.lower() != ".png",
                            len(Path(n).name),
                        ))[0]
                        chosen_score = 999.0
                choices.append((p, chosen, chosen_score))

            missing = [(p, sc) for p, n, sc in choices if not n]
            self.stdout.write(f"Canonical Awards: {len(products)}")
            self.stdout.write(f"Front/editor references matched: {len(choices) - len(missing)}")
            self.stdout.write(f"Needs manual reference: {len(missing)}")
            for p, n, sc in choices:
                if n:
                    self.stdout.write(f"MATCH {p.id}: {p.name} <- {Path(n).name} ({sc:.1f})")
                else:
                    self.stdout.write(self.style.WARNING(f"NO MATCH {p.id}: {p.name} ({sc:.1f})"))

            if not opts["apply"]:
                self.stdout.write(self.style.WARNING("REPORT ONLY. Re-run with --apply after reviewing matches."))
                return

            # Product 34 and all other matches are copied into MEDIA as dedicated
            # editor references. Storefront/marketing Product.image is untouched.
            with transaction.atomic():
                applied = 0
                storefront_repaired = 0
                for p, member, sc in choices:
                    if not member:
                        continue
                    data = zf.read(member)
                    ext = Path(member).suffix.lower()
                    safe_slug = re.sub(r"[^a-z0-9-]+", "-", (p.slug or str(p.id)).lower()).strip("-")
                    target = f"award_editor_references/{safe_slug}{ext}"
                    if p.editor_reference_image:
                        try:
                            p.editor_reference_image.delete(save=False)
                        except Exception:
                            pass
                    p.editor_reference_image.save(target, ContentFile(data), save=False)
                    p.show_product_reference = True
                    # Keep already configured mode/geometry. This command changes
                    # only the visual reference asset.
                    p.save(update_fields=["editor_reference_image", "show_product_reference"])
                    applied += 1

                    if opts["repair_storefront_images"]:
                        current_name = str(getattr(p.image, "name", "") or "")
                        try:
                            exists = bool(current_name) and p.image.storage.exists(current_name)
                        except Exception:
                            exists = False
                        if not exists:
                            p.image.save(f"awards/{safe_slug}{ext}", ContentFile(data), save=False)
                            p.save(update_fields=["image"])
                            storefront_repaired += 1

            self.stdout.write(self.style.SUCCESS(
                f"Imported {applied} local Award editor references. Repaired {storefront_repaired} missing storefront images."
            ))
