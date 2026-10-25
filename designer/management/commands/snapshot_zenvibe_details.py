"""One-way snapshot of public ZenVibe.ca product details into the local Django DB.

Safety guarantees:
- NEVER deletes products, variants, tiers, images, categories, or local content.
- A failed/offline source leaves the local database unchanged.
- Empty scraped fields never overwrite non-empty local values.
- The storefront reads the local DB; it does not call ZenVibe.ca at page load.
- --apply is required to write anything.
"""
from __future__ import annotations
import json, re, time
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from designer.models import Product, ProductSizeVariant, ProductColorVariant, ProductPriceTier
from designer.management.commands.sync_zenvibe_catalog import fetch

BASE = "https://zenvibe.ca"
COLOR_HEX = {"black":"#000000","white":"#FFFFFF","blue":"#0000FF","red":"#FF0000","green":"#008000","yellow":"#FFFF00","orange":"#FFA500","purple":"#800080","pink":"#FFC0CB","grey":"#808080","gray":"#808080","silver":"#C0C0C0","gold":"#D4AF37","rose gold":"#B76E79","dark blue":"#00008B","dark green":"#006400"}

def soup(html):
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise RuntimeError("beautifulsoup4 is required. Run: pip install -r requirements.txt") from e
    return BeautifulSoup(html, "html.parser")

def clean_html(node):
    if not node: return ""
    for bad in node.select("script,style,form,button,.nbo-clear-option-wrap,.nbd-action-wrap"):
        bad.decompose()
    return str(node).strip()

def clean_text(node):
    if not node: return ""
    return " ".join(node.get_text(" ", strip=True).split())

def first_node(s, selectors):
    for sel in selectors:
        n=s.select_one(sel)
        if n: return n
    return None

def money(v):
    try: return Decimal(str(v).replace(",", "").replace("$", "").strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError): return None

def parse_price_range(s):
    txt=clean_text(first_node(s,["p.price",".summary .price"]))
    vals=[money(x) for x in re.findall(r"\$\s*([\d,]+(?:\.\d{1,2})?)",txt)]
    vals=[x for x in vals if x is not None]
    return (min(vals),max(vals)) if vals else (None,None)

def labeled_options(s, wanted):
    wanted=wanted.lower()
    out=[]
    for label in s.find_all(["label","th","div","span"]):
        lt=clean_text(label).strip().lower().rstrip(":")
        if lt != wanted: continue
        parent=label.parent
        if not parent: continue
        # select options
        sel=parent.find("select") or parent.find_next("select")
        if sel:
            for o in sel.find_all("option"):
                v=clean_text(o)
                if v and v.lower() not in {"choose an option","select","clear"}: out.append(v)
        # radio/checkbox labels in the same option block
        for x in parent.find_all(["label","span"]):
            v=clean_text(x)
            if v and v.lower().rstrip(":") != wanted and len(v)<80: out.append(v)
        if out: break
    # fallback from variation JSON attributes
    if not out:
        form=s.select_one("form.variations_form")
        if form and form.get("data-product_variations"):
            try:
                variations=json.loads(form.get("data-product_variations"))
                for v in variations:
                    for k,val in (v.get("attributes") or {}).items():
                        if wanted.replace(" ","") in k.lower().replace("_","").replace("-","") and val:
                            out.append(str(val).replace("-"," ").title())
            except Exception: pass
    seen=[]
    for v in out:
        if v not in seen: seen.append(v)
    return seen

def parse_variation_prices(s):
    form=s.select_one("form.variations_form")
    rows=[]
    if not form or not form.get("data-product_variations"): return rows
    try: variations=json.loads(form.get("data-product_variations"))
    except Exception: return rows
    for v in variations:
        price=money(v.get("display_price"))
        attrs=v.get("attributes") or {}
        size=""
        for k,val in attrs.items():
            if "size" in k.lower() and val: size=str(val).replace("-"," ").upper()
        if price is not None: rows.append((size,price))
    return rows

def parse_qty_tiers(s):
    # Handles visible Woo/NBD tables such as: <100 $1.49, 100-199 $1.99, 500+ $1.65
    text="\n".join(x.strip() for x in s.stripped_strings if x.strip())
    pattern=re.compile(r"(?m)^\s*(<\s*\d+|\d+\s*[-–]\s*\d+|\d+\+)\s*$\s*^\s*\$\s*([\d,]+(?:\.\d{1,2})?)\s*$")
    rows=[]
    for rng,price in pattern.findall(text):
        if rng.strip().startswith("<"): q=1
        else:
            m=re.search(r"\d+",rng); q=int(m.group()) if m else 1
        p=money(price)
        if p is not None: rows.append((q,p))
    # de-dupe quantity while preserving page order
    dedup={}
    for q,p in rows: dedup[q]=p
    return sorted(dedup.items())

