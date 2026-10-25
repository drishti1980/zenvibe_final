from __future__ import annotations

import csv
import re
from copy import deepcopy
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse, quote_plus

import requests
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from designer.models import Product


BASE_URL = "https://zenvibe.ca"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/152 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-CA,en;q=0.9",
}

ENABLED = "fastest_delivery_enabled"
MIN_DAYS = "fastest_delivery_min_business_days"
MAX_DAYS = "fastest_delivery_max_business_days"

# Confirmed local-product -> live ZenVibe URL overrides.
# This does NOT change Product.slug/source_url; it is used only by this delivery sync.
PRODUCT_URL_OVERRIDES = {
    391: "https://zenvibe.ca/product/10x10-custom-canopy-tent/",
}

DELIVERY_RE = re.compile(
    r"Fastest\s+Delivery\s+between\s+"
    r"([A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*|\s+)\d{4})"
    r"\s*(?:-|–|—|to)\s*"
    r"([A-Za-z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*|\s+)\d{4})",
    re.I,
)


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_title(value):
    value = clean(value).lower()
    value = value.replace("×", "x").replace("’", "'").replace("–", "-")
    value = re.sub(r"\b(zenvibe|canada)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return clean(value)


def title_score(a, b):
    a, b = normalize_title(a), normalize_title(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def parse_date(value):
    value = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", clean(value), flags=re.I)
    value = value.replace(",", "")
    for fmt in ("%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported delivery date: {value}")


def business_days_until(start: date, target: date):
    """
    Mirrors designer.views._add_business_days():
    today + N Monday-Friday days, excluding today.
    """
    if target < start:
        raise ValueError(f"source date {target} is before local date {start}")

    current = start
    count = 0
    while current < target:
        current = current.fromordinal(current.toordinal() + 1)
        if current.weekday() < 5:
            count += 1
    return count


def extract_delivery(html):
    soup = BeautifulSoup(html, "html.parser")
    text = clean(soup.get_text(" ", strip=True))
    match = DELIVERY_RE.search(text)
    if not match:
        return None
    start = parse_date(match.group(1))
    end = parse_date(match.group(2))
    return start, end


def extract_title(html):
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("h1.product_title, h1.entry-title, h1")
    return clean(node.get_text(" ", strip=True)) if node else ""


def is_zenvibe_product_url(url):
    try:
        p = urlparse(url)
        return (
            p.scheme in ("http", "https")
            and p.netloc.lower().replace("www.", "") == "zenvibe.ca"
            and "/product/" in p.path
        )
    except Exception:
        return False


def canonical_url(url):
    return clean(url).split("#", 1)[0].split("?", 1)[0].rstrip("/") + "/"


def load_confirmed_mapping():
    """
    Reuse the confirmed live_url -> local_id mapping already maintained beside
    sync_zenvibe_ca.py when available.
    """
    path = Path(__file__).with_name("zenvibe_product_mapping.csv")
    by_id = {}
    if not path.exists():
        return by_id

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if clean(row.get("type")).lower() != "product":
                    continue
                if clean(row.get("status")).upper() != "MATCHED":
                    continue
                try:
                    local_id = int(row.get("local_id") or 0)
                except (TypeError, ValueError):
                    continue
                url = canonical_url(row.get("live_url") or "")
                if local_id and is_zenvibe_product_url(url):
                    by_id[local_id] = url
    except Exception:
        return {}
    return by_id


class Command(BaseCommand):
    help = (
        "Synchronise ONLY fastest-delivery configuration from each matching "
        "zenvibe.ca product page. No price/content/image/category/editor fields are changed."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--timeout", type=int, default=25)
        parser.add_argument(
            "--min-title-score",
            type=float,
            default=0.58,
            help="Safety threshold when validating source page title.",
        )
        parser.add_argument(
            "--allow-slug-fallback",
            action="store_true",
            help=(
                "If source_url/mapping is unavailable, try "
                "https://zenvibe.ca/product/<local-slug>/ and validate its title."
            ),
        )

    def handle(self, *args, **o):
        qs = Product.objects.filter(is_active=True).order_by("id")
        if o["product_id"]:
            qs = Product.objects.filter(pk=o["product_id"])
            if not qs.exists():
                raise CommandError("Product not found.")

        confirmed = load_confirmed_mapping()
        session = requests.Session()
        session.headers.update(HEADERS)

        changed = unchanged = unmatched = no_delivery = errors = 0
        today = timezone.localdate()

        self.stdout.write(f"Local delivery date basis: {today}")
        self.stdout.write(
            "Mode: " + ("APPLY" if o["apply"] else "PREVIEW ONLY")
        )

        with transaction.atomic():
            for product in qs.iterator():
                try:
                    url = self._source_url(product, confirmed, o["allow_slug_fallback"])
                    if not url:
                        unmatched += 1
                        self.stdout.write(self.style.WARNING(
                            f"{product.id} | NO-SOURCE | {product.name}"
                        ))
                        continue

                    response = session.get(url, timeout=o["timeout"], allow_redirects=True)
                    response.raise_for_status()

                    final_url = canonical_url(response.url)
                    if not is_zenvibe_product_url(final_url):
                        unmatched += 1
                        self.stdout.write(self.style.WARNING(
                            f"{product.id} | BAD-REDIRECT | {product.name} | {final_url}"
                        ))
                        continue

                    source_title = extract_title(response.text)
                    score = title_score(product.name, source_title)

                    # Confirmed mapping/source_url is authoritative enough to tolerate
                    # renamed products, but slug fallback requires a strong title match.
                    used_fallback = (
                        not self._direct_or_confirmed_url(product, confirmed)
                    )
                    if used_fallback and score < o["min_title_score"]:
                        unmatched += 1
                        self.stdout.write(self.style.WARNING(
                            f"{product.id} | TITLE-MISMATCH {score:.2f} | "
                            f"{product.name} <> {source_title} | {final_url}"
                        ))
                        continue

                    delivery = extract_delivery(response.text)
                    if not delivery:
                        no_delivery += 1
                        self.stdout.write(self.style.WARNING(
                            f"{product.id} | NO-DELIVERY-TEXT | {product.name} | {final_url}"
                        ))
                        continue

                    source_start, source_end = delivery
                    min_days = business_days_until(today, source_start)
                    max_days = business_days_until(today, source_end)

                    if max_days < min_days:
                        raise ValueError("source end date is before source start date")

                    original = (
                        deepcopy(product.source_attributes)
                        if isinstance(product.source_attributes, dict)
                        else {}
                    )
                    new = deepcopy(original)
                    new[ENABLED] = True
                    new[MIN_DAYS] = min_days
                    new[MAX_DAYS] = max_days

                    # Audit metadata is delivery-only and helps prove what was imported.
                    new["fastest_delivery_source_url"] = final_url
                    new["fastest_delivery_source_start_date"] = source_start.isoformat()
                    new["fastest_delivery_source_end_date"] = source_end.isoformat()
                    new["fastest_delivery_synced_at"] = timezone.now().isoformat()

                    same_core = (
                        original.get(ENABLED) is True
                        and original.get(MIN_DAYS) == min_days
                        and original.get(MAX_DAYS) == max_days
                    )

                    status = "SAME" if same_core else "UPDATE"
                    self.stdout.write(
                        f"{product.id} | {status} | {product.name} | "
                        f"ZenVibe={source_start} - {source_end} | "
                        f"business-days={min_days} - {max_days} | {final_url}"
                    )

                    if o["apply"]:
                        # THE ONLY DATABASE FIELD WRITTEN BY THIS COMMAND.
                        Product.objects.filter(pk=product.pk).update(
                            source_attributes=new
                        )

                    if same_core:
                        unchanged += 1
                    else:
                        changed += 1

                except Exception as exc:
                    errors += 1
                    self.stdout.write(self.style.ERROR(
                        f"{product.id} | ERROR | {product.name} | {exc}"
                    ))

            if not o["apply"]:
                transaction.set_rollback(True)

        message = (
            f"{'APPLIED' if o['apply'] else 'PREVIEW'}: "
            f"{changed} delivery configs {'updated' if o['apply'] else 'would update'}, "
            f"{unchanged} already matched, {unmatched} unmatched, "
            f"{no_delivery} pages without delivery text, {errors} errors. "
            "Only Product.source_attributes delivery keys are written."
        )
        if o["apply"]:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stdout.write(self.style.WARNING(message))

    def _direct_or_confirmed_url(self, product, confirmed):
        override = PRODUCT_URL_OVERRIDES.get(product.id)
        if override:
            return canonical_url(override)

        source_url = clean(getattr(product, "source_url", ""))
        if is_zenvibe_product_url(source_url):
            return canonical_url(source_url)
        return confirmed.get(product.id)

    def _source_url(self, product, confirmed, allow_slug_fallback):
        direct = self._direct_or_confirmed_url(product, confirmed)
        if direct:
            return direct

        if not allow_slug_fallback:
            return None

        # Local Django slugs are not guaranteed to match zenvibe.ca.
        # Discover the live product by name instead of blindly using product.slug.
        discovered = self._discover_live_product_url(product)
        if discovered:
            return discovered

        return None

    def _discover_live_product_url(self, product):
        query = clean(product.name)
        if not query:
            return None

        search_url = f"{BASE_URL}/?s={quote_plus(query)}&post_type=product"
        try:
            response = requests.get(
                search_url, headers=HEADERS, timeout=20, allow_redirects=True
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        urls = []
        for link in soup.select('a[href*="/product/"]'):
            href = canonical_url(link.get("href") or "")
            if is_zenvibe_product_url(href) and href not in urls:
                urls.append(href)

        ranked = []
        for href in urls[:25]:
            try:
                page = requests.get(
                    href, headers=HEADERS, timeout=20, allow_redirects=True
                )
                if not page.ok:
                    continue
                final_url = canonical_url(page.url)
                if not is_zenvibe_product_url(final_url):
                    continue
                live_title = extract_title(page.text)
                ranked.append((title_score(product.name, live_title), final_url))
            except requests.RequestException:
                continue

        if not ranked:
            return None

        ranked.sort(reverse=True)
        best_score, best_url = ranked[0]
        return best_url if best_score >= 0.58 else None
