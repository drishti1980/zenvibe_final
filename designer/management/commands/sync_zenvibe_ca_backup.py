from __future__ import annotations

import json
import re
import csv
import time
import random
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify



BASE_URL = "https://zenvibe.ca/"
SHOP_URL = "https://zenvibe.ca/shop/"


# Confirmed mappings where the old local catalogue name differs substantially
# from the current zenvibe.ca title. These update the EXISTING product ID only.
PRODUCT_MATCH_OVERRIDES = {
    "3-star-gold-plastic-trophy-28-cm": 26,
    "510ml-smart-thermo-bottle-led": 387,
    "adjustable-x-banner-stand": 187,
}



def load_confirmed_product_mapping():
    """Load confirmed live-url -> local Product ID mappings bundled with this command."""
    path = Path(__file__).with_name("zenvibe_product_mapping.csv")
    mapping = {}
    if not path.exists():
        return mapping
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if (row.get("type") or "").strip().lower() != "product":
                    continue
                if (row.get("status") or "").strip().upper() != "MATCHED":
                    continue
                url = (row.get("live_url") or "").strip().rstrip("/") + "/"
                try:
                    local_id = int(row.get("local_id") or 0)
                except (TypeError, ValueError):
                    continue
                if url and local_id:
                    mapping[url] = local_id
    except Exception:
        return {}
    return mapping

CONFIRMED_URL_TO_LOCAL_ID = load_confirmed_product_mapping()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/152 Safari/537.36"
    )
}


# ================================================================
# HELPERS
# ================================================================

def clean(value):
    if not value:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def money(value):
    if value in (None, ""):
        return None

    value = re.sub(
        r"[^0-9.\-]",
        "",
        str(value),
    )

    if not value:
        return None

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def model_has_field(model, name):
    try:
        model._meta.get_field(name)
        return True
    except Exception:
        return False


def product_slug(url):
    parts = (
        urlparse(url)
        .path
        .strip("/")
        .split("/")
    )

    if "product" not in parts:
        return ""

    index = parts.index("product")

    try:
        return parts[index + 1]
    except IndexError:
        return ""


def category_path(url):
    """
    Examples:

    /product-category/banners-displays/
        -> ["banners-displays"]

    /product-category/banners-displays/custom-table-covers/
        -> ["banners-displays", "custom-table-covers"]
    """

    parts = (
        urlparse(url)
        .path
        .strip("/")
        .split("/")
    )

    if "product-category" not in parts:
        return []

    index = parts.index(
        "product-category"
    )

    return [
        value
        for value in parts[index + 1:]
        if value
    ]


def normalize_product_name(value):
    """
    Conservative normalisation used only to find an existing
    local product when the WooCommerce slug/name differs slightly.

    This deliberately does NOT perform fuzzy similarity matching.
    """

    value = (value or "").lower()

    value = (
        value
        .replace("×", "x")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("–", "-")
        .replace("—", "-")
        .replace("&", "and")
    )

    # ZenVibe product titles often contain SEO text after |
    value = value.split("|")[0]

    marketing_words = [
        "premium",
        "custom",
        "personalized",
        "personalised",
        "printing",
        "printed",
        "promotional",
        "high quality",
        "high-quality",
    ]

    for word in marketing_words:
        value = re.sub(
            rf"\b{re.escape(word)}\b",
            " ",
            value,
            flags=re.I,
        )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    replacements = {
        "cards": "card",
        "tickets": "ticket",
        "hangers": "hanger",
        "brochures": "brochure",
        "banners": "banner",
        "notebooks": "notebook",
        "mugs": "mug",
        "pens": "pen",
        "bags": "bag",
        "bottles": "bottle",
        "flags": "flag",
    }

    words = [
        replacements.get(word, word)
        for word in value.split()
    ]

    return " ".join(words)



def product_name_tokens(value):
    normalized = normalize_product_name(value)
    stop_words = {
        "a", "an", "and", "for", "of", "on", "the", "to", "with",
        "canada", "canadian", "ft", "feet", "inch", "inches",
    }
    return {
        token for token in normalized.split()
        if len(token) > 1 and token not in stop_words
    }


def product_measurements(value):
    value = (value or "").lower().replace("×", "x")
    patterns = (
        r"\b\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\b",
        r"\b\d+(?:\.\d+)?\s*(?:ml|oz|cm|mm|ft|gb)\b",
        r"\b\d{2,4}\b",
    )
    found = set()
    for pattern in patterns:
        found.update(
            re.sub(r"\s+", "", match)
            for match in re.findall(pattern, value, flags=re.I)
        )
    return found


def safe_name_similarity(remote_name, local_name):
    remote_norm = normalize_product_name(remote_name)
    local_norm = normalize_product_name(local_name)
    if not remote_norm or not local_norm:
        return 0.0

    remote_tokens = product_name_tokens(remote_name)
    local_tokens = product_name_tokens(local_name)
    union = remote_tokens | local_tokens
    token_score = (
        len(remote_tokens & local_tokens) / len(union)
        if union else 0.0
    )
    sequence_score = SequenceMatcher(None, remote_norm, local_norm).ratio()

    remote_measures = product_measurements(remote_name)
    local_measures = product_measurements(local_name)
    if remote_measures and local_measures and remote_measures.isdisjoint(local_measures):
        return 0.0

    containment = remote_norm in local_norm or local_norm in remote_norm
    score = max(sequence_score, token_score, 0.86 if containment else 0.0)

    if remote_measures and local_measures and remote_measures & local_measures:
        score = min(1.0, score + 0.08)

    return score


# ================================================================
# ZENVIBE.CA CLIENT
# ================================================================

