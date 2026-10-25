import hashlib
import html
import json
import mimetypes
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product, ProductImage

CONTENT_FIELDS = (
    "short_description", "description", "product_information",
    "printing_method", "design_guidelines", "printing_guidelines", "faqs",
)
URL_ATTR_RE = re.compile(r'(?P<prefix>\b(?:src|href)\s*=\s*["\'])(?P<url>https?://[^"\']+)(?P<suffix>["\'])', re.I)
CSS_URL_RE = re.compile(r'url\(\s*["\']?(?P<url>https?://[^)"\']+)["\']?\s*\)', re.I)


def norm(value):
    value = unicodedata.normalize("NFKD", html.unescape(str(value or "")))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\b(custom|personalized|printed)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def host_of(url):
    return (urlparse(str(url or "")).hostname or "").lower().lstrip("www.")


def is_legacy_url(url, legacy_host):
    return bool(url) and host_of(url) == legacy_host.lower().lstrip("www.")


def safe_ext(url, content_type=""):
    ext = Path(urlparse(url).path).suffix.lower()
    if ext and len(ext) <= 8:
        return ext
    return mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip()) or ".bin"


class AssetLocalizer:
    def __init__(self, legacy_host, allow_network, timeout=25):
        self.legacy_host = legacy_host.lower().lstrip("www.")
        self.allow_network = allow_network
        self.timeout = timeout
        self.cache = {}
        self.downloaded = []

    def localize(self, url, folder="imported"):
        url = html.unescape(str(url or "").strip())
        if not is_legacy_url(url, self.legacy_host):
            return url
        if url in self.cache:
            return self.cache[url]
        if not self.allow_network:
            raise CommandError(f"Legacy asset still needs downloading: {url}. Run with --download-assets.")

        req = Request(url, headers={"User-Agent": "Mozilla/5.0 ZenVibe migration"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "")
        except Exception as exc:
            raise CommandError(f"Could not download {url}: {exc}") from exc

        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:18]
        stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", Path(urlparse(url).path).stem).strip("-")[:60] or "asset"
        name = f"legacy_import/{folder}/{stem}-{digest}{safe_ext(url, content_type)}"
        if not default_storage.exists(name):
            name = default_storage.save(name, ContentFile(body))
        local_url = default_storage.url(name)
        self.cache[url] = local_url
        self.downloaded.append({"from": url, "to": local_url})
        return local_url

    def clean_html(self, value, folder="richtext"):
        text = str(value or "")

        def attr_repl(match):
            url = match.group("url")
            if is_legacy_url(url, self.legacy_host):
                # Images/files become local. Ordinary page links become non-linked text target '#'.
                path = urlparse(url).path.lower()
                looks_like_asset = bool(Path(path).suffix) or "/uploads/" in path or "/media/" in path
                replacement = self.localize(url, folder) if looks_like_asset else "#"
                return match.group("prefix") + replacement + match.group("suffix")
            return match.group(0)

        text = URL_ATTR_RE.sub(attr_repl, text)

        def css_repl(match):
            url = match.group("url")
            return f"url('{self.localize(url, folder)}')" if is_legacy_url(url, self.legacy_host) else match.group(0)

        text = CSS_URL_RE.sub(css_repl, text)
        # Remove plain-text legacy URLs that may have been pasted into descriptions.
        text = re.sub(rf'https?://(?:www\.)?{re.escape(self.legacy_host)}[^\s<"\']*', "", text, flags=re.I)
        return text


def clean_json(value, localizer):
    if isinstance(value, dict):
        result = {}
        for key, val in value.items():
            # Migration-only metadata must never be persisted to storefront data.
            if key.lower() in {"source_url", "product_url", "legacy_url", "original_url"}:
                continue
            result[key] = clean_json(val, localizer)
        return result
    if isinstance(value, list):
        return [clean_json(v, localizer) for v in value]
    if isinstance(value, str):
        if is_legacy_url(value, localizer.legacy_host):
            path = urlparse(value).path.lower()
            if Path(path).suffix or "/uploads/" in path or "/media/" in path:
                return localizer.localize(value, "attributes")
            return ""
        return localizer.clean_html(value, "attributes")
    return value


