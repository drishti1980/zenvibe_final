# designer/management/commands/sync_zenvibe_catalog.py
"""
Synchronise the PUBLIC ZenVibe.ca WooCommerce catalogue into Django.

Behaviour
---------
* Reads current zenvibe.ca category/product pages at run time.
* Creates missing Category rows.
* Creates missing Product rows.
* Existing categories/products are SKIPPED -- never overwritten.
* Preserves parent/subcategory hierarchy where Category.parent exists.
* Does NOT import gallery/media "products" from your old asset library.
* Does NOT set physical print dimensions. Dimension/surface configuration is a
  separate concern and should be synced after the catalogue is correct.
* Dry-run by default unless --apply is supplied.

Examples
--------
python manage.py sync_zenvibe_catalog
python manage.py sync_zenvibe_catalog --apply

Optional:
python manage.py sync_zenvibe_catalog --apply --base-url https://zenvibe.ca
"""

from __future__ import annotations

import re
import time
from decimal import Decimal
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction, IntegrityError
from django.utils.text import slugify

from designer.models import Category, Product


DEFAULT_BASE = "https://zenvibe.ca"
SHOP_PATH = "/shop/"
UA = "Mozilla/5.0 (compatible; ZenVibeCatalogSync/1.0)"


# Exact public hierarchy currently exposed by zenvibe.ca.
# The crawler also discovers products from these category URLs.
CATEGORY_TREE = {
    "Awards": [],
    "Bags": [],
    "Banners & Displays": [
        "Canopy Tent",
        "Custom Banners",
        "Custom Flags",
        "Custom Table Covers",
        "Standing Banners",
        "Trade Show Displays",
    ],
    "Corporate Gift Set": [],
    "Custom Apparel": [
        "Custom Caps",
        "Custom DTF T-shirt",
        "Hoodie",
        "Custom Jackets",
        "Custom Sublimated Sportswear",
    ],
    "Custom notebooks": [],
    "Drinkware": [],
    "Marketing Materials": [],
    "Pens": [],
    "Promotional Products": [],
}


# Known public category slugs. If ZenVibe changes one, discovery from /shop/
# is attempted first and this map is used as a fallback.
CATEGORY_SLUGS = {
    "Awards": "awards",
    "Bags": "bags",
    "Banners & Displays": "banners-displays",
    "Canopy Tent": "banners-displays/canopy-tent",
    "Custom Banners": "banners-displays/custom-banners",
    "Custom Flags": "banners-displays/custom-flags",
    "Custom Table Covers": "banners-displays/custom-table-covers",
    "Standing Banners": "banners-displays/standing-banners",
    "Trade Show Displays": "banners-displays/trade-show-displays",
    "Corporate Gift Set": "corporate-gift-set",
    "Custom Apparel": "custom-apparel",
    "Custom Caps": "custom-apparel/custom-caps",
    "Custom DTF T-shirt": "custom-apparel/custom-dtf-t-shirt",
    "Hoodie": "custom-apparel/hoodie",
    "Custom Jackets": "custom-apparel/custom-jackets",
    "Custom Sublimated Sportswear": "custom-apparel/custom-sublimated-sportswear",
    "Custom notebooks": "custom-notebooks",
    "Drinkware": "drinkware",
    "Marketing Materials": "marketing-materials",
    "Pens": "pens",
    "Promotional Products": "promotional-products",
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            self.links.append((self._href, unescape(text)))
            self._href = None
            self._text = []


def fetch(url, timeout=25, retries=5):
    """Fetch a public ZenVibe page with polite retry/backoff for HTTP 429/5xx."""
    last_error = None
    for attempt in range(retries):
        req = Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-CA,en;q=0.9",
            },
        )
        try:
            with urlopen(req, timeout=timeout) as r:
                charset = r.headers.get_content_charset() or "utf-8"
                return r.read().decode(charset, errors="replace")
        except HTTPError as e:
            last_error = e
            if e.code not in {429, 500, 502, 503, 504}:
                raise
            retry_after = e.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else min(2 ** attempt, 16)
            except (TypeError, ValueError):
                wait = min(2 ** attempt, 16)
            time.sleep(wait)
        except Exception as e:
            last_error = e
            if attempt == retries - 1:
                raise
            time.sleep(min(2 ** attempt, 8))
    raise last_error


