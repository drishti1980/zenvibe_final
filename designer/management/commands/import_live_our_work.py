"""Import the ACTUAL image files on zenvibe.ca/our-work/ into Django media.

Requires: pip install requests beautifulsoup4
Preview: python manage.py import_live_our_work --dry-run
Import:  python manage.py import_live_our_work --replace-images
Existing admin titles, text, links and section ordering are preserved.
"""
import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import PageContentBlock

SOURCE = "https://zenvibe.ca/our-work/"
SECTIONS = [
    ("banners", "Banners & Displays"),
    ("promotional", "Promotional Products"),
    ("corporate", "Corporate Gift sets"),
    ("awards", "Awards"),
    ("marketing", "Marketing materials"),
    ("apparel", "Custom Apparel"),
]


def norm(value):
    return " ".join((value or "").casefold().split())


def image_url(tag):
    """Choose real WordPress image URLs rather than SVG lazy-loading placeholders."""
    candidates = [tag.get(k) for k in ("data-full-url", "data-orig-file", "data-src", "data-lazy-src", "data-original", "src")]
    for k in ("data-srcset", "srcset"):
        candidates.extend(item.strip().split()[0] for item in (tag.get(k) or "").split(",") if item.strip())
    for candidate in candidates:
        if not candidate or candidate.startswith(("data:", "blob:")):
            continue
        url = urljoin(SOURCE, candidate)
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname == "zenvibe.ca" and parsed.path.lower().endswith((".webp", ".jpg", ".jpeg", ".png")):
            return url
    return ""


def gallery_for_heading(heading):
    # Scan the DOM between this heading and the next heading of equal/higher rank.
    # Gallery images may be inside columns, nested rows, and WordPress blocks.
    rank = int(heading.name[1])
    images = []
    for node in heading.next_elements:
        if getattr(node, "name", None) in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if int(node.name[1]) <= rank:
                break
        if getattr(node, "name", None) == "img":
            url = image_url(node)
            if url and url not in images:
                images.append(url)
    return images


class Command(BaseCommand):
    help = "Download the original Our Work page images into admin-editable PageContentBlock records."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--replace-images", action="store_true",
                            help="Replace image files in existing Our Work records, keeping admin-edited text.")
        parser.add_argument("--source", default=SOURCE)
        parser.add_argument("--sync-gallery", action="store_true", help="Deactivate outdated gallery records after a successful import")

    def handle(self, *args, **options):
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise CommandError("Install dependencies: pip install requests beautifulsoup4") from exc

        source = options["source"]
        if urlparse(source).hostname != "zenvibe.ca" or urlparse(source).scheme != "https":
            raise CommandError("Only https://zenvibe.ca is an allowed source.")
        session = requests.Session()
        session.headers["User-Agent"] = "ZenVibe-OurWork-Migration/1.0"
        try:
            response = session.get(source, timeout=25)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch original Our Work page: {exc}") from exc
        soup = BeautifulSoup(response.text, "html.parser")
        main = soup.select_one("main") or soup.select_one(".site-main") or soup.select_one("article") or soup.body
        if main is None:
            raise CommandError("Reference page has no readable content.")

        heading_nodes = main.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        matches = {}
        for key, title in SECTIONS:
            heading = next((h for h in heading_nodes if norm(h.get_text(" ", strip=True)) == norm(title)), None)
            if heading:
                urls = gallery_for_heading(heading)
                if urls:
                    matches[key] = urls
            if key not in matches:
                self.stderr.write(f"No images found under {title}; section unchanged.")

        if not matches:
            raise CommandError("No section galleries detected; no database records changed.")

        # The original page's lead image is before the first gallery heading.
        hero = None
        first = next((h for h in heading_nodes if norm(h.get_text(" ", strip=True)) == norm(SECTIONS[0][1])), None)
        if first:
            candidates = []
            for tag in main.find_all("img"):
                if tag is first or tag in first.find_all_previous():
                    break
                url = image_url(tag)
                if url:
                    candidates.append(url)
            hero = candidates[-1] if candidates else None

        plan = []
        if hero:
            plan.append(("hero", "OUR WORKS", hero, 0))
        for group_index, (key, title) in enumerate(SECTIONS):
            urls = matches.get(key, [])
            if urls:
                plan.append((f"{key}-heading", title.upper(), None, 10 + group_index * 20))
            for index, url in enumerate(urls, 1):
                plan.append((f"{key}-image-{index:02d}", "", url, 11 + group_index * 20 + index))

        for key, title, url, order in plan:
            self.stdout.write(f"{key}: {url or '[section heading]'}")
        if options["dry_run"]:
            self.stdout.write(f"Dry run: {len(plan)} blocks, no downloads or database changes.")
            return

        imported = 0
        imported_keys = set()
        failed_groups = set()
        for key, title, url, order in plan:
            block, created = PageContentBlock.objects.get_or_create(
                page="our_work", section_key=key,
                defaults={"heading": title, "sort_order": order, "is_active": True})
            if not url:
                continue
            if block.image and not options["replace_images"]:
                self.stdout.write(f"Preserved existing image: {key}")
                continue
            parsed = urlparse(url)
            if parsed.scheme != "https" or not (parsed.hostname == "zenvibe.ca" or parsed.hostname.endswith(".zenvibe.ca")):
                self.stderr.write(f"Skipped external image: {url}")
                continue
            try:
                result = session.get(url, timeout=35)
                result.raise_for_status()
                if len(result.content) > 15 * 1024 * 1024:
                    raise ValueError("Image exceeds 15 MB")
                kind = result.headers.get("content-type", "").split(";")[0].strip()
                if not kind.startswith("image/") or kind == "image/svg+xml":
                    raise ValueError(f"Unsupported image content-type: {kind}")
                extension = mimetypes.guess_extension(kind) or Path(parsed.path).suffix or ".jpg"
                if extension == ".jpe":
                    extension = ".jpg"
                digest = hashlib.sha256(result.content).hexdigest()[:12]
                filename = f"our-work/{key}-{digest}{extension}"
                block.image.save(filename, ContentFile(result.content), save=True)
                if not block.image.name.startswith("page-content/our-work/"):
                    raise CommandError(f"Unexpected media path for {key}: {block.image.name}")
                if not block.image.storage.exists(block.image.name):
                    raise CommandError(f"Image was not saved in local storage: {block.image.name}")
                imported += 1
                imported_keys.add(key)
            except (requests.RequestException, ValueError) as exc:
                failed_groups.add(key.split("-image-")[0])
                self.stderr.write(f"Failed {key}: {exc}")
        if options["sync_gallery"]:
            for group, _ in SECTIONS:
                if group not in matches or group in failed_groups:
                    continue
                prefix = group + "-image-"
                count = PageContentBlock.objects.filter(page="our_work", section_key__startswith=prefix).exclude(section_key__in=imported_keys).update(is_active=False)
                if count:
                    self.stdout.write(f"Deactivated {count} outdated {group} gallery records.")
        self.stdout.write(self.style.SUCCESS(f"Imported {imported} original images into media/page-content/our-work/."))
        self.stdout.write("Images are served from Django MEDIA_URL, not from zenvibe.ca.")
        self.stdout.write("Use Django Admin > Page Content Blocks > Our Work to edit all images and text.")
