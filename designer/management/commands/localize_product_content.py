import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, urljoin

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import reverse
from django.utils.text import slugify

from designer.models import Product

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


LEGACY_HOSTS = {"zenvibe.ca", "www.zenvibe.ca"}
TEXT_FIELDS = (
    "description",
    "short_description",
    "product_information",
    "printing_method",
    "design_guidelines",
    "printing_guidelines",
    "faqs",
)
ASSET_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg",
    ".pdf", ".ai", ".eps", ".zip", ".doc", ".docx",
}
URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.I)


def host_is_legacy(url):
    try:
        return urlparse(url).netloc.lower() in LEGACY_HOSTS
    except Exception:
        return False


def is_asset_url(url):
    try:
        return Path(urlparse(url).path).suffix.lower() in ASSET_EXTS
    except Exception:
        return False


class Command(BaseCommand):
    help = (
        "Remove runtime zenvibe.ca dependencies from Product content. "
        "Rewrites matching old product links to local Django product URLs, "
        "downloads old-site assets into MEDIA_ROOT, and unwraps unmatched old links."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--legacy-host", default="zenvibe.ca")
        parser.add_argument("--report", default="localize_product_content_report.json")

    def handle(self, *args, **opts):
        if opts["apply"] and opts["dry_run"]:
            raise CommandError("Use either --dry-run or --apply, not both.")
        apply_changes = bool(opts["apply"])
        if not apply_changes:
            self.stdout.write(self.style.WARNING("DRY RUN: database/files will not be changed."))

        if BeautifulSoup is None:
            raise CommandError("BeautifulSoup is required. Install with: pip install beautifulsoup4")
        if apply_changes and requests is None:
            raise CommandError("requests is required. Install with: pip install requests")

        media_root = Path(settings.MEDIA_ROOT)
        asset_root = media_root / "legacy_import" / "products"

        products = list(Product.objects.all())
        by_slug = {p.slug: p for p in products if p.slug}
        # Also permit a generated slug from product name.
        for p in products:
            by_slug.setdefault(slugify(p.name), p)

        report = {
            "mode": "apply" if apply_changes else "dry-run",
            "products_changed": 0,
            "links_rewritten": 0,
            "links_unwrapped": 0,
            "assets_localized": 0,
            "asset_failures": [],
            "remaining_legacy_urls": [],
            "changes": [],
        }

        session = requests.Session() if requests and apply_changes else None
        if session:
            session.headers.update({"User-Agent": "Mozilla/5.0 ZenVibe migration"})

        def local_product_url(old_url):
            parsed = urlparse(old_url)
            parts = [x for x in parsed.path.split("/") if x]
            if len(parts) >= 2 and parts[0] == "product":
                slug = parts[1]
                target = by_slug.get(slug)
                if target:
                    try:
                        return reverse("designer:choose_design", args=[target.id])
                    except Exception:
                        return f"/product/{target.id}/"
            return None

        def download_asset(url, product):
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "asset"
            stem = slugify(Path(filename).stem) or "asset"
            ext = Path(filename).suffix.lower()
            if ext not in ASSET_EXTS:
                ext = ".bin"
            rel_dir = Path("legacy_import") / "products" / str(product.id)
            rel_path = rel_dir / f"{stem}{ext}"
            abs_path = media_root / rel_path

            if abs_path.exists():
                return settings.MEDIA_URL.rstrip("/") + "/" + rel_path.as_posix()

            if not apply_changes:
                return settings.MEDIA_URL.rstrip("/") + "/" + rel_path.as_posix()

            abs_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                r = session.get(url, timeout=30, allow_redirects=True)
                r.raise_for_status()
                abs_path.write_bytes(r.content)
                report["assets_localized"] += 1
                return settings.MEDIA_URL.rstrip("/") + "/" + rel_path.as_posix()
            except Exception as exc:
                report["asset_failures"].append({
                    "product_id": product.id, "url": url, "error": str(exc)
                })
                return None

        def clean_html(value, product, field):
            if not value or "zenvibe.ca" not in value.lower():
                return value, False

            soup = BeautifulSoup(value, "html.parser")
            changed = False

            # Anchor links.
            for a in list(soup.find_all("a")):
                href = (a.get("href") or "").strip()
                if not href:
                    continue
                absolute = urljoin("https://zenvibe.ca/", href)
                if host_is_legacy(absolute):
                    if is_asset_url(absolute):
                        local = download_asset(absolute, product)
                        if local:
                            a["href"] = local
                            changed = True
                    else:
                        local = local_product_url(absolute)
                        if local:
                            a["href"] = local
                            report["links_rewritten"] += 1
                        else:
                            # Keep visible text/content, remove only the dead dependency.
                            a.unwrap()
                            report["links_unwrapped"] += 1
                        changed = True

            # Media attributes.
            for tag in soup.find_all(True):
                for attr in ("src", "poster"):
                    raw = (tag.get(attr) or "").strip()
                    if raw:
                        absolute = urljoin("https://zenvibe.ca/", raw)
                        if host_is_legacy(absolute):
                            local = download_asset(absolute, product)
                            if local:
                                tag[attr] = local
                                changed = True

                srcset = (tag.get("srcset") or "").strip()
                if srcset and "zenvibe.ca" in srcset.lower():
                    new_parts = []
                    for part in srcset.split(","):
                        bits = part.strip().split()
                        if not bits:
                            continue
                        absolute = urljoin("https://zenvibe.ca/", bits[0])
                        if host_is_legacy(absolute):
                            local = download_asset(absolute, product)
                            if local:
                                bits[0] = local
                                changed = True
                        new_parts.append(" ".join(bits))
                    tag["srcset"] = ", ".join(new_parts)

                style = tag.get("style")
                if style and "zenvibe.ca" in style.lower():
                    def repl(m):
                        old = m.group(0)
                        local = download_asset(old, product) if is_asset_url(old) else None
                        return local or ""
                    new_style = URL_RE.sub(repl, style)
                    if new_style != style:
                        tag["style"] = new_style
                        changed = True

            result = str(soup)
            # Any legacy URL left in plain text/HTML gets recorded, never silently hidden.
            leftovers = [u.rstrip(").,;") for u in URL_RE.findall(result) if host_is_legacy(u.rstrip(").,;"))]
            for url in leftovers:
                report["remaining_legacy_urls"].append({
                    "product_id": product.id, "field": field, "url": url
                })
            return result, changed

        for product in products:
            field_changes = {}
            for field in TEXT_FIELDS:
                if not hasattr(product, field):
                    continue
                old = getattr(product, field) or ""
                new, changed = clean_html(old, product, field)
                if changed and new != old:
                    field_changes[field] = new

            # Clean source_attributes recursively without altering editor/template JSON.
            if hasattr(product, "source_attributes"):
                attrs = product.source_attributes or {}
                raw = json.dumps(attrs, ensure_ascii=False)
                if "zenvibe.ca" in raw.lower():
                    def clean_obj(obj):
                        if isinstance(obj, dict):
                            return {k: clean_obj(v) for k, v in obj.items()}
                        if isinstance(obj, list):
                            return [clean_obj(v) for v in obj]
                        if isinstance(obj, str):
                            if host_is_legacy(obj):
                                local = local_product_url(obj)
                                return local or ""
                            return obj.replace("https://www.zenvibe.ca", "").replace(
                                "https://zenvibe.ca", ""
                            )
                        return obj
                    cleaned = clean_obj(attrs)
                    if cleaned != attrs:
                        field_changes["source_attributes"] = cleaned

            if field_changes:
                report["products_changed"] += 1
                report["changes"].append({
                    "product_id": product.id,
                    "name": product.name,
                    "fields": list(field_changes.keys()),
                })
                if apply_changes:
                    for field, value in field_changes.items():
                        setattr(product, field, value)
                    product.save(update_fields=list(field_changes.keys()))

        Path(opts["report"]).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        self.stdout.write("")
        self.stdout.write(f"Products changed: {report['products_changed']}")
        self.stdout.write(f"Local product links rewritten: {report['links_rewritten']}")
        self.stdout.write(f"Unmatched old links unwrapped: {report['links_unwrapped']}")
        self.stdout.write(f"Assets localized: {report['assets_localized']}")
        self.stdout.write(f"Asset failures: {len(report['asset_failures'])}")
        self.stdout.write(f"Remaining legacy URLs: {len(report['remaining_legacy_urls'])}")
        self.stdout.write(f"Report: {opts['report']}")

        if apply_changes and report["asset_failures"]:
            self.stdout.write(self.style.WARNING(
                "Some assets could not be downloaded. Review the report before switching off the old site."
            ))
        elif apply_changes and not report["remaining_legacy_urls"]:
            self.stdout.write(self.style.SUCCESS(
                "Product content localization completed with no detected legacy URLs in processed fields."
            ))