class ZenVibeClient:

    def __init__(
        self,
        timeout=30,
        request_delay=1.25,
        max_retries=6,
    ):
        self.timeout = timeout
        self.request_delay = request_delay
        self.max_retries = max_retries

        self.session = requests.Session()

        self.session.headers.update({
            **HEADERS,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-AU,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        })

        self.last_request_time = 0.0

    def _wait_before_request(self):
        """
        Keep requests spaced apart so we do not hammer
        zenvibe.ca.
        """

        elapsed = (
            time.monotonic()
            - self.last_request_time
        )

        # Small random jitter avoids sending requests
        # at an exact mechanical interval.
        required_delay = (
            self.request_delay
            + random.uniform(0.15, 0.55)
        )

        if elapsed < required_delay:
            time.sleep(
                required_delay - elapsed
            )

    def _retry_delay(
        self,
        response,
        attempt,
    ):
        """
        Prefer Retry-After supplied by the server.
        Otherwise use exponential backoff.
        """

        retry_after = (
            response.headers.get(
                "Retry-After"
            )
            if response is not None
            else None
        )

        if retry_after:
            try:
                return min(
                    max(
                        float(retry_after),
                        1.0,
                    ),
                    120.0,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        # 5, 10, 20, 40, 60, 60...
        return min(
            5 * (2 ** attempt),
            60,
        )

    def get(self, url):
        """
        GET with throttling and retry support.

        Retries:
        - HTTP 429
        - HTTP 500
        - HTTP 502
        - HTTP 503
        - HTTP 504
        - temporary connection/time-out failures
        """

        last_error = None

        for attempt in range(
            self.max_retries + 1
        ):
            self._wait_before_request()

            response = None

            try:
                response = (
                    self.session.get(
                        url,
                        timeout=self.timeout,
                    )
                )

                self.last_request_time = (
                    time.monotonic()
                )

                # Success
                if response.status_code < 400:
                    return response

                # Rate limiting / temporary server problem
                if response.status_code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    if (
                        attempt
                        >= self.max_retries
                    ):
                        response.raise_for_status()

                    delay = (
                        self._retry_delay(
                            response,
                            attempt,
                        )
                    )

                    print(
                        f"Temporary HTTP "
                        f"{response.status_code} "
                        f"for {url}"
                    )

                    print(
                        f"Waiting "
                        f"{delay:.1f}s before "
                        f"retry "
                        f"{attempt + 1}/"
                        f"{self.max_retries}..."
                    )

                    time.sleep(delay)
                    continue

                # Permanent 4xx error
                response.raise_for_status()

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as error:
                last_error = error

                self.last_request_time = (
                    time.monotonic()
                )

                if (
                    attempt
                    >= self.max_retries
                ):
                    raise

                delay = min(
                    5 * (2 ** attempt),
                    60,
                )

                print(
                    f"Temporary network error "
                    f"for {url}: {error}"
                )

                print(
                    f"Waiting "
                    f"{delay:.1f}s before "
                    f"retry "
                    f"{attempt + 1}/"
                    f"{self.max_retries}..."
                )

                time.sleep(delay)

        if last_error:
            raise last_error

        raise RuntimeError(
            f"Unable to retrieve {url}"
        )

    def soup(self, url):
        response = self.get(url)

        return BeautifulSoup(
            response.text,
            "html.parser",
        )

    # ------------------------------------------------------------
    # CATEGORY DISCOVERY
    # ------------------------------------------------------------

    def get_categories(self):
        soup = self.soup(
            SHOP_URL
        )

        found = {}

        for anchor in soup.select(
            'a[href*="/product-category/"]'
        ):
            href = urljoin(
                BASE_URL,
                anchor.get(
                    "href",
                    "",
                ),
            )

            path = category_path(
                href
            )

            if not path:
                continue

            slug = path[-1]

            parent_slug = (
                path[-2]
                if len(path) > 1
                else None
            )

            name = clean(
                anchor.get_text(
                    " ",
                    strip=True,
                )
            )

            name = re.sub(
                r"\s+\d+\s+Products?$",
                "",
                name,
                flags=re.I,
            ).strip()

            if not name:
                continue

            found[slug] = {
                "slug": slug,
                "name": name,
                "url": href,
                "parent_slug":
                    parent_slug,
            }

        # Load descriptions and proper titles
        for category in (
            found.values()
        ):
            try:
                page = self.soup(
                    category["url"]
                )
            except Exception:
                category[
                    "description"
                ] = ""
                continue

            title = page.select_one(
                "h1"
            )

            if title:
                category["name"] = clean(
                    title.get_text(
                        " ",
                        strip=True,
                    )
                )

            description = (
                page.select_one(
                    ".term-description"
                )
                or
                page.select_one(
                    ".woocommerce-products-header__description"
                )
            )

            if description:
                category[
                    "description"
                ] = "".join(
                    str(item)
                    for item
                    in description.contents
                ).strip()
            else:
                category[
                    "description"
                ] = ""

        return found

    # ------------------------------------------------------------
    # PRODUCT URL DISCOVERY
    # ------------------------------------------------------------

    def category_products(
        self,
        category_url,
    ):
        output = set()

        current_url = category_url

        visited = set()

        while current_url:

            if current_url in visited:
                break

            visited.add(
                current_url
            )

            soup = self.soup(
                current_url
            )

            for anchor in soup.select(
                'a[href*="/product/"]'
            ):
                href = urljoin(
                    BASE_URL,
                    anchor.get(
                        "href",
                        "",
                    ),
                )

                if (
                    "/product/"
                    not in
                    urlparse(href).path
                ):
                    continue

                href = (
                    href
                    .split("?")[0]
                    .rstrip("/")
                    + "/"
                )

                output.add(
                    href
                )

            next_page = (
                soup.select_one(
                    "a.next.page-numbers"
                )
            )

            if next_page:
                current_url = urljoin(
                    current_url,
                    next_page.get(
                        "href",
                        "",
                    ),
                )
            else:
                current_url = None

        return output

    # ------------------------------------------------------------
    # PRODUCT DETAIL SECTION HELPERS
    # ------------------------------------------------------------

    def section_html(self, soup, ids=(), headings=()):
        """Return a non-empty HTML section without inventing content."""
        for element_id in ids:
            node = soup.select_one(f"#{element_id}")
            if node:
                html = "".join(str(item) for item in node.contents).strip()
                if clean(node.get_text(" ", strip=True)):
                    return html

        wanted = {clean(value).lower() for value in headings if clean(value)}
        if not wanted:
            return ""

        for heading in soup.find_all(re.compile(r"^h[1-6]$")):
            title = clean(heading.get_text(" ", strip=True)).lower().rstrip(":")
            if not any(value == title or value in title for value in wanted):
                continue

            parts = []
            for sibling in heading.next_siblings:
                tag_name = getattr(sibling, "name", None)
                if tag_name and re.match(r"^h[1-6]$", tag_name, flags=re.I):
                    break
                text = clean(getattr(sibling, "get_text", lambda *a, **k: str(sibling))(" ", strip=True)) if tag_name else clean(str(sibling))
                if text:
                    parts.append(str(sibling))
            html = "".join(parts).strip()
            if html:
                return html

        return ""

    def quantity_bounds(self, soup, tiers):
        """Extract explicit min/max quantity, with conservative tier fallback."""
        page_text = clean(soup.get_text(" ", strip=True))
        minimum = None
        maximum = None

        min_patterns = [
            r"minimum\s+(?:order\s+)?quantity\s*[:\-]?\s*(\d{1,7})",
            r"minimum\s+order\s*[:\-]?\s*(\d{1,7})",
            r"min(?:imum)?\.?\s*qty\.?\s*[:\-]?\s*(\d{1,7})",
            r"moq\s*[:\-]?\s*(\d{1,7})",
        ]
        max_patterns = [
            r"maximum\s+(?:order\s+)?quantity\s*[:\-]?\s*(\d{1,7})",
            r"maximum\s+order\s*[:\-]?\s*(\d{1,7})",
            r"max(?:imum)?\.?\s*qty\.?\s*[:\-]?\s*(\d{1,7})",
        ]

        for pattern in min_patterns:
            match = re.search(pattern, page_text, flags=re.I)
            if match:
                minimum = int(match.group(1))
                break

        for pattern in max_patterns:
            match = re.search(pattern, page_text, flags=re.I)
            if match:
                maximum = int(match.group(1))
                break

        if minimum is None and tiers:
            minimum = min(quantity for quantity, _price in tiers)

        return minimum, maximum

    # ------------------------------------------------------------
    # PRODUCT DETAILS
    # ------------------------------------------------------------

    def product(
        self,
        url,
    ):
        soup = self.soup(
            url
        )

        slug = product_slug(
            url
        )

        title = (
            soup.select_one(
                "h1.product_title"
            )
            or
            soup.select_one(
                "h1.entry-title"
            )
            or
            soup.select_one(
                "h1"
            )
        )

        if title:
            name = clean(
                title.get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            name = (
                slug
                .replace("-", " ")
                .title()
            )

        # --------------------------------------------------------
        # DESCRIPTION
        # --------------------------------------------------------

        description_node = (
            soup.select_one(
                "#tab-description"
            )
            or
            soup.select_one(
                ".woocommerce-Tabs-panel--description"
            )
        )

        description = ""

        if description_node:
            description = "".join(
                str(item)
                for item
                in description_node.contents
            ).strip()

        short_description_node = (
            soup.select_one(
                ".woocommerce-product-details__short-description"
            )
        )

        short_description = ""

        if short_description_node:
            short_description = "".join(
                str(item)
                for item
                in short_description_node.contents
            ).strip()

        # --------------------------------------------------------
        # INFORMATION / PRINTING GUIDELINES / FAQ
        # --------------------------------------------------------

        product_information = self.section_html(
            soup,
            ids=(
                "tab-additional_information",
                "tab-additional-information",
                "tab-information",
                "tab-product_information",
            ),
            headings=(
                "additional information",
                "product information",
                "information",
                "specifications",
                "product specifications",
            ),
        )

        printing_guidelines = self.section_html(
            soup,
            ids=(
                "tab-printing-guidelines",
                "tab-printing_guidelines",
                "tab-artwork-guidelines",
                "tab-design-guidelines",
                "tab-design_guideline",
                "tab-design-guideline",
                "tab-guidelines",
            ),
            headings=(
                "printing guidelines",
                "artwork guidelines",
                "artwork requirements",
                "design guidelines",
                "design requirements",
                "print guidelines",
                "file requirements",
            ),
        )

        faqs = self.section_html(
            soup,
            ids=(
                "tab-faqs",
                "tab-faq",
                "tab-nbd_faq",
                "faq",
                "faqs",
            ),
            headings=(
                "frequently asked questions",
                "frequently asked question",
                "faq",
                "faqs",
            ),
        )

        # --------------------------------------------------------
        # SKU
        # --------------------------------------------------------

        sku_node = soup.select_one(
            ".sku"
        )

        if sku_node:
            sku = clean(
                sku_node.get_text(
                    " ",
                    strip=True,
                )
            )
        else:
            sku = ""

        # --------------------------------------------------------
        # PRODUCT CATEGORIES
        # --------------------------------------------------------

        category_slugs = []

        for anchor in soup.select(
            '.posted_in a[href*="/product-category/"], '
            '.product_meta a[href*="/product-category/"]'
        ):
            path = category_path(
                anchor.get(
                    "href",
                    "",
                )
            )

            if not path:
                continue

            slug_value = path[-1]

            if (
                slug_value
                not in category_slugs
            ):
                category_slugs.append(
                    slug_value
                )

        # --------------------------------------------------------
        # JSON-LD PRODUCT DATA
        # --------------------------------------------------------

        json_product = {}

        for script in soup.find_all(
            "script",
            attrs={
                "type":
                    "application/ld+json"
            },
        ):
            try:
                payload = json.loads(
                    script.string
                    or
                    script.get_text()
                    or
                    "{}"
                )
            except Exception:
                continue

            candidates = []

            if isinstance(
                payload,
                list,
            ):
                candidates += payload

            elif isinstance(
                payload,
                dict,
            ):
                candidates.append(
                    payload
                )

                graph = payload.get(
                    "@graph"
                )

                if isinstance(
                    graph,
                    list,
                ):
                    candidates += graph

            for item in candidates:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                item_type = item.get(
                    "@type"
                )

                is_product = (
                    item_type == "Product"
                    or
                    (
                        isinstance(
                            item_type,
                            list,
                        )
                        and
                        "Product"
                        in item_type
                    )
                )

                if is_product:
                    json_product = item
                    break

            if json_product:
                break

        # --------------------------------------------------------
        # PRICE
        # --------------------------------------------------------

        price = None
        min_price = None
        max_price = None

        offers = json_product.get(
            "offers"
        )

        if isinstance(
            offers,
            dict,
        ):
            offer_type = offers.get(
                "@type"
            )

            if (
                offer_type
                == "AggregateOffer"
            ):
                min_price = money(
                    offers.get(
                        "lowPrice"
                    )
                )

                max_price = money(
                    offers.get(
                        "highPrice"
                    )
                )

                price = min_price

            else:
                price = money(
                    offers.get(
                        "price"
                    )
                )

                min_price = price
                max_price = price

        elif isinstance(
            offers,
            list,
        ):
            offer_prices = []

            for offer in offers:
                if not isinstance(
                    offer,
                    dict,
                ):
                    continue

                value = money(
                    offer.get(
                        "price"
                    )
                )

                if value is not None:
                    offer_prices.append(
                        value
                    )

            if offer_prices:
                min_price = min(
                    offer_prices
                )

                max_price = max(
                    offer_prices
                )

                price = min_price

        # Fallback visible WooCommerce price
        if price is None:
            price_element = (
                soup.select_one(
                    "p.price"
                )
                or
                soup.select_one(
                    ".summary .price"
                )
            )

            if price_element:
                price_text = clean(
                    price_element.get_text(
                        " ",
                        strip=True,
                    )
                )

                values = re.findall(
                    r"\$\s*"
                    r"([0-9]+(?:\.[0-9]+)?)",
                    price_text,
                )

                values = [
                    money(value)
                    for value in values
                ]

                values = [
                    value
                    for value in values
                    if value is not None
                ]

                if values:
                    min_price = min(
                        values
                    )

                    max_price = max(
                        values
                    )

                    price = min_price

        # --------------------------------------------------------
        # IMAGES
        # --------------------------------------------------------

        images = []

        for image in soup.select(
            ".woocommerce-product-gallery img"
        ):
            src = (
                image.get(
                    "data-large_image"
                )
                or
                image.get(
                    "data-src"
                )
                or
                image.get(
                    "src"
                )
            )

            if not src:
                continue

            src = urljoin(
                url,
                src,
            )

            if src not in images:
                images.append(
                    src
                )

        # JSON-LD image fallback
        json_images = json_product.get(
            "image"
        )

        if isinstance(
            json_images,
            str,
        ):
            json_images = [
                json_images
            ]

        if isinstance(
            json_images,
            list,
        ):
            for image_url in json_images:
                if not isinstance(
                    image_url,
                    str,
                ):
                    continue

                image_url = urljoin(
                    url,
                    image_url,
                )

                if (
                    image_url
                    not in images
                ):
                    images.append(
                        image_url
                    )

        # --------------------------------------------------------
        # ATTRIBUTES / VARIATIONS
        # --------------------------------------------------------

        attributes = {}

        for select in soup.select(
            "form.variations_form select"
        ):
            key = (
                select.get(
                    "data-attribute_name"
                )
                or
                select.get(
                    "name"
                )
                or
                select.get(
                    "id"
                )
                or
                ""
            )

            key = re.sub(
                r"^(attribute_|pa_)",
                "",
                key,
            )

            key = (
                key
                .replace("_", " ")
                .replace("-", " ")
                .strip()
                .title()
            )

            values = []

            for option in select.select(
                "option"
            ):
                value = clean(
                    option.get_text(
                        " ",
                        strip=True,
                    )
                )

                if not value:
                    continue

                if value.lower() in {
                    "choose an option",
                    "select",
                    "clear",
                }:
                    continue

                if value not in values:
                    values.append(
                        value
                    )

            if key and values:
                attributes[key] = values

        # Additional information table
        for row in soup.select(
            ".woocommerce-product-attributes tr"
        ):
            heading = row.select_one(
                "th"
            )

            value_node = row.select_one(
                "td"
            )

            if (
                not heading
                or
                not value_node
            ):
                continue

            key = clean(
                heading.get_text(
                    " ",
                    strip=True,
                )
            )

            values = [
                clean(value)
                for value in re.split(
                    r"[,|]",
                    value_node.get_text(
                        " ",
                        strip=True,
                    ),
                )
                if clean(value)
            ]

            if key and values:
                attributes.setdefault(
                    key,
                    values,
                )

        # --------------------------------------------------------
        # QUANTITY PRICE TIERS
        # --------------------------------------------------------

        tiers = []

        # Quantity pricing on ZenVibe is normally rendered in visible HTML tables.
        # Parse the first quantity/range token and the first dollar price in each row.
        # Examples: 50-99 $13.99, 100–249 $11.90, 500+ $11.82, <100 $1.49.
        for row in soup.select("table tr"):
            text = clean(row.get_text(" ", strip=True))
            if "$" not in text:
                continue
            price_match = re.search(r"\$\s*([0-9,]+(?:\.[0-9]{1,2})?)", text)
            if not price_match:
                continue
            quantity = None
            range_match = re.search(r"(?<![\d.])(\d{1,7})\s*(?:[-–—]\s*\d{1,7}|\+)", text)
            if range_match:
                quantity = int(range_match.group(1))
            else:
                less_match = re.search(r"<\s*(\d{1,7})", text)
                if less_match:
                    quantity = 1
            if quantity is None:
                continue
            unit_price = money(price_match.group(1))
            if unit_price is not None:
                tiers.append((quantity, unit_price))

        # De-duplicate by threshold and keep ascending quantity.
        # De-duplicate and validate quantity pricing.
        tier_map = {}
        for quantity, unit_price in tiers:
            if quantity is None or unit_price is None:
                continue
            try:
                quantity = int(quantity)
                unit_price = Decimal(str(unit_price))
            except (TypeError, ValueError, InvalidOperation):
                continue
            if quantity <= 0 or unit_price <= 0:
                continue
            tier_map[quantity] = unit_price

        tiers = sorted(tier_map.items(), key=lambda item: item[0])

        # Genuine quantity pricing is authoritative. WooCommerce AggregateOffer
        # can contain placeholder/add-on values on configurable products.
        if tiers:
            tier_prices = [unit_price for _quantity, unit_price in tiers]
            price = tiers[0][1]
            min_price = min(tier_prices)
            max_price = max(tier_prices)

        minimum_quantity, maximum_quantity = self.quantity_bounds(
            soup,
            tiers,
        )
        if minimum_quantity is None:
            minimum_quantity = tiers[0][0] if tiers else 1

        return {
            "name": name,
            "slug": slug,
            "url": url,
            "description": (
                description
                or
                short_description
            ),
            "short_description":
                short_description,
            "product_information": product_information,
            "printing_guidelines": printing_guidelines,
            "faqs": faqs,
            "minimum_quantity": minimum_quantity,
            "maximum_quantity": maximum_quantity,
            "source_url": url,
            "sku": sku,
            "price": price,
            "min_price":
                min_price,
            "max_price":
                max_price,
            "category_slugs":
                category_slugs,
            "images":
                images,
            "attributes":
                attributes,
            "tiers":
                sorted(tiers),
        }


# ================================================================
# DJANGO MANAGEMENT COMMAND
# ================================================================

class Command(BaseCommand):

    help = (
        "Synchronise products/categories "
        "from zenvibe.ca into the new "
        "ZenVibe project."
    )

    # ------------------------------------------------------------
    # ARGUMENTS
    # ------------------------------------------------------------

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Actually save changes. "
                "Without this flag it is "
                "a dry run."
            ),
        )

        parser.add_argument(
            "--download-images",
            action="store_true",
            help=(
                "Download product images "
                "from zenvibe.ca."
            ),
        )

        parser.add_argument(
            "--replace-images",
            action="store_true",
            help=(
                "Replace existing main "
                "product images."
            ),
        )

        parser.add_argument(
            "--allow-create",
            action="store_true",
            help=(
                "Allow remote products with no safe local match to be created. "
                "Default behaviour is update-existing-only to avoid duplicates."
            ),
        )

        parser.add_argument(
            "--create-missing",
            action="store_true",
            help=(
                "Create a remote product only when there is no plausible "
                "existing local match. Ambiguous products are still skipped."
            ),
        )

        parser.add_argument(
            "--source-of-truth",
            action="store_true",
            help=(
                "Treat every discovered zenvibe.ca product as authoritative: "
                "update safe existing matches and create a local product for every "
                "remaining source product. Never deletes local products or editor data."
            ),
        )

        parser.add_argument(
            "--exact-catalogue",
            action="store_true",
            help=(
                "Make supported catalogue fields match zenvibe.ca while preserving "
                "editor/template/print configuration and existing Product IDs."
            ),
        )

        parser.add_argument(
            "--verbose-data",
            action="store_true",
            help="Print parsed catalogue values for each product during dry-run/apply.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help=(
                "Limit the number of "
                "products processed."
            ),
        )

        parser.add_argument(
            "--slug",
            action="append",
            default=[],
            help=(
                "Only process a specific "
                "product slug. May be "
                "specified multiple times."
            ),
        )

    # ------------------------------------------------------------
    # MAIN COMMAND
    # ------------------------------------------------------------

    def handle(
        self,
        *args,
        **options,
    ):
        self.apply = options[
            "apply"
        ]
        self.verbose_data = options.get("verbose_data", False)

        self.download_images = options[
            "download_images"
        ]

        self.replace_images = options[
            "replace_images"
        ]

        self.allow_create = options[
            "allow_create"
        ]
        self.create_missing = options[
            "create_missing"
        ]

        self.exact_catalogue = options[
            "exact_catalogue"
        ]
        self.source_of_truth = options[
            "source_of_truth"
        ]

        if self.source_of_truth:
            self.exact_catalogue = True
            self.create_missing = True

        # Exact catalogue mode includes source images and replaces the main
        # catalogue image. Editor/template configuration is still preserved.
        if self.exact_catalogue:
            self.download_images = True
            self.replace_images = True

        Category = apps.get_model(
            "designer",
            "Category",
        )

        Product = apps.get_model(
            "designer",
            "Product",
        )

        ProductImage = (
            self.optional_model(
                "ProductImage"
            )
        )

        Size = self.optional_model(
            "ProductSizeVariant"
        )

        Color = self.optional_model(
            "ProductColorVariant"
        )

        Tier = self.optional_model(
            "ProductPriceTier"
        )

        client = ZenVibeClient()

        self.stdout.write(
            "Reading categories "
            "from zenvibe.ca..."
        )

        remote_categories = (
            client.get_categories()
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Found "
                f"{len(remote_categories)} "
                f"categories/subcategories."
            )
        )

        category_map = (
            self.sync_categories(
                Category,
                remote_categories,
            )
        )

        # --------------------------------------------------------
        # DISCOVER ALL PRODUCT URLS
        # --------------------------------------------------------

        product_urls = set()

        for category in (
            remote_categories.values()
        ):
            try:
                product_urls.update(
                    client.category_products(
                        category["url"]
                    )
                )

            except Exception as error:
                self.stderr.write(
                    self.style.WARNING(
                        f"Category failed "
                        f"{category['slug']}: "
                        f"{error}"
                    )
                )

        product_urls = sorted(
            product_urls
        )

        requested_slugs = {
            value.lower().strip()
            for value
            in options["slug"]
            if value.strip()
        }

        if requested_slugs:
            product_urls = [
                url
                for url
                in product_urls
                if (
                    product_slug(url)
                    .lower()
                    in requested_slugs
                )
            ]

        if options["limit"]:
            product_urls = (
                product_urls[
                    :options["limit"]
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Found "
                f"{len(product_urls)} "
                f"product pages."
            )
        )

        created = 0
        updated = 0
        failed = 0

        for index, url in enumerate(
            product_urls,
            start=1,
        ):
            try:
                data = client.product(
                    url
                )

                result = (
                    self.sync_product(
                        Product=Product,
                        ProductImage=
                            ProductImage,
                        Size=Size,
                        Color=Color,
                        Tier=Tier,
                        Category=Category,
                        category_map=
                            category_map,
                        data=data,
                    )
                )

                if result == "created":
                    created += 1
                else:
                    updated += 1

                self.stdout.write(
                    f"[{index}/"
                    f"{len(product_urls)}] "
                    f"{result}: "
                    f"{data['name']}"
                )

            except Exception as error:
                failed += 1

                self.stderr.write(
                    self.style.WARNING(
                        f"[{index}/"
                        f"{len(product_urls)}] "
                        f"FAILED "
                        f"{url}: "
                        f"{error}"
                    )
                )

        mode = (
            "APPLIED"
            if self.apply
            else
            "DRY RUN"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{mode} complete. "
                f"Created={created}, "
                f"Updated={updated}, "
                f"Failed={failed}"
            )
        )

    # ============================================================
    # CATEGORY IMPORT
    # ============================================================

    def sync_categories(
        self,
        Category,
        remote,
    ):
        result = {}

        # Parent categories first
        values = sorted(
            remote.values(),
            key=lambda item: (
                bool(
                    item[
                        "parent_slug"
                    ]
                ),
                item["name"],
            ),
        )

        for data in values:
            existing = (
                Category.objects
                .filter(
                    slug=data["slug"]
                )
                .first()
            )

            obj = (
                existing
                or
                Category(
                    slug=data["slug"]
                )
            )

            obj.name = data["name"]

            parent_slug = data[
                "parent_slug"
            ]

            if (
                parent_slug
                and
                model_has_field(
                    Category,
                    "parent",
                )
            ):
                parent = (
                    result.get(
                        parent_slug
                    )
                    or
                    Category.objects
                    .filter(
                        slug=parent_slug
                    )
                    .first()
                )

                if parent:
                    obj.parent = parent

            if (
                data.get(
                    "description"
                )
                and
                model_has_field(
                    Category,
                    "description",
                )
            ):
                obj.description = data[
                    "description"
                ]

            if model_has_field(
                Category,
                "is_active",
            ):
                obj.is_active = True

            if self.apply:
                obj.save()

            result[
                data["slug"]
            ] = obj

        return result

    # ============================================================
    # PRODUCT IMPORT
    # ============================================================

    @transaction.atomic
    def sync_product(
        self,
        *,
        Product,
        ProductImage,
        Size,
        Color,
        Tier,
        Category,
        category_map,
        data,
    ):
        # --------------------------------------------------------
        # SAFE EXISTING PRODUCT MATCHING
        # --------------------------------------------------------

        obj = None
        match_method = None

        # 0A. Confirmed mapping generated from the previous sync report.
        # Never blindly trust an old mapping: the CSV may contain a stale or
        # incorrect Product ID. Validate the mapped local product against the
        # current remote product before allowing catalogue data to update it.
        source_key = (
            (data.get("source_url") or "")
            .strip()
            .rstrip("/")
            + "/"
        )
        mapped_id = CONFIRMED_URL_TO_LOCAL_ID.get(source_key)

        if mapped_id is not None:
            mapped_obj = Product.objects.filter(pk=mapped_id).first()

            if mapped_obj is not None:
                remote_name = normalize_product_name(data.get("name") or "")
                local_name = normalize_product_name(mapped_obj.name or "")
                similarity = safe_name_similarity(
                    data.get("name") or "",
                    mapped_obj.name or "",
                )

                mapping_is_valid = (
                    remote_name == local_name
                    or similarity >= 0.82
                )

                if mapping_is_valid:
                    obj = mapped_obj
                    match_method = f"confirmed-report:id={mapped_id}"
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "Ignoring stale confirmed mapping: "
                            f"{data.get('name')} -> "
                            f"ID {mapped_id} ({mapped_obj.name}) "
                            f"[similarity={similarity:.2f}]"
                        )
                    )

        # 0. Explicit confirmed legacy-product mapping.
        # This is safer than guessing when an old local title is very different.
        override_id = PRODUCT_MATCH_OVERRIDES.get(data.get("slug"))
        if obj is None and override_id is not None:
            obj = Product.objects.filter(pk=override_id).first()
            if obj is None:
                raise ValueError(
                    f"Configured product mapping points to missing local ID {override_id}."
                )
            match_method = f"confirmed-map:id={override_id}"

        # 1. Previously-confirmed source URL.
        if obj is None and model_has_field(Product, "source_url") and data.get("source_url"):
            matches = list(Product.objects.filter(source_url=data["source_url"])[:2])
            if len(matches) == 1:
                obj = matches[0]
                match_method = "source-url"

        # 2. Exact slug.
        if obj is None:
            matches = list(Product.objects.filter(slug=data["slug"])[:2])
            if len(matches) == 1:
                obj = matches[0]
                match_method = "slug"

        # 3. Exact product name.
        if obj is None:
            matches = list(Product.objects.filter(name__iexact=data["name"])[:2])
            if len(matches) == 1:
                obj = matches[0]
                match_method = "exact-name"

        # 4. Exact normalized name.
        if obj is None:
            remote_normalized = normalize_product_name(data["name"])
            matches = [
                candidate
                for candidate in Product.objects.all()
                if normalize_product_name(candidate.name) == remote_normalized
            ]
            if len(matches) == 1:
                obj = matches[0]
                match_method = "normalized-name"

        # 5. Strong fuzzy match with ambiguity protection.
        if obj is None:
            scored = []
            remote_category_slugs = set(data.get("category_slugs") or [])

            for candidate in Product.objects.select_related("category").all():
                score = safe_name_similarity(data["name"], candidate.name)
                if score <= 0:
                    continue

                candidate_category = getattr(candidate, "category", None)
                candidate_category_slug = getattr(candidate_category, "slug", "") or ""
                if candidate_category_slug in remote_category_slugs:
                    score = min(1.0, score + 0.04)

                scored.append((score, candidate.id, candidate))

            scored.sort(key=lambda item: (-item[0], item[1]))

            if scored:
                best_score, _best_id, best = scored[0]
                second_score = scored[1][0] if len(scored) > 1 else 0.0
                margin = best_score - second_score

                confident = (
                    best_score >= 0.90
                    or (best_score >= 0.82 and margin >= 0.08)
                    or (best_score >= 0.76 and margin >= 0.15)
                )

                if confident:
                    obj = best
                    match_method = f"safe-fuzzy:{best_score:.2f}"
                else:
                    # A moderately similar local record means the case is
                    # ambiguous: never auto-create a duplicate for it.
                    plausible_existing = best_score >= 0.58
                    if plausible_existing and not self.allow_create:
                        if self.source_of_truth:
                            # Do not overwrite a questionable local product. Leave it
                            # intact and create the authoritative source product below.
                            obj = None
                            match_method = "source-create"
                        else:
                            raise ValueError(
                                "Ambiguous existing product match. "
                                f"Best candidate: {best.id} {best.name} "
                                f"(score={best_score:.2f}, runner-up={second_score:.2f}). "
                                "Skipped; add a confirmed mapping instead of guessing."
                            )

        if obj is None:
            if self.allow_create:
                pass
            elif self.create_missing:
                # Normal create-missing mode remains conservative. Source-of-truth
                # mode intentionally creates the remote product when matching is
                # ambiguous rather than overwriting a possibly different local item.
                if (
                    not self.source_of_truth
                    and scored
                    and scored[0][0] >= 0.58
                ):
                    best_score, _best_id, best = scored[0]
                    raise ValueError(
                        "Ambiguous existing product match. "
                        f"Best candidate: {best.id} {best.name} "
                        f"(score={best_score:.2f}). Skipped instead of creating a duplicate."
                    )
            else:
                raise ValueError(
                    "No safe existing local product match. "
                    "Skipped to avoid creating a duplicate. "
                    "Use --create-missing for genuinely missing products."
                )

        created = obj is None

        # --------------------------------------------------------
        # CATEGORY
        # --------------------------------------------------------

        category = None

        # Most specific category wins
        for slug in reversed(
            data[
                "category_slugs"
            ]
        ):
            category = (
                category_map.get(
                    slug
                )
                or
                Category.objects
                .filter(
                    slug=slug
                )
                .first()
            )

            if category:
                break

        # --------------------------------------------------------
        # CREATE PRODUCT OBJECT
        # --------------------------------------------------------

        if obj is None:
            if category is None:
                raise ValueError(
                    "No matching category "
                    f"for {data['name']}."
                )

            obj = Product(
                slug=data["slug"],
                category=category,
                name=data["name"],
            )

        # --------------------------------------------------------
        # UPDATE CATALOGUE DATA
        # --------------------------------------------------------

        # Keep the existing Product ID so all editor/template relationships remain
        # attached, but in exact-catalogue mode make the customer-facing catalogue
        # identity match the current source.
        if created or self.exact_catalogue:
            obj.name = data["name"]

        if (
            (created or self.exact_catalogue)
            and category
            and model_has_field(
                Product,
                "category",
            )
        ):
            obj.category = category

        if (
            data["description"]
            and
            model_has_field(
                Product,
                "description",
            )
        ):
            obj.description = data[
                "description"
            ]

        # Snapshot-only fields. Empty remote values never wipe good local data.
        snapshot_fields = (
            "short_description",
            "product_information",
            "printing_guidelines",
            "faqs",
        )

        for field_name in snapshot_fields:
            remote_value = data.get(field_name)
            if remote_value and model_has_field(Product, field_name):
                setattr(obj, field_name, remote_value)

        if (
            data.get("minimum_quantity") is not None
            and model_has_field(Product, "minimum_quantity")
        ):
            obj.minimum_quantity = data["minimum_quantity"]

        if (
            data.get("maximum_quantity") is not None
            and model_has_field(Product, "maximum_quantity")
        ):
            obj.maximum_quantity = data["maximum_quantity"]

        if data.get("source_url") and model_has_field(Product, "source_url"):
            obj.source_url = data["source_url"]

        if model_has_field(Product, "source_synced_at"):
            obj.source_synced_at = timezone.now()

        if (
            data["sku"]
            and
            model_has_field(
                Product,
                "sku",
            )
        ):
            obj.sku = data["sku"]

        if (
            data["price"]
            is not None
            and
            model_has_field(
                Product,
                "price",
            )
        ):
            obj.price = data[
                "price"
            ]

        if (
            data["min_price"]
            is not None
            and
            model_has_field(
                Product,
                "min_price",
            )
        ):
            obj.min_price = data[
                "min_price"
            ]

        if (
            data["max_price"]
            is not None
            and
            model_has_field(
                Product,
                "max_price",
            )
        ):
            obj.max_price = data[
                "max_price"
            ]

        if model_has_field(
            Product,
            "is_active",
        ):
            obj.is_active = True

        # --------------------------------------------------------
        # DO NOT TOUCH NEW EDITOR CONFIGURATION
        # --------------------------------------------------------
        #
        # Existing products retain:
        #
        # width
        # height
        # print_width_in
        # print_height_in
        # bleed_in
        # safe_margin_in
        # min_dpi
        # customizer_mode
        # ProductPrintSurface
        # ProductPrintArea
        # DesignTemplate
        #
        # Because existing Product IDs are retained.
        # --------------------------------------------------------

        # --------------------------------------------------------
        # DRY RUN
        # --------------------------------------------------------

        if not self.apply:
            if self.verbose_data:
                self.stdout.write(
                    "  DATA "
                    f"min_qty={data.get('minimum_quantity')} "
                    f"max_qty={data.get('maximum_quantity')} "
                    f"price={data.get('price')} "
                    f"tiers={data.get('tiers')} "
                    f"attributes={data.get('attributes')} "
                    f"images={len(data.get('images') or [])} "
                    f"description={'yes' if data.get('description') else 'no'} "
                    f"short={'yes' if data.get('short_description') else 'no'} "
                    f"info={'yes' if data.get('product_information') else 'no'} "
                    f"guidelines={'yes' if data.get('printing_guidelines') else 'no'} "
                    f"faqs={'yes' if data.get('faqs') else 'no'}"
                )
            if created:
                return "created"

            suffix = ",exact-catalogue" if self.exact_catalogue else ""
            return (
                f"updated["
                f"{match_method}{suffix}]"
            )

        # --------------------------------------------------------
        # SAVE PRODUCT
        # --------------------------------------------------------

        obj.save()

        # --------------------------------------------------------
        # SIZE / COLOR VARIANTS
        # --------------------------------------------------------

        self.sync_attributes(
            obj,
            Size,
            Color,
            data["attributes"],
        )

        # --------------------------------------------------------
        # QUANTITY PRICE TIERS
        # --------------------------------------------------------

        self.sync_tiers(
            obj,
            Tier,
            data["tiers"],
        )

        # --------------------------------------------------------
        # IMAGES
        # --------------------------------------------------------

        if self.download_images:
            self.sync_images(
                obj,
                Product,
                ProductImage,
                data["images"],
            )

        if created:
            return "created"

        return (
            f"updated["
            f"{match_method}]"
        )

    # ============================================================
    # VARIANTS
    # ============================================================

    def sync_attributes(
        self,
        product,
        Size,
        Color,
        attributes,
    ):
        """
        Synchronise source Size/Colour options.

        Existing variant rows are reused where possible so editor_profile,
        print dimensions and canvas settings stay attached. In exact catalogue
        mode, stale source options are deactivated rather than deleted.
        """
        size_values = None
        color_values = None

        for label, values in attributes.items():
            key = label.lower()

            if Size and ("size" in key or "dimension" in key):
                size_values = list(dict.fromkeys(values))

            if Color and ("color" in key or "colour" in key):
                color_values = list(dict.fromkeys(values))

        if Size and size_values is not None:
            active_ids = []

            for index, value in enumerate(size_values):
                size_key = slugify(value)[:140] or f"size-{index + 1}"

                existing = (
                    Size.objects
                    .filter(product=product, size_key=size_key)
                    .first()
                )

                if existing is None:
                    # Legacy fallback: reuse the same named row if it exists.
                    name_field = (
                        "name"
                        if model_has_field(Size, "name")
                        else "size_name"
                        if model_has_field(Size, "size_name")
                        else None
                    )
                    if name_field:
                        existing = (
                            Size.objects
                            .filter(product=product, **{f"{name_field}__iexact": value})
                            .first()
                        )

                obj = existing or Size(product=product)

                if model_has_field(Size, "name"):
                    obj.name = value
                elif model_has_field(Size, "size_name"):
                    obj.size_name = value

                if model_has_field(Size, "size_key"):
                    obj.size_key = size_key

                if model_has_field(Size, "sort_order"):
                    obj.sort_order = index

                if model_has_field(Size, "is_active"):
                    obj.is_active = True

                obj.save()
                active_ids.append(obj.pk)

            if self.exact_catalogue and model_has_field(Size, "is_active"):
                (
                    Size.objects
                    .filter(product=product)
                    .exclude(pk__in=active_ids)
                    .update(is_active=False)
                )

        if Color and color_values is not None:
            active_ids = []

            for index, value in enumerate(color_values):
                color_key = slugify(value)[:120] or f"color-{index + 1}"

                existing = (
                    Color.objects
                    .filter(product=product, color_key=color_key)
                    .first()
                )

                if existing is None:
                    name_field = (
                        "name"
                        if model_has_field(Color, "name")
                        else "color_name"
                        if model_has_field(Color, "color_name")
                        else None
                    )
                    if name_field:
                        existing = (
                            Color.objects
                            .filter(product=product, **{f"{name_field}__iexact": value})
                            .first()
                        )

                obj = existing or Color(product=product)

                if model_has_field(Color, "name"):
                    obj.name = value
                elif model_has_field(Color, "color_name"):
                    obj.color_name = value

                if model_has_field(Color, "color_key"):
                    obj.color_key = color_key

                if model_has_field(Color, "sort_order"):
                    obj.sort_order = index

                if model_has_field(Color, "is_active"):
                    obj.is_active = True

                obj.save()
                active_ids.append(obj.pk)

            if self.exact_catalogue and model_has_field(Color, "is_active"):
                (
                    Color.objects
                    .filter(product=product)
                    .exclude(pk__in=active_ids)
                    .update(is_active=False)
                )

    # ============================================================
    # PRICE TIERS
    # ============================================================

    def sync_tiers(
        self,
        product,
        Tier,
        tiers,
    ):
        if not Tier:
            return

        quantity_field = None

        if model_has_field(
            Tier,
            "min_quantity",
        ):
            quantity_field = (
                "min_quantity"
            )

        elif model_has_field(
            Tier,
            "quantity",
        ):
            quantity_field = (
                "quantity"
            )

        price_field = None

        if model_has_field(
            Tier,
            "unit_price",
        ):
            price_field = (
                "unit_price"
            )

        elif model_has_field(
            Tier,
            "price",
        ):
            price_field = "price"

        if not (
            quantity_field
            and
            price_field
        ):
            return

        active_ids = []

        for quantity, price in tiers:
            lookup = {
                "product":
                    product,
                quantity_field:
                    quantity,
            }

            # Source tiers parsed here are product-wide/default tiers.
            if model_has_field(Tier, "variant"):
                lookup["variant"] = None

            defaults = {
                price_field:
                    price,
            }

            if model_has_field(
                Tier,
                "is_active",
            ):
                defaults[
                    "is_active"
                ] = True

            tier_obj, _ = Tier.objects.update_or_create(
                **lookup,
                defaults=defaults,
            )
            active_ids.append(tier_obj.pk)

        # Do not wipe anything when the source parser found no tiers.
        # When tiers ARE present, deactivate stale default/source tiers only.
        if (
            self.exact_catalogue
            and tiers
            and model_has_field(Tier, "is_active")
        ):
            stale = Tier.objects.filter(product=product)

            if model_has_field(Tier, "variant"):
                stale = stale.filter(variant__isnull=True)

            stale.exclude(pk__in=active_ids).update(is_active=False)

    # ============================================================
    # IMAGES
    # ============================================================

    def sync_images(
        self,
        product,
        Product,
        ProductImage,
        images,
    ):
        if not images:
            return

        # MAIN PRODUCT IMAGE: exact-catalogue mode always refreshes it.
        if model_has_field(Product, "image"):
            existing = getattr(product, "image", None)

            if (
                not existing
                or self.replace_images
                or self.exact_catalogue
            ):
                self.save_remote_image(
                    product,
                    "image",
                    images[0],
                )

        if not ProductImage:
            return

        source_gallery = images[1:12]
        existing_gallery = list(
            ProductImage.objects
            .filter(product=product)
            .order_by("sort_order", "id")
        )

        for index, image_url in enumerate(source_gallery, start=1):
            # Reuse the row at the same position first. This preserves any
            # image-specific print-area configuration already attached to it.
            obj = (
                existing_gallery[index - 1]
                if index - 1 < len(existing_gallery)
                else ProductImage(product=product)
            )

            if model_has_field(ProductImage, "sort_order"):
                obj.sort_order = index

            if not obj.pk:
                obj.save()

            self.save_remote_image(
                obj,
                "image",
                image_url,
            )

        if self.exact_catalogue and len(existing_gallery) > len(source_gallery):
            # Remove only surplus gallery rows that have no custom print-area
            # coordinates. Rows carrying editor configuration are preserved.
            for obj in existing_gallery[len(source_gallery):]:
                protected = any(
                    getattr(obj, field, None) is not None
                    for field in (
                        "print_left_pct",
                        "print_top_pct",
                        "print_width_pct",
                        "print_height_pct",
                    )
                    if model_has_field(ProductImage, field)
                )
                if not protected:
                    obj.delete()

    # ============================================================
    # REMOTE IMAGE SAVE
    # ============================================================

    def save_remote_image(
        self,
        obj,
        field,
        url,
    ):
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=45,
        )

        response.raise_for_status()

        filename = (
            Path(
                urlparse(url).path
            ).name
            or
            "zenvibe-image.jpg"
        )

        getattr(
            obj,
            field,
        ).save(
            filename,
            ContentFile(
                response.content
            ),
            save=True,
        )

    # ============================================================
    # OPTIONAL MODELS
    # ============================================================

    def optional_model(
        self,
        name,
    ):
        try:
            return apps.get_model(
                "designer",
                name,
            )

        except LookupError:
            return None