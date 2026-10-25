#!/usr/bin/env python
"""
ZenVibe catalogue sync V3.

Purpose:
- Re-fetch product data from zenvibe.ca.
- Keep Description / Information / Printing Guidelines / FAQ separated.
- Populate Size, Colour, quantity pricing and generic source_attributes.
- Never touch templates, saved designs, orders, print areas, editor dimensions or product IDs.

Run beside manage.py:
  python sync_zenvibe_product_details_v3.py --dry-run
  python sync_zenvibe_product_details_v3.py
"""
import os, re, json, shutil, argparse, html as htmlmod
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from difflib import SequenceMatcher

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zenvibe_site.settings")
import django
django.setup()

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from bs4 import BeautifulSoup

from designer.models import Product, ProductSizeVariant, ProductColorVariant, ProductPriceTier

BASE = "https://zenvibe.ca"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36"

GENERIC_EDITOR_MARKERS = (
    "create your first design", "add and edit text", "rotate and resize",
    "align or position", "add images", "crop images", "apply image shapes",
    "download designs", "undo and redo changes", "save for later",
    "upload requirements", "group and ungroup", "duplicate from the context menu",
)

def fetch(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def clean_text(s):
    return re.sub(r"\s+", " ", htmlmod.unescape(s or "")).strip()

def norm_name(s):
    s = clean_text(s).lower()
    s = re.sub(r"\b(custom|premium|personalized|printed|canada|zenvibe|corporate|gifts?)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return clean_text(s)

def discover_urls():
    urls = set()
    for sitemap in ("/wp-sitemap.xml", "/sitemap_index.xml", "/product-sitemap.xml"):
        try:
            soup = BeautifulSoup(fetch(BASE+sitemap), "xml")
            for loc in soup.find_all("loc"):
                u = clean_text(loc.get_text())
                if "/product/" in u:
                    urls.add(u)
                elif "sitemap" in u and u != BASE+sitemap:
                    try:
                        ss = BeautifulSoup(fetch(u), "xml")
                        for x in ss.find_all("loc"):
                            v = clean_text(x.get_text())
                            if "/product/" in v: urls.add(v)
                    except Exception:
                        pass
        except Exception:
            pass
    # catalogue pages are fallback discovery
    for page in ("/shop/", "/templates-3/"):
        try:
            soup = BeautifulSoup(fetch(BASE+page), "html.parser")
            for a in soup.select('a[href*="/product/"]'):
                urls.add(urljoin(BASE, a.get("href")))
        except Exception:
            pass
    return sorted(urls)

def product_title(soup):
    h = soup.select_one("h1.product_title, h1.entry-title, h1")
    return clean_text(h.get_text(" ", strip=True)) if h else ""

def html_of(node):
    if not node: return ""
    return clean_fragment(node.decode_contents())

def clean_fragment(fragment):
    soup = BeautifulSoup(fragment or "", "html.parser")
    for x in soup.select("script,style,noscript,form,button,.designer,.lumise-wrapper,.nbd-designer"):
        x.decompose()
    return str(soup).strip()

def panel_by_heading(soup, names):
    # Prefer WooCommerce tab panel IDs/classes: avoids mixing adjacent tabs.
    selectors = []
    for n in names:
        k = re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
        selectors += [f"#tab-{k}", f"#tab_{k}", f".woocommerce-Tabs-panel--{k}"]
    for sel in selectors:
        n = soup.select_one(sel)
        if n: return n
    # Match tab anchor href -> exact panel.
    for a in soup.select(".woocommerce-tabs a, .wc-tabs a"):
        label = clean_text(a.get_text(" ", strip=True)).lower()
        if any(n.lower() in label for n in names):
            href = a.get("href","")
            if href.startswith("#"):
                n = soup.select_one(href)
                if n: return n
    return None

def strip_embedded_faq(fragment):
    if not fragment: return ""
    soup = BeautifulSoup(fragment, "html.parser")
    for tag in soup.find_all(["h2","h3","h4","strong"]):
        t = clean_text(tag.get_text(" ", strip=True)).lower()
        if t.startswith("faq") or "frequently asked questions" in t:
            # Remove heading and all following siblings from description only.
            cur = tag
            while cur:
                nxt = cur.find_next_sibling()
                cur.decompose()
                cur = nxt
            break
    return str(soup).strip()

def faq_from_description(fragment):
    if not fragment: return ""
    soup = BeautifulSoup(fragment, "html.parser")
    for tag in soup.find_all(["h2","h3","h4","strong"]):
        t = clean_text(tag.get_text(" ", strip=True)).lower()
        if t.startswith("faq") or "frequently asked questions" in t:
            parts=[str(tag)]
            cur=tag.find_next_sibling()
            while cur:
                parts.append(str(cur)); cur=cur.find_next_sibling()
            return "".join(parts)
    return ""

def trim_generic_editor_help(fragment):
    if not fragment: return ""
    soup = BeautifulSoup(fragment, "html.parser")
    for tag in soup.find_all(["h2","h3","h4","h5","strong"]):
        t=clean_text(tag.get_text(" ",strip=True)).lower()
        if any(m in t for m in GENERIC_EDITOR_MARKERS):
            cur=tag
            while cur:
                nxt=cur.find_next_sibling()
                cur.decompose()
                cur=nxt
            break
    return str(soup).strip()

def parse_attributes(soup):
    attrs={}
    table = panel_by_heading(soup, ["additional information"])
    if table:
        for tr in table.select("tr"):
            th=tr.find(["th","td"])
            cells=tr.find_all(["th","td"])
            if len(cells)>=2:
                label=clean_text(cells[0].get_text(" ",strip=True)).rstrip("*")
                value=clean_text(cells[1].get_text(" ",strip=True))
                vals=[clean_text(v) for v in re.split(r"\s*,\s*|\s*\|\s*", value) if clean_text(v)]
                if label and vals: attrs[label]=vals
    # Product option labels often live above tabs. Capture select/radio field text conservatively.
    text=soup.get_text("\n",strip=True)
    for label in ("Select Size","Size(W x H)","Size (D X H)","Select Color","Color","Colour",
                  "Printed Sides","Decoration Technology","Printing Method","Material"):
        m=re.search(rf"{re.escape(label)}\*?\s*\|\s*([^\n]+)", text, re.I)
        if m:
            vals=[clean_text(x) for x in m.group(1).split(",") if clean_text(x)]
            if vals: attrs[label]=vals
    return attrs

def split_attributes(attrs):
    sizes=[]; colors=[]; generic={}
    for label, vals in attrs.items():
        low=label.lower()
        if "size" in low:
            sizes += vals
        elif "color" in low or "colour" in low:
            colors += vals
        elif low not in {"quantity","price","unit price"}:
            generic[label.rstrip("*").strip()] = vals
    return list(dict.fromkeys(sizes)), list(dict.fromkeys(colors)), generic

def parse_price_tiers(soup):
    tiers=[]
    # Find rows with quantity-range + currency price.
    for tr in soup.select("tr"):
        cells=[clean_text(x.get_text(" ",strip=True)) for x in tr.find_all(["th","td"])]
        if len(cells)<2: continue
        q,p=cells[0],cells[1]
        pm=re.search(r"\$?\s*(\d+(?:\.\d{1,2})?)",p)
        if not pm: continue
        qm=re.search(r"(\d+)\s*\+",q) or re.search(r"(\d+)\s*-\s*\d+",q) or re.search(r"<\s*(\d+)",q)
        if not qm: continue
        n=int(qm.group(1))
        # "<30" is storefront's base band; treat minimum as 1.
        if q.strip().startswith("<"): n=1
        tiers.append((n, Decimal(pm.group(1))))
    # de-dupe
    return list(dict.fromkeys(tiers))

def parse_page(url):
    soup=BeautifulSoup(fetch(url),"html.parser")
    title=product_title(soup)
    desc_node=panel_by_heading(soup,["description"])
    info_node=panel_by_heading(soup,["additional information"])
    faq_node=panel_by_heading(soup,["faqs","faq"])
    art_node=panel_by_heading(soup,["artwork & file setup","artwork design"])
    guide_node=panel_by_heading(soup,["design guidelines","design guideline"])

    raw_desc=html_of(desc_node)
    embedded_faq=faq_from_description(raw_desc)
    description=strip_embedded_faq(raw_desc)
    information=html_of(info_node)
    faq=html_of(faq_node) or embedded_faq

    guide_parts=[]
    for n in (art_node,guide_node):
        h=trim_generic_editor_help(html_of(n))
        if h and h not in guide_parts: guide_parts.append(h)
    guidelines="\n".join(guide_parts)

    attrs=parse_attributes(soup)
    sizes,colors,generic=split_attributes(attrs)
    tiers=parse_price_tiers(soup)

    # visible headline price/range
    price_text=""
    price_node=soup.select_one(".summary .price, p.price, .price")
    if price_node: price_text=clean_text(price_node.get_text(" ",strip=True))
    prices=[Decimal(x) for x in re.findall(r"\$?\s*(\d+(?:\.\d{1,2})?)",price_text)]
    min_price=min(prices) if prices else (min((p for _,p in tiers),default=None))
    max_price=max(prices) if prices else (max((p for _,p in tiers),default=None))

    return dict(url=url,title=title,description=description,information=information,
                guidelines=guidelines,faq=faq,sizes=sizes,colors=colors,generic=generic,
                tiers=tiers,min_price=min_price,max_price=max_price)

def score(local, remote):
    a,b=norm_name(local),norm_name(remote)
    if not a or not b:return 0
    if a==b:return 1
    seq=SequenceMatcher(None,a,b).ratio()
    A,B=set(a.split()),set(b.split())
    jac=len(A&B)/max(1,len(A|B))
    return max(seq, jac, 0.96 if (a in b or b in a) and min(len(a),len(b))>10 else 0)

def match_product(p, pages):
    # source_url exact first
    if p.source_url:
        for x in pages:
            if x["url"].rstrip("/")==p.source_url.rstrip("/"): return x,1.0
    ranked=sorted(((score(p.name,x["title"]),x) for x in pages),reverse=True,key=lambda z:z[0])
    if not ranked:return None,0
    best=ranked[0]
    second=ranked[1][0] if len(ranked)>1 else 0
    if best[0] < .86 or (best[0] < .95 and best[0]-second < .04): return None,best[0]
    return best[1],best[0]

def upsert_variants(product, sizes, colors, tiers):
    for i,name in enumerate(sizes):
        key=slugify(name)[:140] or f"size-{i+1}"
        ProductSizeVariant.objects.update_or_create(
            product=product,size_key=key,
            defaults={"name":name,"sort_order":i,"is_active":True})
    for i,name in enumerate(colors):
        key=slugify(name)[:120] or f"color-{i+1}"
        ProductColorVariant.objects.update_or_create(
            product=product,color_key=key,
            defaults={"name":name,"sort_order":i,"is_active":True})
    # Only product-wide tiers from source. Do not delete size-specific tiers.
    for n,price in tiers:
        ProductPriceTier.objects.update_or_create(
            product=product,variant=None,min_quantity=n,
            defaults={"unit_price":price,"is_active":True})

def backup_db():
    from django.conf import settings
    src=Path(settings.DATABASES["default"]["NAME"])
    stamp=timezone.now().strftime("%Y%m%d_%H%M%S")
    dst=src.with_name(f"{src.stem}_before_zenvibe_v3_{stamp}{src.suffix}")
    shutil.copy2(src,dst)
    return dst

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--limit",type=int,default=0)
    args=ap.parse_args()

    urls=discover_urls()
    print(f"Discovered {len(urls)} source product URLs.")
    pages=[]
    for i,u in enumerate(urls,1):
        try:
            x=parse_page(u)
            if x["title"]: pages.append(x)
            print(f"FETCH {i}/{len(urls)} {x['title']}")
        except Exception as e:
            print("FETCH-FAILED",u,e)

    products=list(Product.objects.select_related("category").all())
    if args.limit: products=products[:args.limit]

    matches=[]; review=[]
    for p in products:
        x,s=match_product(p,pages)
        if not x:
            review.append({"id":p.id,"name":p.name,"best_score":round(s,3)})
            print(f"REVIEW {p.id}: {p.name} ({s:.3f})")
            continue
        matches.append((p,x,s))
        print(f"MATCH {p.id}: {p.name} -> {x['title']} [{s:.3f}] "
              f"size={len(x['sizes'])} color={len(x['colors'])} tiers={len(x['tiers'])} "
              f"attrs={list(x['generic'])} faq={'Y' if x['faq'] else 'N'} guide={'Y' if x['guidelines'] else 'N'}")

    Path("zenvibe_v3_match_review.json").write_text(json.dumps(review,indent=2),encoding="utf-8")
    if args.dry_run:
        print(f"\nDRY RUN: matched {len(matches)}, review {len(review)}. Database unchanged.")
        return

    print("Backup:",backup_db())
    with transaction.atomic():
        for p,x,s in matches:
            # Never blank existing fields when source section is absent.
            if x["description"]: p.description=x["description"]
            if x["information"]: p.product_information=x["information"]
            if x["guidelines"]: p.printing_guidelines=x["guidelines"]
            if x["faq"]: p.faqs=x["faq"]
            p.source_url=x["url"]
            p.source_synced_at=timezone.now()
            p.source_attributes=x["generic"] or {}
            if x["min_price"] is not None: p.min_price=x["min_price"]
            if x["max_price"] is not None: p.max_price=x["max_price"]
            if x["tiers"]:
                # first source tier defines storefront/base unit price
                p.price=x["tiers"][0][1]
                p.minimum_quantity=min(n for n,_ in x["tiers"])
            p.save()
            upsert_variants(p,x["sizes"],x["colors"],x["tiers"])
    print(f"DONE: updated {len(matches)} products. Review file contains {len(review)} unmatched/ambiguous rows.")

if __name__=="__main__":
    main()
