"""Search Pixabay for umbrella artwork references and import selected assets.

Pixabay's API prohibits systematic mass downloads. This command caches search
results for 24 hours and downloads only an explicitly selected image ID.

Set PIXABAY_API_KEY in the environment (never commit credentials).

    python manage.py pixabay_umbrella_assets --query "elegant wedding flowers"
    python manage.py pixabay_umbrella_assets --download-id 123456

Downloaded files are saved in MEDIA_ROOT/umbrella_pixabay/ and a provenance
JSON record is written alongside each asset. The image can then be selected
for an editable photo layer in a Zenvibe template.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

API = "https://pixabay.com/api/"
MAX_BYTES = 15 * 1024 * 1024
CACHE_SECONDS = 24 * 60 * 60
ALLOWED_IMAGE_HOSTS = {"cdn.pixabay.com", "pixabay.com", "images.pixabay.com"}
TOPICS = {
    "corporate": "modern office architecture",
    "wedding": "elegant wedding bouquet",
    "birthday": "luxury birthday celebration",
    "botanical": "watercolor botanical flowers",
    "hotel": "luxury hotel interior",
    "real-estate": "modern luxury house",
    "golf": "golf course landscape",
    "travel": "mountain travel landscape",
    "restaurant": "fine dining restaurant",
    "festival": "elegant festival decorations",
}

def request_bytes(url, limit=MAX_BYTES):
    request = Request(url, headers={"User-Agent": "ZenvibeUmbrellaAssetPicker/1.0"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise CommandError(f"Pixabay returned HTTP {response.status}")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise CommandError("Image exceeds allowed file size")
    return data

def api_query(key, **params):
    url = API + "?" + urlencode({"key": key, **params})
    try:
        raw = request_bytes(url, 2 * 1024 * 1024)
        return json.loads(raw.decode("utf-8"))
    except (HTTPError, URLError, ValueError) as exc:
        raise CommandError(f"Pixabay request failed: {exc}") from exc

class Command(BaseCommand):
    help = "Find Pixabay artwork or download a specifically chosen image; never bulk-download."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--query", help="Search Pixabay and list image IDs")
        group.add_argument("--topic", choices=sorted(TOPICS))
        group.add_argument("--download-id", type=int)
        parser.add_argument("--type", choices=["photo","illustration","vector"],
                            default="photo")

    def handle(self, *args, **options):
        key = os.environ.get("PIXABAY_API_KEY", "").strip()
        if not key:
            raise CommandError(
                "PIXABAY_API_KEY is missing. Set it in your local environment; "
                "do not put the key in Git or source code."
            )
        root = Path(settings.MEDIA_ROOT) / "umbrella_pixabay"
        root.mkdir(parents=True, exist_ok=True)
        if options["download_id"] is not None:
            image_id = options["download_id"]
            if image_id <= 0:
                raise CommandError("Image ID must be positive")
            result = api_query(key, id=image_id)
            hits = result.get("hits", [])
            if not hits:
                raise CommandError(f"Pixabay image {image_id} was not found")
            hit = hits[0]
            url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not url:
                raise CommandError("No image URL available")
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname not in ALLOWED_IMAGE_HOSTS:
                raise CommandError("Untrusted Pixabay image URL")
            try:
                data = request_bytes(url)
            except (HTTPError, URLError) as exc:
                raise CommandError(f"Image download failed: {exc}") from exc
            from PIL import Image
            from io import BytesIO
            try:
                image = Image.open(BytesIO(data))
                image.verify()
            except (OSError, ValueError) as exc:
                raise CommandError("Downloaded asset is not a valid image") from exc
            extension = ".png" if parsed.path.lower().endswith(".png") else ".jpg"
            target = root / f"pixabay-{image_id}{extension}"
            target.write_bytes(data)
            metadata = {
                "provider": "Pixabay",
                "id": image_id,
                "pageURL": hit.get("pageURL"),
                "creator": hit.get("user"),
                "tags": hit.get("tags"),
                "license": "Pixabay Content License — review restrictions for merchandise",
                "source_url": url,
            }
            target.with_suffix(".json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
            self.stdout.write(self.style.SUCCESS(f"Saved {target}"))
            self.stdout.write("Review Pixabay's merchandise and trademark restrictions before publishing.")
            return

        query = options["query"] or TOPICS[options["topic"]]
        cache_dir = root / ".search_cache"
        cache_dir.mkdir(exist_ok=True)
        import hashlib
        cache_key = hashlib.sha256(
            f"{query}|{options['type']}".encode("utf-8")
        ).hexdigest()
        cache_path = cache_dir / f"{cache_key}.json"
        if cache_path.exists() and time.time() - cache_path.stat().st_mtime < CACHE_SECONDS:
            result = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            result = api_query(
                key, q=query[:100], image_type=options["type"],
                safesearch="true", per_page=20, min_width=640, min_height=480
            )
            cache_path.write_text(json.dumps(result), encoding="utf-8")
        self.stdout.write(f"Pixabay search: {query}")
        for hit in result.get("hits", []):
            self.stdout.write(
                f"ID {hit.get('id')} | {hit.get('tags','')} | {hit.get('pageURL','')}"
            )
        self.stdout.write(
            "To download an approved image: python manage.py pixabay_umbrella_assets "
            "--download-id IMAGE_ID"
        )