def section_by_id_or_heading(s, ids, heading_terms):
    for ident in ids:
        n=s.find(id=ident)
        if n: return clean_html(n)
    # Find heading and capture siblings until next same/higher heading.
    for h in s.find_all(re.compile(r"^h[1-6]$")):
        title=clean_text(h).lower()
        if any(term in title for term in heading_terms):
            level=int(h.name[1]); chunks=[]
            for sib in h.next_siblings:
                name=getattr(sib,"name",None)
                if name and re.match(r"^h[1-6]$",name) and int(name[1])<=level: break
                if name: chunks.append(str(sib))
            if chunks: return "".join(chunks).strip()
    return ""

def snapshot_page(html):
    s=soup(html)
    short=clean_html(first_node(s,[".woocommerce-product-details__short-description",".product-short-description",".short-description"]))
    desc=section_by_id_or_heading(s,["tab-description"],["description"])
    info=section_by_id_or_heading(s,["tab-additional_information","tab-additional-information"],["additional information","product information"])
    guidelines=section_by_id_or_heading(s,["tab-design_guidelines","tab-design-guidelines","tab-design-guideline"],["design guideline","printing guideline","artwork guideline"])
    faqs=section_by_id_or_heading(s,["tab-faqs","tab-faq","tab-nbd_faq"],["frequently asked questions","faq"])
    lo,hi=parse_price_range(s)
    return {"short_description":short,"description":desc,"product_information":info,"printing_guidelines":guidelines,"faqs":faqs,"min_price":lo,"max_price":hi,"sizes":labeled_options(s,"Size"),"colors":labeled_options(s,"Color") or labeled_options(s,"Colour"),"tiers":parse_qty_tiers(s),"variation_prices":parse_variation_prices(s)}

class Command(BaseCommand):
    help="Safely snapshot ZenVibe.ca details into local products; never deletes/wipes local data."
    def add_arguments(self,p):
        p.add_argument("--apply",action="store_true",help="Write changes. Without this flag, dry-run only.")
        p.add_argument("--product-id",type=int)
        p.add_argument("--delay",type=float,default=.25)
        p.add_argument("--base-url",default=BASE)
    def handle(self,*args,**o):
        qs=Product.objects.all().order_by("id")
        if o["product_id"]: qs=qs.filter(pk=o["product_id"])
        ok=failed=0
        for product in qs.iterator():
            url=product.source_url or urljoin(o["base_url"].rstrip("/")+"/",f"product/{product.slug}/")
            try:
                html=fetch(url); data=snapshot_page(html)
                if not any([data["short_description"],data["description"],data["faqs"],data["min_price"]]):
                    raise RuntimeError("page did not contain recognizable product data")
            except Exception as e:
                failed+=1; self.stderr.write(self.style.WARNING(f"SKIP {product.id} {product.name}: {e}")); continue
            self.stdout.write(f"{'APPLY' if o['apply'] else 'DRY'} {product.id}: {product.name} <- {url}")
            if not o["apply"]:
                self.stdout.write(f"  sizes={data['sizes']} colors={data['colors']} tiers={data['tiers']} prices={data['min_price']}..{data['max_price']}")
                ok+=1; time.sleep(o["delay"]); continue
            with transaction.atomic():
                # Non-empty-only writes: source outage/blank parsing can never wipe local content.
                changed=[]
                for f in ["short_description","description","product_information","printing_guidelines","faqs","min_price","max_price"]:
                    v=data.get(f)
                    if v not in (None,""):
                        setattr(product,f,v); changed.append(f)
                if data["min_price"] is not None:
                    product.price=data["min_price"]; changed.append("price")
                product.source_url=url; product.source_synced_at=timezone.now(); changed += ["source_url","source_synced_at"]
                product.save(update_fields=list(dict.fromkeys(changed)))
                for i,name in enumerate(data["sizes"]):
                    ProductSizeVariant.objects.update_or_create(product=product,size_key=slugify(name)[:140],defaults={"name":name,"sort_order":i,"is_active":True})
                for i,name in enumerate(data["colors"]):
                    ProductColorVariant.objects.update_or_create(product=product,color_key=slugify(name)[:120],defaults={"name":name,"hex_value":COLOR_HEX.get(name.lower(),""),"sort_order":i,"is_active":True})
                # Do not delete old tiers. Upsert only successfully parsed tiers.
                for q,price in data["tiers"]:
                    ProductPriceTier.objects.update_or_create(product=product,variant=None,min_quantity=q,defaults={"unit_price":price,"is_active":True})
                # Variation price snapshot where a size can be identified.
                for size_name,price in data["variation_prices"]:
                    if not size_name: continue
                    variant=ProductSizeVariant.objects.filter(product=product,size_key=slugify(size_name)[:140]).first()
                    if variant:
                        ProductPriceTier.objects.update_or_create(product=product,variant=variant,min_quantity=product.minimum_quantity or 1,defaults={"unit_price":price,"is_active":True})
            ok+=1; time.sleep(o["delay"])
        self.stdout.write(self.style.SUCCESS(f"Finished. successful={ok}, skipped/failed={failed}, mode={'APPLY' if o['apply'] else 'DRY-RUN'}"))
        if failed: self.stdout.write("Skipped products were NOT modified. Existing local data remains intact.")
