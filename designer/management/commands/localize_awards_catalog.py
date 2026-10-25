import csv
import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from designer.models import Category, Product, ProductImage, ProductPrintArea, ProductPrintSurface


# Source catalogue IDs are snapshot identifiers only. They are NEVER assumed
# to equal the current database Product.pk.
CANONICAL_AWARD_SOURCE_IDS = {
    494,495,499,502,504,507,508,509,511,512,513,514,515,516,517,518,519,520,
    521,524,526,527,528,529,530,534,535,536,537,538,541,573,581,586,589,595,
    601,608,619,626,656,657,658,659,660,661,662,663,664,
}

ALIASES = {
    "certificatewithframe": "personalizedcertificatewithframe",
    "crystalawardtrophymarblebase": "premiumcrystalawardtrophywithmarblebase",
    "customcoppermetalcrowncrystalglassmedalswithribbon": "custommetalcrowncrystalglassmedalwithribbon",
    "customroundmetalglassmedalbronze": "roundmetalglassmedal",
    "customsquarewoodencertificateplaque": "customsquarewoodencertificateplaquewith16cmroundgoldplate",
    "customizedcreativecrystaltrophy": "customizedcreativecrystalawardpremiumengravedaward",
    "elegantgoldfinishedplasticaward31cm": "elegantgoldfinishedplastictrophy31cm",
    "metalchampioncuptrophydesign": "goldmetalchampioncuptrophy",
    "platedmetalgrandtrophycup": "goldplatedmetalgrandtrophycupforsportscompetitions",
    "goldenunityhandtrophy": "goldenunityhandtrophycanadaresincrystalleadershipaward",
    "golfplasticrecognitiontrophy31cm": "plasticrecognitiontrophy31cm",
    "moderngoldgolfswingtrophyoncrystalbase768x1024": "golfswingtrophyoncrystalbase",
    "personalizedstarborderglassmedalsbronze": "personalizedstarborderglassmedal",
    "ballinhand": "goldresinhandcrystalglobetrophypremiumaward",
    "3starresinwithcrystalbase": "customgoldstarresinawardpremiumengravedaward",
    "mirrorfinishingaward": "purplecrystalawardpremiumrecognitiontrophy",
    "roundcrystalcertificateofexcellenceawardwithgoldbasecanada": "roundcrystalcertificateofexcellenceawardelegantrecognitiontrophy",
    "premiumresintrophy": "premiumresintrophyuniquecustomaward",
}


