"""
ZenVibe product-content synchronizer
Run from the Django project folder:
    python sync_zenvibe_product_details.py --dry-run
    python sync_zenvibe_product_details.py

What it does:
- Backs up db.sqlite3 before writing.
- Uses each product's source_url (or zenvibe.ca/product/<slug>/).
- Reads the REAL WooCommerce product tabs.
- Updates Description, Information, Printing Guidelines/Design Guidelines and FAQ separately.
- Never deletes products, templates, price tiers, images, print areas, saved designs or orders.
- Never blanks an existing field when the source tab is missing.
"""

import os, sys, re, time, shutil, argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from html import unescape

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zenvibe_site.settings")

import django
django.setup()

from django.db import transaction
from designer.models import Product

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise SystemExit("BeautifulSoup is required. Run: pip install beautifulsoup4")

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--delay", type=float, default=0.20)
parser.add_argument("--limit", type=int, default=0)
args = parser.parse_args()

DB = PROJECT / "db.sqlite3"
if not args.dry_run and DB.exists():
    backup = PROJECT / ("db_before_zenvibe_content_sync_" + time.strftime("%Y%m%d_%H%M%S") + ".sqlite3")
    shutil.copy2(DB, backup)
    print("BACKUP:", backup)

def fetch(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; ZenVibeCatalogueSync/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")

def clean_fragment(node):
    if not node:
        return ""
    # Remove scripts/forms/editor widgets/buttons while preserving product content.
    clone = BeautifulSoup(str(node), "html.parser")
    for bad in clone.select("script,style,form,button,noscript,.product-designer,.lumise-wrapper,.pc-editor"):
        bad.decompose()
    root = clone.find()
    if not root:
        return ""
    return "".join(str(x) for x in root.contents).strip()

def panel_label(panel):
    pid = (panel.get("id") or "").lower().replace("_"," ").replace("-"," ")
    classes = " ".join(panel.get("class") or []).lower().replace("_"," ").replace("-"," ")
    heading = panel.find(["h1","h2","h3","h4"])
    heading_text = heading.get_text(" ", strip=True).lower() if heading else ""
    return " ".join([pid, classes, heading_text])

def classify(panel):
    s = panel_label(panel)
    if "description" in s and "additional" not in s:
        return "description"
    if "additional information" in s or "additionalinformation" in s or "product information" in s:
        return "information"
    if "faq" in s or "frequently asked" in s:
        return "faqs"
    if any(x in s for x in (
        "design guideline", "design guidelines", "printing guideline",
        "printing guidelines", "artwork", "file setup", "artwork design"
    )):
        return "printing_guidelines"
    return None

def extract_tabs(html):
    soup = BeautifulSoup(html, "html.parser")
    found = {}

    # Standard WooCommerce panels.
    panels = soup.select(
        ".woocommerce-Tabs-panel, .woocommerce-tabs .panel, "
        "[role='tabpanel'][id^='tab-'], [id^='tab-'].panel"
    )
    for panel in panels:
        kind = classify(panel)
        if kind and kind not in found:
            content = clean_fragment(panel)
            if content and len(BeautifulSoup(content, "html.parser").get_text(" ", strip=True)) >= 2:
                found[kind] = content

    # Exact standard IDs take priority.
    exact = {
        "description": ["#tab-description"],
        "information": ["#tab-additional_information", "#tab-additional-information"],
        "faqs": ["#tab-faqs", "#tab-faq", "#tab-frequently-asked-questions"],
        "printing_guidelines": [
            "#tab-design-guidelines", "#tab-design_guidelines",
            "#tab-printing-guidelines", "#tab-printing_guidelines",
            "#tab-artwork-file-setup", "#tab-artwork-design"
        ],
    }
    for kind, selectors in exact.items():
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                content = clean_fragment(node)
                if content:
                    found[kind] = content
                    break
    return found

products = Product.objects.all().order_by("id")
if args.limit:
    products = products[:args.limit]

counts = {"checked":0, "updated":0, "failed":0, "no_tabs":0}
failures = []

for p in products:
    counts["checked"] += 1
    url = (getattr(p, "source_url", "") or "").strip()
    if not url:
        url = "https://zenvibe.ca/product/%s/" % p.slug

    try:
        html = fetch(url)
        tabs = extract_tabs(html)
        if not tabs:
            counts["no_tabs"] += 1
            failures.append((p.id, p.name, "No recognized product tabs", url))
            print("NO TABS:", p.id, p.name)
            continue

        changes = {}
        # IMPORTANT: only update fields that were actually found on the source page.
        # Missing source sections never erase existing local content.
        for field in ("description","product_information","printing_guidelines","faqs"):
            source_key = "information" if field == "product_information" else field
            value = tabs.get(source_key, "").strip()
            if value and value != (getattr(p, field) or "").strip():
                changes[field] = value

        if changes:
            print("UPDATE:", p.id, p.name, "=>", ", ".join(changes.keys()))
            if not args.dry_run:
                with transaction.atomic():
                    Product.objects.filter(pk=p.pk).update(**changes)
            counts["updated"] += 1
        else:
            print("OK:", p.id, p.name)

    except (HTTPError, URLError, TimeoutError, Exception) as e:
        counts["failed"] += 1
        failures.append((p.id, p.name, str(e), url))
        print("FAILED:", p.id, p.name, e)

    time.sleep(args.delay)

print("\nDONE")
for k,v in counts.items():
    print(k, "=", v)

if failures:
    report = PROJECT / "zenvibe_content_sync_failures.txt"
    report.write_text("\n".join(f"{i} | {n} | {err} | {url}" for i,n,err,url in failures), encoding="utf-8")
    print("Failure report:", report)