def links_from(html_text, base):
    p = LinkParser()
    p.feed(html_text)
    out = []
    for href, text in p.links:
        if not href:
            continue
        out.append((urljoin(base, href), text.strip()))
    return out


def canonical_product_url(url, base_host):
    u = urlparse(url)
    if u.netloc and u.netloc != base_host:
        return None
    path = u.path.rstrip("/") + "/"
    # Product pages only; explicitly exclude category paths.
    if "/product/" not in path or "/product-category/" in path:
        return None
    return f"https://{base_host}{path}"


def discover_category_urls(shop_html, base_url):
    """Map visible category anchor text -> public category URL."""
    host = urlparse(base_url).netloc
    found = {}
    for url, text in links_from(shop_html, base_url):
        u = urlparse(url)
        if u.netloc == host and "/product-category/" in u.path and text:
            clean = re.sub(r"\s+\d+\s+Products?$", "", text, flags=re.I).strip()
            if clean:
                found.setdefault(clean.lower(), url.split("?")[0])
    return found


def category_url(name, discovered, base_url):
    if name.lower() in discovered:
        return discovered[name.lower()]
    slug = CATEGORY_SLUGS[name]
    return urljoin(base_url.rstrip("/") + "/", f"product-category/{slug}/")


def discover_products_for_category(cat_url, base_url, max_pages=30):
    """
    Crawl WooCommerce category pagination and return {product_name: product_url}.
    Product names come from anchor text. Duplicates are naturally collapsed.
    """
    host = urlparse(base_url).netloc
    products = {}
    seen_pages = set()
    queue = [cat_url]

    while queue and len(seen_pages) < max_pages:
        page_url = queue.pop(0)
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)

        html_text = fetch(page_url)
        for url, text in links_from(html_text, page_url):
            purl = canonical_product_url(url, host)
            if purl and text:
                name = " ".join(unescape(text).split())
                # Remove common quick-view/button noise.
                if name.lower() not in {
                    "quick view", "select options", "add to cart",
                    "read more", "view product"
                } and len(name) >= 3:
                    products.setdefault(name, purl)

            # Follow category pagination only.
            u = urlparse(url)
            if (
                u.netloc == host
                and "/product-category/" in u.path
                and re.search(r"/page/\d+/?$", u.path)
                and url not in seen_pages
                and url not in queue
            ):
                queue.append(url)

        time.sleep(0.35)

    return products


def model_field_names(model):
    return {f.name for f in model._meta.concrete_fields}


def category_lookup(name, parent=None):
    fields = model_field_names(Category)
    lookup = {"name": name}
    if "parent" in fields:
        lookup["parent"] = parent
    return lookup


def category_defaults(name):
    fields = model_field_names(Category)
    d = {}
    if "slug" in fields:
        d["slug"] = slugify(name)
    if "is_active" in fields:
        d["is_active"] = True
    return d


def required_product_defaults(name, category):
    """
    Populate only fields Django says are mandatory and have no model default.
    This keeps the command compatible with the current Product model without
    overwriting existing records.

    Neutral values are intentionally used. Pricing, dimensions and print
    surfaces should be configured by their dedicated import/sync processes.
    """
    result = {}
    for f in Product._meta.concrete_fields:
        if f.primary_key or f.auto_created or f.name in {"name", "category"}:
            continue
        if f.has_default() or f.null:
            continue
        if getattr(f, "blank", False):
            # blank is form-level; DB may still require a value.
            pass

        if isinstance(f, models.SlugField):
            # Assigned separately at creation time so category+slug uniqueness
            # can be checked against the database.
            continue
        elif isinstance(f, (models.CharField, models.TextField)):
            result[f.name] = ""
        elif isinstance(f, models.BooleanField):
            result[f.name] = True if f.name == "is_active" else False
        elif isinstance(f, (models.DecimalField, models.FloatField)):
            result[f.name] = Decimal("0")
        elif isinstance(f, (models.IntegerField, models.PositiveIntegerField,
                              models.PositiveSmallIntegerField,
                              models.SmallIntegerField, models.BigIntegerField)):
            # Internal canvas only. If dimensions are mandatory, use a neutral
            # square workspace; the later dimension sync will configure it.
            result[f.name] = 1000 if f.name in {"width", "height"} else 0
        elif isinstance(f, models.ForeignKey):
            # Unknown mandatory relations must not be guessed.
            raise CommandError(
                f"Product.{f.name} is a required ForeignKey with no default. "
                "Add an explicit mapping for it before applying the catalogue sync."
            )
        elif isinstance(f, (models.DateField, models.DateTimeField)):
            # auto_now/auto_now_add are handled by Django.
            if not getattr(f, "auto_now", False) and not getattr(f, "auto_now_add", False):
                raise CommandError(
                    f"Product.{f.name} is a required date field with no default. "
                    "Add an explicit default before applying."
                )
        elif isinstance(f, (models.FileField, models.ImageField)):
            result[f.name] = ""
        else:
            raise CommandError(
                f"Cannot safely infer required Product field {f.name} "
                f"({f.__class__.__name__}). Add an explicit default."
            )

    fields = model_field_names(Product)
    if "is_active" in fields:
        result["is_active"] = True
    # Slug is assigned at creation time with unique_product_slug(), because
    # Product enforces uniqueness on (category, slug).
    result.pop("slug", None)
    return result