class Command(BaseCommand):
    help = "One-time product migration. Copies legacy content/assets locally so storefront runtime is independent."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="zenvibe_catalog.json")
        parser.add_argument("--legacy-host", required=True, help="Old site's hostname, supplied at run time only.")
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--download-assets", action="store_true")
        parser.add_argument("--overwrite-empty-only", action="store_true")
        parser.add_argument("--deactivate-unmatched", action="store_true")
        parser.add_argument("--replace-gallery", action="store_true")
        parser.add_argument("--audit", default="product_migration_audit.json")

    def handle(self, *args, **opts):
        if opts["apply"] == opts["dry_run"]:
            raise CommandError("Choose exactly one of --dry-run or --apply.")
        if opts["apply"] and not opts["download_assets"]:
            raise CommandError("For final migration use --apply --download-assets so no legacy asset URLs survive.")

        source = Path(opts["source"]).resolve()
        if not source.exists():
            raise CommandError(f"Snapshot not found: {source}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CommandError(f"Could not read snapshot: {exc}") from exc
        rows = payload.get("products") if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not rows:
            raise CommandError("Snapshot must contain a non-empty products list.")

        by_slug = {norm(r.get("slug")): r for r in rows if isinstance(r, dict) and r.get("slug")}
        by_name = {norm(r.get("name")): r for r in rows if isinstance(r, dict) and r.get("name")}
        qs = Product.objects.all().order_by("id")
        if opts["product_id"]:
            qs = qs.filter(id=opts["product_id"])
            if not qs.exists():
                raise CommandError("Product not found.")

        localizer = AssetLocalizer(opts["legacy_host"], opts["download_assets"] and opts["apply"])
        audit = {"matched": [], "unmatched": [], "deactivated": [], "downloaded_assets": []}
        matched_ids = set()

        with transaction.atomic():
            for product in qs:
                row = by_slug.get(norm(product.slug)) or by_name.get(norm(product.name))
                match_type = "slug" if by_slug.get(norm(product.slug)) is row and row else "name"
                if not row:
                    audit["unmatched"].append({"id": product.id, "name": product.name})
                    self.stdout.write(self.style.WARNING(f"UNMATCHED {product.id}: {product.name}"))
                    continue

                matched_ids.add(product.id)
                changed = []
                for field in CONTENT_FIELDS:
                    if field not in row or row[field] is None:
                        continue
                    if opts["overwrite_empty_only"] and getattr(product, field, ""):
                        continue
                    cleaned = localizer.clean_html(row[field], f"products/{product.id}/content")
                    if getattr(product, field, "") != cleaned:
                        setattr(product, field, cleaned)
                        changed.append(field)

                if "source_attributes" in row and row["source_attributes"] is not None:
                    cleaned_attrs = clean_json(row["source_attributes"], localizer)
                    if product.source_attributes != cleaned_attrs:
                        product.source_attributes = cleaned_attrs
                        changed.append("source_attributes")

                # Main image. Supported snapshot keys: image_url or image.
                main_url = row.get("image_url") or (row.get("image") if isinstance(row.get("image"), str) else "")
                if main_url and is_legacy_url(main_url, localizer.legacy_host):
                    local_url = localizer.localize(main_url, f"products/{product.id}")
                    storage_name = local_url.split(default_storage.base_url, 1)[-1] if hasattr(default_storage, "base_url") and local_url.startswith(default_storage.base_url) else local_url.lstrip("/")
                    if product.image.name != storage_name:
                        product.image.name = storage_name
                        changed.append("image")

                hover_url = row.get("hover_image_url")
                if hover_url and is_legacy_url(hover_url, localizer.legacy_host):
                    local_url = localizer.localize(hover_url, f"products/{product.id}/hover")
                    storage_name = local_url.split(default_storage.base_url, 1)[-1] if hasattr(default_storage, "base_url") and local_url.startswith(default_storage.base_url) else local_url.lstrip("/")
                    if product.hover_image.name != storage_name:
                        product.hover_image.name = storage_name
                        changed.append("hover_image")

                gallery = row.get("image_urls") or row.get("gallery_images") or row.get("images") or []
                if isinstance(gallery, str):
                    gallery = [gallery]
                gallery = [u for u in gallery if isinstance(u, str) and is_legacy_url(u, localizer.legacy_host)]
                if opts["apply"] and opts["replace_gallery"] and gallery:
                    product.angle_images.all().delete()
                if opts["apply"] and gallery:
                    existing_names = set(product.angle_images.values_list("image", flat=True))
                    for index, url in enumerate(gallery):
                        local_url = localizer.localize(url, f"products/{product.id}/gallery")
                        storage_name = local_url.split(default_storage.base_url, 1)[-1] if hasattr(default_storage, "base_url") and local_url.startswith(default_storage.base_url) else local_url.lstrip("/")
                        if storage_name not in existing_names:
                            ProductImage.objects.create(product=product, image=storage_name, sort_order=index)
                            existing_names.add(storage_name)

                if opts["apply"] and changed:
                    product.save(update_fields=list(dict.fromkeys(changed)))

                audit["matched"].append({"id": product.id, "name": product.name, "match": match_type, "changed_fields": changed})
                self.stdout.write(f"{'APPLY' if opts['apply'] else 'DRY RUN'} {product.id}: {product.name} -> {', '.join(changed) or 'no changes'}")

            if opts["apply"] and opts["deactivate_unmatched"] and not opts["product_id"]:
                for product in Product.objects.filter(is_active=True).exclude(id__in=matched_ids):
                    product.is_active = False
                    product.save(update_fields=["is_active"])
                    audit["deactivated"].append({"id": product.id, "name": product.name})

            if opts["dry_run"]:
                transaction.set_rollback(True)

        audit["downloaded_assets"] = localizer.downloaded
        Path(opts["audit"]).write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"Finished: matched={len(audit['matched'])}, unmatched={len(audit['unmatched'])}, "
            f"assets={len(localizer.downloaded)}, applied={opts['apply']}"
        ))
        if opts["apply"]:
            self.stdout.write(self.style.SUCCESS("Migration complete. Storefront data now points to local storage."))