def norm(value):
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def download(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 ZenVibe catalogue localizer"})
    with urlopen(req, timeout=30) as res:
        return res.read(), (res.headers.get_content_type() or "")


def extension(url, content_type):
    ext = Path(urlparse(url).path).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ext
    return mimetypes.guess_extension(content_type) or ".bin"


class Command(BaseCommand):
    help = (
        "One-time Awards localization. Copies canonical Award source images into local MEDIA, "
        "stores canonical source identity in the DB, and leaves runtime independent of zenvibe.ca."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write DB/media changes.")
        parser.add_argument("--download-images", action="store_true", help="Copy canonical main images to local MEDIA.")
        parser.add_argument("--disable-legacy", action="store_true", help="Disable unmatched Award/Crystal Award storefront records.")
        parser.add_argument("--timeout-ok", action="store_true", help="Continue if an individual source image cannot be downloaded.")
        parser.add_argument("--repair-missing-images", action="store_true", help="Restore missing Award media files only; preserve all existing product data.")

    def repair_missing_images(self):
        """Repair missing media for localized Awards without modifying catalogue records."""
        repaired = 0
        missing_source = 0
        failed = 0
        intact = 0
        products = Product.objects.filter(category__name__icontains="award").select_related("category")
        for product in products.iterator():
            attrs = product.source_attributes if isinstance(product.source_attributes, dict) else {}
            if not attrs.get("source_localized"):
                continue
            current_name = product.image.name if product.image else ""
            if current_name and default_storage.exists(current_name):
                intact += 1
                continue
            source_url = str(attrs.get("source_main_image_url") or "").strip()
            if not source_url.startswith(("https://", "http://")):
                missing_source += 1
                self.stderr.write(f"NO SOURCE: {product.pk} {product.name}")
                continue
            try:
                data, ctype = download(source_url)
                if not ctype.startswith("image/") or not data:
                    raise ValueError(f"Not an image response: {ctype}")
                from PIL import Image
                import io
                with Image.open(io.BytesIO(data)) as im:
                    im.verify()
                digest = hashlib.sha1(data).hexdigest()[:12]
                ext = extension(source_url, ctype)
                if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                    raise ValueError(f"Unsupported image extension: {ext}")
                name = f"awards/{slugify(product.name)}-{digest}{ext}"
                stored_name = default_storage.save(name, ContentFile(data))
                product.image.name = stored_name
                product.save(update_fields=["image"])
                repaired += 1
                self.stdout.write(f"RESTORED: {product.pk} {stored_name}")
            except Exception as exc:
                failed += 1
                self.stderr.write(f"FAILED: {product.pk} {product.name}: {exc}")
        self.stdout.write(
            f"Awards media: intact={intact}, restored={repaired}, "
            f"no_source={missing_source}, failed={failed}"
        )

    def handle(self, *args, **o):
        csv_path = Path(settings.BASE_DIR) / "designer" / "management" / "commands" / "zenvibe_product_mapping.csv"
        if not csv_path.exists():
            raise CommandError(f"Missing mapping CSV: {csv_path}")

        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            all_rows = list(csv.DictReader(fh))
        rows = []
        for r in all_rows:
            try:
                sid = int(r.get("local_id") or 0)
            except ValueError:
                continue
            if r.get("type") == "product" and r.get("status") == "MATCHED" and sid in CANONICAL_AWARD_SOURCE_IDS:
                rows.append(r)
        if len(rows) != 49:
            raise CommandError(f"Expected 49 canonical Awards in mapping CSV, found {len(rows)}. Refusing partial sync.")

        if o["repair_missing_images"]:
            self.repair_missing_images()
            return

        products = list(
            Product.objects.filter(category__name__icontains="award")
            .select_related("category").order_by("id")
        )
        by_name = {norm(r["local_name"]): r for r in rows}
        by_slug = {norm(r["local_slug"]): r for r in rows}
        by_url_slug = {norm(r["live_url"].rstrip("/").split("/")[-1]): r for r in rows}

        matches = {}
        for p in products:
            attrs = p.source_attributes if isinstance(p.source_attributes, dict) else {}
            keys = [ALIASES.get(norm(p.name)), norm(p.name), norm(p.slug)]
            source_url = str(attrs.get("source_url") or attrs.get("live_url") or "")
            if source_url:
                keys.append(norm(source_url.rstrip("/").split("/")[-1]))
            row = next((by_name.get(k) or by_slug.get(k) or by_url_slug.get(k) for k in keys if k), None)
            if row:
                matches[p.id] = row

        # Keep one local product per canonical source. Prefer exact canonical name.
        source_to_ids = {}
        for pid, row in matches.items():
            source_to_ids.setdefault(int(row["local_id"]), []).append(pid)
        keep = {}
        duplicate_ids = set()
        for sid, ids in source_to_ids.items():
            row = next(r for r in rows if int(r["local_id"]) == sid)
            ranked = sorted(ids, key=lambda pid: (
                norm(next(p.name for p in products if p.id == pid)) != norm(row["local_name"]), pid
            ))
            keep[sid] = ranked[0]
            duplicate_ids.update(ranked[1:])

        missing = [r for r in rows if int(r["local_id"]) not in keep]
        unmatched = [p for p in products if p.id not in matches]

        self.stdout.write(f"Canonical Awards: {len(rows)}")
        self.stdout.write(f"Matched canonical Awards: {len(keep)}")
        self.stdout.write(f"Missing canonical Awards: {len(missing)}")
        self.stdout.write(f"Legacy/unmatched local rows: {len(unmatched)}")
        self.stdout.write(f"Duplicate local rows: {len(duplicate_ids)}")

        if not o["apply"]:
            self.stdout.write(self.style.WARNING("REPORT ONLY. Add --apply when ready."))
            for r in missing:
                self.stdout.write(f"MISSING {r['local_name']}")
            return

        with transaction.atomic():
            # Missing canonical products are created from the checked-in catalogue snapshot.
            # They deliberately start with conservative/default commerce fields; no remote
            # page is required at runtime and no guessed editor geometry is created.
            if missing:
                category = (
                    Category.objects.filter(name__iexact="Awards").first()
                    or Category.objects.filter(name__icontains="award").order_by("id").first()
                )
                if not category:
                    raise CommandError("Awards category does not exist.")

                used_slugs = set(Product.objects.values_list("slug", flat=True))
                for row in missing:
                    base_slug = slugify(row.get("live_url", "").rstrip("/").split("/")[-1] or row["local_name"])
                    slug = base_slug
                    n = 2
                    while slug in used_slugs:
                        slug = f"{base_slug}-{n}"
                        n += 1
                    used_slugs.add(slug)
                    attrs = {
                        "source_product_id": str(row["local_id"]),
                        "source_url": row["live_url"],
                        "source_main_image_url": row["main_image_url"],
                        "source_localized": True,
                        "catalogue_import_pending_details": True,
                    }
                    p = Product.objects.create(
                        category=category,
                        name=row["local_name"],
                        slug=slug,
                        source_attributes=attrs,
                        is_active=True,
                        customizer_mode="awards",
                        editor_layout_mode="legacy",
                        constrain_to_print_area=False,
                        show_product_reference=False,
                    )
                    products.append(p)
                    keep[int(row["local_id"])] = p.id

            # Process the canonical set after any missing local rows were created.
            by_product_id = {p.id: p for p in products}
            for sid, pid in keep.items():
                p = by_product_id[pid]
                row = next(r for r in rows if int(r["local_id"]) == sid)
                attrs = dict(p.source_attributes or {})
                # Historical provenance is stored for audit/admin only. Runtime code
                # must use p.image / ProductImage and must never fetch this URL.
                attrs["source_product_id"] = str(sid)
                attrs["source_url"] = row["live_url"]
                attrs["source_main_image_url"] = row["main_image_url"]
                attrs["source_localized"] = True
                p.name = row["local_name"]
                p.source_attributes = attrs
                p.is_active = True
                p.save(update_fields=["name", "source_attributes", "is_active"])

                if o["download_images"] and row.get("main_image_url"):
                    try:
                        data, ctype = download(row["main_image_url"])
                        digest = hashlib.sha1(data).hexdigest()[:12]
                        ext = extension(row["main_image_url"], ctype)
                        filename = f"awards/{slugify(row['local_name'])}-{digest}{ext}"
                        target = Path(settings.MEDIA_ROOT) / filename
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(data)
                        # Store a MEDIA-relative path. No remote URL is used at runtime.
                        p.image.name = filename.replace("\\", "/")
                        p.save(update_fields=["image"])
                    except Exception as exc:
                        if not o["timeout_ok"]:
                            raise CommandError(f"Image download failed for {p.name}: {exc}")
                        self.stderr.write(f"IMAGE SKIPPED {p.id} {p.name}: {exc}")

            for p in products:
                if p.id in duplicate_ids or (o["disable_legacy"] and p in unmatched):
                    p.is_active = False
                    p.save(update_fields=["is_active"])

        self.stdout.write(self.style.SUCCESS(
            "Awards localized. Canonical products are in the local DB; runtime product images are local MEDIA files; DesignTemplate data was untouched."
        ))
        self.stdout.write(self.style.WARNING(
            "No unverified ruler/print geometry was invented. Configure product-specific workspace/print areas in Admin; verified configurations remain local DB data."
        ))
