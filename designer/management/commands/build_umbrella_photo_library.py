"""Build 100 photo-based umbrella templates from actual Zenvibe calendar/media assets.

This command NEVER fabricates photographs or replaces the active library when
there are fewer than 100 genuinely distinct source images.

python manage.py build_umbrella_photo_library
python manage.py build_umbrella_photo_library --apply
python manage.py build_umbrella_photo_library --asset-dir "C:/photos" --apply
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from designer.models import DesignTemplate

SUPPORTED={".png",".jpg",".jpeg",".webp"}
CATEGORIES=[
    ("Corporate Identity","YOUR LOGO","Brand your business"),
    ("Grand Opening","NOW OPEN","Visit us today"),
    ("Real Estate","PREMIER ESTATES","Exceptional properties"),
    ("Hospitality","THE GRAND HOTEL","Stay inspired"),
    ("Wedding","FOREVER & ALWAYS","Our special day"),
    ("Anniversary","CELEBRATE TOGETHER","A beautiful milestone"),
    ("Birthday","HAPPY BIRTHDAY","Celebrate in style"),
    ("Botanical","NATURE COLLECTION","Beautiful by nature"),
    ("Travel","EXPLORE MORE","Discover new horizons"),
    ("Seasonal Promotion","SPECIAL COLLECTION","Designed for every occasion"),
]

def walk_images(value):
    if isinstance(value,dict):
        kind=str(value.get("type","")).lower()
        if kind in ("image","photo","picture") or "image" in kind:
            for field in ("src","url","image","imageUrl","image_url"):
                val=value.get(field)
                if isinstance(val,str):
                    yield val
        for child in value.values():
            yield from walk_images(child)
    elif isinstance(value,list):
        for child in value:
            yield from walk_images(child)

def resolve_media_url(url,media_root,media_url):
    if not isinstance(url,str) or url.startswith("data:"):
        return None
    parsed=urlparse(url)
    prefix=urlparse(media_url).path.rstrip("/")+"/"
    path=unquote(parsed.path)
    if not path.startswith(prefix):
        return None
    relative=path[len(prefix):].lstrip("/")
    target=(media_root/relative).resolve()
    if not target.is_relative_to(media_root) or target.suffix.lower() not in SUPPORTED:
        return None
    return target if target.is_file() else None

def usable(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            w,h=im.size
            return w>=500 and h>=400
    except (OSError,ValueError):
        return False

def fingerprint(path):
    # Dedupe image content regardless of filename or compression.
    from PIL import Image,ImageOps
    with Image.open(path) as im:
        image=ImageOps.exif_transpose(im).convert("RGB").resize((32,32))
        return hashlib.sha256(image.tobytes()).hexdigest()

class Command(BaseCommand):
    help="Use 100 real, unique calendar/media photographs for umbrella designs."
    def add_arguments(self,parser):
        parser.add_argument("--asset-dir",default=None,
                            help="Optional directory of owned/licensed product and occasion photos")
        parser.add_argument("--apply",action="store_true")
        parser.add_argument("--product-id",type=int,default=205)

    def handle(self,*args,**options):
        media_root=Path(settings.MEDIA_ROOT).resolve()
        sources=[]
        # Reuse existing images in calendar template JSON (not network images).
        qs=DesignTemplate.objects.filter(product__name__icontains="calendar")
        for template in qs.iterator():
            for url in walk_images(template.json_data):
                target=resolve_media_url(url,media_root,settings.MEDIA_URL)
                if target:
                    sources.append(target)
        if options["asset_dir"]:
            folder=Path(options["asset_dir"]).resolve()
            if not folder.is_dir():
                raise CommandError(f"Asset directory does not exist: {folder}")
            sources.extend(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)
        unique={}
        for path in sources:
            if not usable(path):
                continue
            try:
                key=fingerprint(path)
            except (OSError,ValueError):
                continue
            unique.setdefault(key,path)
        if len(unique)<100:
            raise CommandError(
                f"Found only {len(unique)} usable, distinct local photographs. "
                "Need 100 before replacing the gallery. Add licensed images with "
                "--asset-dir, or import calendar images into MEDIA_ROOT. "
                "Existing umbrella templates were NOT changed."
            )
        out=Path(settings.BASE_DIR)/"umbrella_artworks"/"photography"
        out.mkdir(parents=True,exist_ok=True)
        manifest=[]
        for i,source in enumerate(list(unique.values())[:100]):
            label,headline,subtitle=CATEGORIES[i//10]
            # Use a separate real image for every template, never reuse photos.
            filename=f"photo-{i+1:03d}{source.suffix.lower()}"
            shutil.copyfile(source,out/filename)
            manifest.append({
                "name":f"{label} — Photo Edition {i%10+1:02d}",
                "artwork":filename,
                "headline":headline,
                "subtitle":subtitle,
            })
        target=out/"manifest.json"
        target.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Prepared 100 different photo templates: {target}"))
        if options["apply"]:
            call_command("import_umbrella_artworks",product_id=options["product_id"],
                         manifest=str(target),apply=True)