def unique_product_slug(category, name):
    """
    Return a slug unique inside this category.

    Product has a database uniqueness constraint on (category, slug), so two
    different public product names that slugify to the same value must not
    collide. Existing rows are never changed.
    """
    base = slugify(name) or "product"
    candidate = base
    n = 2
    while Product.objects.filter(category=category, slug=candidate).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def find_existing_product(name, category=None):
    """
    Existing means:
      1) same name (case-insensitive), anywhere; OR
      2) same slug in the intended category.

    If either exists, SKIP. We never overwrite an existing Product.
    """
    by_name = Product.objects.filter(name__iexact=name).first()
    if by_name:
        return by_name

    if category is not None and "slug" in model_field_names(Product):
        candidate = slugify(name)
        if candidate:
            by_slug = Product.objects.filter(
                category=category,
                slug=candidate,
            ).first()
            if by_slug:
                return by_slug
    return None


class Command(BaseCommand):
    help = (
        "Create missing categories/products from the live public zenvibe.ca "
        "catalogue. Existing records are skipped and never overwritten."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--base-url", default=DEFAULT_BASE)
        parser.add_argument("--max-pages", type=int, default=30)

    def handle(self, *args, **opts):
        apply_changes = opts["apply"]
        base_url = opts["base_url"].rstrip("/")
        max_pages = opts["max_pages"]

        self.stdout.write(f"Reading live catalogue: {base_url}{SHOP_PATH}")
        try:
            shop_html = fetch(base_url + SHOP_PATH)
        except Exception as e:
            raise CommandError(f"Could not read ZenVibe shop: {e}")

        discovered = discover_category_urls(shop_html, base_url)

        # Crawl leaf categories where available; otherwise top-level category.
        crawl_categories = []
        for parent, children in CATEGORY_TREE.items():
            if children:
                crawl_categories.extend(children)
            else:
                crawl_categories.append(parent)

        catalogue = {}
        failed_categories = []
        self.stdout.write("Discovering products...")
        for cat_name in crawl_categories:
            url = category_url(cat_name, discovered, base_url)
            try:
                items = discover_products_for_category(
                    url, base_url, max_pages=max_pages
                )
            except Exception as e:
                failed_categories.append((cat_name, url, str(e)))
                self.stdout.write(self.style.WARNING(
                    f"  {cat_name}: FAILED to read {url}: {e}"
                ))
                continue

            catalogue[cat_name] = items
            self.stdout.write(f"  {cat_name}: {len(items)} products")

        # First prepare/category plan.
        cat_plan = []
        parent_objects = {}

        # Existing parents can be resolved immediately.
        for parent in CATEGORY_TREE:
            obj = Category.objects.filter(name__iexact=parent)
            if "parent" in model_field_names(Category):
                obj = obj.filter(parent__isnull=True)
            parent_objects[parent] = obj.first()

        existing_products = 0
        missing_products = []

        # Product plan can be made without writing categories.
        for cat_name, items in catalogue.items():
            for product_name, product_url in sorted(items.items()):
                existing = find_existing_product(product_name)
                if existing:
                    existing_products += 1
                else:
                    missing_products.append((cat_name, product_name, product_url))

        # Category status report.
        self.stdout.write("")
        self.stdout.write("CATEGORY PLAN")
        for parent, children in CATEGORY_TREE.items():
            pobj = parent_objects[parent]
            if pobj:
                self.stdout.write(f"  SKIP parent: {parent}")
            else:
                self.stdout.write(f"  CREATE parent: {parent}")

            for child in children:
                qs = Category.objects.filter(name__iexact=child)
                if "parent" in model_field_names(Category) and pobj:
                    qs = qs.filter(parent=pobj)
                child_exists = qs.exists()
                self.stdout.write(
                    f"    {'SKIP' if child_exists else 'CREATE'} child: {child}"
                )

        self.stdout.write("")
        self.stdout.write(
            f"Products discovered: {existing_products + len(missing_products)} | "
            f"already exist: {existing_products} | "
            f"missing: {len(missing_products)}"
        )
        for cat_name, name, url in missing_products:
            self.stdout.write(f"  CREATE [{cat_name}] {name}")

        if apply_changes and failed_categories:
            names = ", ".join(x[0] for x in failed_categories)
            raise CommandError(
                "Catalogue discovery was incomplete; nothing was written. "
                f"Failed categories: {names}. Wait a little and run the command again."
            )

        if not apply_changes:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(
                "Dry run complete. Database unchanged. "
                "Review the list, then rerun with --apply."
            ))
            return

        created_categories = 0
        created_products = 0
        skipped_products = 0

        with transaction.atomic():
            # Parents first.
            parent_objects = {}
            for parent in CATEGORY_TREE:
                qs = Category.objects.filter(name__iexact=parent)
                if "parent" in model_field_names(Category):
                    qs = qs.filter(parent__isnull=True)
                obj = qs.first()
                if not obj:
                    obj = Category.objects.create(
                        **category_lookup(parent, None),
                        **category_defaults(parent),
                    )
                    created_categories += 1
                parent_objects[parent] = obj

            # Children second.
            child_objects = {}
            for parent, children in CATEGORY_TREE.items():
                pobj = parent_objects[parent]
                for child in children:
                    qs = Category.objects.filter(name__iexact=child)
                    if "parent" in model_field_names(Category):
                        qs = qs.filter(parent=pobj)
                    obj = qs.first()
                    if not obj:
                        obj = Category.objects.create(
                            **category_lookup(child, pobj),
                            **category_defaults(child),
                        )
                        created_categories += 1
                    child_objects[child] = obj

            # Products. Recheck existence inside transaction.
            for cat_name, items in catalogue.items():
                category = child_objects.get(cat_name) or parent_objects.get(cat_name)
                if not category:
                    raise CommandError(f"Could not resolve category: {cat_name}")

                for product_name, product_url in sorted(items.items()):
                    # Rule requested for this importer:
                    # if the product already exists, SKIP it. Never update it.
                    existing = find_existing_product(product_name, category=category)
                    if existing:
                        skipped_products += 1
                        self.stdout.write(
                            f"  SKIP existing [{category.name}] {product_name} "
                            f"(DB id={existing.pk})"
                        )
                        continue

                    defaults = required_product_defaults(product_name, category)
                    product_fields = model_field_names(Product)

                    if "slug" in product_fields:
                        base_slug = slugify(product_name) or "product"

                        # Re-check slug before creating. If occupied in this
                        # category, treat it as EXISTING and skip -- do NOT make
                        # product-2/product-3, because this command's purpose is
                        # catalogue completion, not duplication.
                        slug_existing = Product.objects.filter(
                            category=category,
                            slug=base_slug,
                        ).first()
                        if slug_existing:
                            skipped_products += 1
                            self.stdout.write(
                                f"  SKIP existing slug [{category.name}] "
                                f"{product_name} -> {base_slug} "
                                f"(DB id={slug_existing.pk})"
                            )
                            continue
                        defaults["slug"] = base_slug

                    try:
                        with transaction.atomic():
                            Product.objects.create(
                                name=product_name,
                                category=category,
                                **defaults,
                            )
                        created_products += 1
                    except IntegrityError as e:
                        # Product.save() in this project can generate/normalise
                        # the slug itself. If that generated slug collides, this
                        # importer must SKIP the row rather than crash or create
                        # a duplicate.
                        skipped_products += 1
                        self.stdout.write(self.style.WARNING(
                            f"  SKIP database duplicate [{category.name}] "
                            f"{product_name}: {e}"
                        ))
                        continue

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Catalogue sync complete. Categories created: {created_categories}; "
            f"products created: {created_products}; "
            f"existing products skipped: {skipped_products}."
        ))
        self.stdout.write(self.style.WARNING(
            "No existing Product was overwritten. Physical dimensions, print "
            "surfaces, pricing, images and template assignments were not changed."
        ))
