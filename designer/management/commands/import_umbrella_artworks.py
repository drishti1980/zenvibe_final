"""Import a curated umbrella artwork library without generating duplicate layouts.

Usage:
  python manage.py import_umbrella_artworks --product-id 205 --manifest path/to/manifest.json
  python manage.py import_umbrella_artworks --product-id 205 --manifest path/to/manifest.json --apply

Manifest is a JSON list of 100 records:
[{"name":"Floral Garden","artwork":"floral-garden.png",
  "headline":"YOUR BRAND","subtitle":"Beautiful days ahead",
  "photo":"optional-customer-photo.png"}, ...]
Files are relative to the manifest folder. Every artwork must be unique.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

LIBRARY="zenvibe-umbrella-curated-v1"
IMAGE_EXTENSIONS={".png",".webp",".jpg",".jpeg",".svg"}
MAX_BYTES=15*1024*1024

def _read_image(base,relative):
    if not isinstance(relative,str) or not relative.strip():
        raise CommandError("Missing artwork filename")
    target=(base/relative).resolve()
    if not target.is_relative_to(base):
        raise CommandError("Artwork path escapes manifest directory")
    if target.suffix.lower() not in IMAGE_EXTENSIONS:
        raise CommandError(f"Unsupported image format: {target.name}")
    if not target.is_file():
        raise CommandError(f"Artwork file not found: {target}")
    if target.stat().st_size > MAX_BYTES:
        raise CommandError(f"Artwork exceeds 15 MB: {target.name}")
    data=target.read_bytes()
    if target.suffix.lower()==".svg":
        from xml.etree import ElementTree
        try:
            root=ElementTree.fromstring(data)
        except ElementTree.ParseError as exc:
            raise CommandError(f"Invalid SVG: {target.name}: {exc}")
        if not root.tag.endswith("svg"):
            raise CommandError(f"Expected SVG root: {target.name}")
        forbidden=("script","foreignObject","iframe")
        for node in root.iter():
            if any(node.tag.endswith(x) for x in forbidden):
                raise CommandError(f"Unsafe SVG element in {target.name}")
            for k,v in node.attrib.items():
                if k.lower().startswith("on") or "javascript:" in v.lower() or ("href" in k.lower() and not v.startswith("#")):
                    raise CommandError(f"Unsafe SVG attribute in {target.name}")
    if not data:
        raise CommandError(f"Empty image: {target.name}")
    return target,data,hashlib.sha256(data).hexdigest()

class Command(BaseCommand):
    help="Validate and import 100 unique curated umbrella designs, preserving product colors."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,default=205)
        parser.add_argument("--manifest",required=True)
        parser.add_argument("--apply",action="store_true",
                            help="Write validated assets and templates; default is validation only")

    def handle(self,*args,**options):
        manifest=Path(options["manifest"]).resolve()
        if not manifest.is_file():
            raise CommandError(f"Manifest not found: {manifest}")
        base=manifest.parent
        try:
            items=json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError,ValueError) as exc:
            raise CommandError(f"Invalid manifest: {exc}")
        if not isinstance(items,list) or len(items)!=100:
            raise CommandError("Manifest must contain exactly 100 artworks")
        if not Product.objects.filter(pk=options["product_id"]).exists():
            raise CommandError("Umbrella product not found")
        prepared=[]
        hashes=set()
        names=set()
        for i,item in enumerate(items):
            if not isinstance(item,dict):
                raise CommandError(f"Entry {i+1}: expected object")
            name=str(item.get("name","")).strip()
            if not name or name.casefold() in names:
                raise CommandError(f"Entry {i+1}: missing or duplicate design name")
            names.add(name.casefold())
            file,data,digest=_read_image(base,item.get("artwork"))
            if digest in hashes:
                raise CommandError(f"Entry {i+1}: duplicate artwork bytes: {file.name}")
            hashes.add(digest)
            photo=None
            if item.get("photo"):
                photo=_read_image(base,item["photo"])
            prepared.append((i,item,name,file,data,digest,photo))
        self.stdout.write(self.style.SUCCESS("Validated 100 distinct artwork files and names"))
        if not options["apply"]:
            self.stdout.write("No changes made. Pass --apply to import.")
            return

        # Upload assets first; DB writes remain atomic. Old gallery stays intact
        # until every asset has been saved and all 100 templates are prepared.
        uploads=[]
        for i,item,name,file,data,digest,photo in prepared:
            key=f"zenvibe/umbrella-curated/{digest[:20]}{file.suffix.lower()}"
            if not default_storage.exists(key):
                default_storage.save(key,ContentFile(data))
            photo_url=None
            if photo:
                pf,pdata,pdigest=photo
                pkey=f"zenvibe/umbrella-curated/{pdigest[:20]}{pf.suffix.lower()}"
                if not default_storage.exists(pkey):
                    default_storage.save(pkey,ContentFile(pdata))
                photo_url=default_storage.url(pkey)
            uploads.append((i,item,name,default_storage.url(key),photo_url,digest))
        with transaction.atomic():
            product=Product.objects.select_for_update().get(pk=options["product_id"])
            existing=DesignTemplate.objects.filter(product=product,is_active=True)
            for i,item,name,url,photo_url,digest in uploads:
                # Artwork is an editable image object. User can replace or move it.
                objects=[{
                    "id":f"umbrella_{i+1:03d}_artwork","name":"Replaceable Artwork",
                    "type":"image","src":url,"left":185,"top":105,
                    "width":680,"height":730,"scaleX":1,"scaleY":1,
                    "angle":0,"opacity":1,"selectable":True,"evented":True,
                    "customerEditable":True,"replaceable":True,
                }]
                if photo_url:
                    objects.append({
                        "id":f"umbrella_{i+1:03d}_photo","name":"Customer Photo",
                        "type":"image","src":photo_url,"left":345,"top":255,
                        "width":360,"height":300,"scaleX":1,"scaleY":1,
                        "angle":0,"opacity":1,"selectable":True,"evented":True,
                        "customerEditable":True,"replaceable":True,
                    })
                # Large, readable brand lockup on the lower canopy panel.
                # Opaque dark plate protects contrast on all seven umbrella colours.
                headline=str(item.get("headline","")).strip()
                subtitle=str(item.get("subtitle","")).strip()
                if headline or subtitle:
                    objects.append({
                        "id":f"umbrella_{i+1:03d}_brand_backing",
                        "name":"Brand backing","type":"rect",
                        "left":275,"top":675,"width":500,"height":135,
                        "fill":"#142332","rx":12,"ry":12,
                        "scaleX":1,"scaleY":1,"angle":0,"opacity":0.96,
                        "selectable":True,"evented":True,"customerEditable":True,
                    })
                for suffix,value,y,size,weight,color in [
                    ("headline",headline,690,43,"800","#FFFFFF"),
                    ("subtitle",subtitle,755,21,"600","#F4D99C"),
                ]:
                    if value:
                        objects.append({
                            "id":f"umbrella_{i+1:03d}_{suffix}",
                            "name":suffix.title(),"type":"textbox","text":value,
                            "left":300,"top":y,"width":450,"fontSize":size,
                            "fontFamily":"Poppins","fontWeight":weight,
                            "textAlign":"center","fill":color,
                            "scaleX":1,"scaleY":1,"angle":0,"opacity":1,
                            "selectable":True,"evented":True,"customerEditable":True,
                        })
                page={"name":"Print Area","background":"transparent","objects":objects}
                payload={
                    "version":2,"templateType":"editable-master",
                    "generator":LIBRARY,"designName":name,
                    "document":{"width":1050,"height":1000,"unit":"in"},
                    "pageCount":1,"pages":[page],"adminPages":[page],
                    "editable":True,"editorNative":True,
                    "editorSchema":"fabric-primitives-v1",
                    "showProductMockup":True,"lockProductMockup":True,
                    "constrainToPrintArea":True,
                    "source":{"type":"curated-umbrella-artwork","sha256":digest},
                }
                DesignTemplate.objects.update_or_create(
                    product=product,name=f"Umbrella Curated {i+1:03d} — {name}",
                    defaults={"json_data":payload,"is_active":True}
                )
            existing.exclude(json_data__generator=LIBRARY).update(is_active=False)
        self.stdout.write(self.style.SUCCESS("Imported 100 curated umbrella designs"))
