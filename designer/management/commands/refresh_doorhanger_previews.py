"""Rebuild door-hanger previews from complete editable page objects.

Unlike the original marketing seeder, this renders the headline, description,
photo panels and CTA on top of the background. Existing template IDs are kept.

python manage.py refresh_doorhanger_previews --dry-run
python manage.py refresh_doorhanger_previews --apply
"""
import base64
import json
import re
from html import escape

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from designer.management.commands.seed_100_marketing_material_templates import (
    GENERATOR_ID, door_page, KINDS, THEMES, PALETTES, uri,
)
try:
    import cairosvg
except (ImportError, OSError):
    cairosvg=None

# Public Unsplash image IDs, one per industry theme. Photos are downloaded
# only when --apply is run, then embedded as data URIs in the editable JSON.
# This keeps the editor and preview independent of external image URLs.
PHOTO_IDS = [
    "photo-1497366754035-f200968a6e72",  # Corporate / office
    "photo-1600596542815-ffad4c1539a9",  # Real estate
    "photo-1517248135467-4c7edcad34c4",  # Restaurant
    "photo-1488646953014-85cb44e25828",  # Travel
    "photo-1540555700478-4be289fbecef",  # Wellness
    "photo-1576091160399-112ba8d25d1d",  # Healthcare
    "photo-1503676260728-1c00da094a0b",  # Education
    "photo-1518770660439-4636190af475",  # Technology
    "photo-1534438327276-14e5300c3a48",  # Fitness
    "photo-1460925895917-afdab827c52f",  # Finance
    "photo-1524504388940-b1c1722653e1",  # Beauty
    "photo-1504307651254-35680f356dfd",  # Construction
    "photo-1600607687920-4e2a09cf159d",  # Interior
    "photo-1492144534655-ae79c964c9d7",  # Automotive
    "photo-1511795409834-ef04bbd61622",  # Events
    "photo-1483985988355-763728e1935b",  # Fashion
    "photo-1452587925148-ce544e77e70d",  # Photography
    "photo-1589829545856-d10d557cf95f",  # Legal
    "photo-1552664730-d307ca884978",  # Marketing
    "photo-1529156069898-49953e39b3ac",  # Community
]

def theme_photo_data_uri(idx):
    from urllib.request import Request, urlopen
    photo_id = PHOTO_IDS[idx % len(PHOTO_IDS)]
    url = f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=700&h=700&q=80"
    request = Request(url, headers={"User-Agent": "ZenvibeTemplateBuilder/1.0"})
    with urlopen(request, timeout=12) as response:
        content_type = response.headers.get_content_type()
        content = response.read(2_500_001)
    if len(content) > 2_500_000 or content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise ValueError("Photo response was not a supported image")
    return "data:" + content_type + ";base64," + base64.b64encode(content).decode("ascii")

def svg_image_href(src):
    if src.startswith("data:image/svg+xml;base64,"):
        return src
    if src.startswith("data:image/png;base64,") or src.startswith("data:image/jpeg;base64,"):
        return src
    return None

def svg_preview(bg,objects,w,h):
    # Inline every editable text/photo object into a single complete preview.
    out=[bg.rsplit("</svg>",1)[0]]
    for o in objects:
        if o.get("backgroundAsset"):
            continue
        x=float(o.get("left",0));y=float(o.get("top",0))
        width=float(o.get("width",0));height=float(o.get("height",0))
        if o.get("type")=="image":
            href=svg_image_href(o.get("src",""))
            if href:
                out.append('<image x="%s" y="%s" width="%s" height="%s" href="%s" preserveAspectRatio="xMidYMid slice"/>'%
                           (x,y,width,height,escape(href,quote=True)))
        elif o.get("type")=="rect":
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" opacity="%s"/>'%
                       (x,y,width,height,escape(o.get("fill","#FFFFFF"),quote=True),o.get("opacity",1)))
        elif o.get("type") in ("textbox","text"):
            font=escape(o.get("fontFamily","Arial"),quote=True)
            color=escape(o.get("fill","#202020"),quote=True)
            size=float(o.get("fontSize",20))
            weight=str(o.get("fontWeight","normal"))
            align=o.get("textAlign","left")
            anchor={"center":"middle","right":"end"}.get(align,"start")
            tx=x+(width/2 if align=="center" else width if align=="right" else 0)
            text=str(o.get("text",""))
            # Text wrap within the same width used by the editor.
            maxchars=max(9,int(width/(size*.67)))
            lines=[]
            for paragraph in text.split("\n"):
                words=paragraph.split()
                line=""
                for word in words:
                    if len(line+" "+word)>maxchars and line:
                        lines.append(line);line=word
                    else:
                        line=(line+" "+word).strip()
                lines.append(line)
            out.append('<text x="%s" y="%s" text-anchor="%s" font-family="%s" font-size="%s" font-weight="%s" fill="%s">'%
                       (tx,y+size,anchor,font,size,weight,color))
            for k,line in enumerate(lines):
                out.append('<tspan x="%s" dy="%s">%s</tspan>'%
                           (tx,0 if k==0 else size*1.16,escape(line)))
            out.append('</text>')
    out.append("</svg>")
    return "".join(out)

class Command(BaseCommand):
    help="Refresh complete door hanger previews without deleting templates."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=None)
        p.add_argument("--dry-run",action="store_true")
        p.add_argument("--apply",action="store_true")
    def handle(self,*args,**opts):
        if opts["dry_run"]==opts["apply"]:
            raise CommandError("Choose exactly one of --dry-run or --apply")
        qs=DesignTemplate.objects.filter(is_active=True,name__startswith="ZV Door Hanger ")
        if opts["product_id"]:
            qs=qs.filter(product_id=opts["product_id"])
        rows=list(qs.order_by("pk"))
        if not rows:
            raise CommandError("No generated door hanger templates found")
        self.stdout.write("Found %d door-hanger templates; existing IDs will be preserved."%len(rows))
        if opts["dry_run"]:
            return
        changed=0
        photo_cache = {}
        for t in rows:
            data=t.json_data
            if isinstance(data,str):
                data=json.loads(data)
            if not isinstance(data,dict) or not data.get("pages"):
                self.stdout.write(self.style.WARNING("Skipping invalid JSON for %s"%t.pk));continue
            # Regenerate both pages for original generator templates to fix the
            # same poor layout in the editor, not just the thumbnail.
            match=re.search(r"ZV Door Hanger (\d+)",t.name)
            if not match:
                continue
            idx=int(match.group(1))-1
            if data.get("generator") not in (GENERATOR_ID,"zenvibe-doorhanger-complete-preview-v2"):
                self.stdout.write(self.style.WARNING("Skipping non-original template %s"%t.pk));continue
            theme_idx = idx % len(PHOTO_IDS)
            if theme_idx not in photo_cache:
                try:
                    photo_cache[theme_idx] = theme_photo_data_uri(theme_idx)
                except Exception as exc:
                    photo_cache[theme_idx] = None
                    self.stdout.write(self.style.WARNING(
                        "Photo download unavailable for theme %s: %s" % (theme_idx + 1, exc)
                    ))
            w=int(data.get("width",450));h=int(data.get("height",1100))
            pages=[]
            for side in range(2):
                bg,objects=door_page(idx,side,w,h)
                # Replace the generic placeholder on both sides with a real
                # industry photo; preserve image objects for customer replacement.
                photo_src = photo_cache.get(theme_idx)
                if photo_src:
                    for obj in objects:
                        if obj.get("id") in ("photo_front", "photo_back"):
                            obj["src"] = photo_src
                            obj["baseSrc"] = photo_src
                            obj["name"] = "Replace industry photo"
                            obj["customerEditable"] = True
                            obj["manualReplacement"] = True
                # Compose a single full-bleed artwork. The previous inset
                # white panel made the design look like a flyer inside a hanger.
                # All content now sits directly on a unified background.
                palette = PALETTES[(idx * 5 + side) % len(PALETTES)]
                primary, paper, accent, white, dark = palette
                background = {
                    "id": "door-artwork-base", "type": "rect",
                    "left": 0, "top": 0, "width": w, "height": h,
                    "fill": paper, "opacity": 1,
                    "selectable": False, "evented": False,
                    "customerEditable": False,
                }
                objects.insert(1, background)
                # Reserved top 20% for the door-hanger hole/cutout.
                # Decorative colour bands are part of the artwork, not a
                # second content card.
                objects.insert(2, {
                    "id": "door-artwork-header", "type": "rect",
                    "left": 0, "top": 0, "width": w, "height": h * .225,
                    "fill": primary, "opacity": 1,
                    "selectable": False, "evented": False,
                })
                objects.insert(3, {
                    "id": "door-artwork-accent", "type": "rect",
                    "left": 0, "top": h * .225, "width": w,
                    "height": max(4, h * .009),
                    "fill": accent, "opacity": 1,
                    "selectable": False, "evented": False,
                })
                if side == 0:
                    positions = {
                        "photo_front": (.075, .265, .85, .305),
                        "headline": (.075, .61, .85, None),
                        "subhead": (.075, .69, .85, None),
                        "offer": (.075, .79, .85, None),
                        "contact": (.075, .88, .85, None),
                    }
                    for obj in objects:
                        oid = obj.get("id")
                        if oid not in positions:
                            continue
                        xx, yy, ww, hh = positions[oid]
                        obj["left"] = round(w * xx, 2)
                        obj["top"] = round(h * yy, 2)
                        obj["width"] = round(w * ww, 2)
                        if hh is not None:
                            obj["height"] = round(h * hh, 2)
                        if oid != "photo_front":
                            obj["fill"] = dark if oid != "offer" else primary
                            obj["textAlign"] = "center"
                            obj["fontSize"] = round(min(
                                float(obj.get("fontSize", 20)),
                                w * (.053 if oid == "headline" else .037)
                            ), 2)
                else:
                    for obj in objects:
                        if obj.get("type") in ("textbox", "text"):
                            obj["fill"] = dark
                            obj["width"] = min(float(obj.get("width", w)), w * .85)
                # The first object is the original SVG background; the new
                # full-bleed base covers its patterns consistently in the
                # editor and in the rendered preview.
                pages.append({"name":"Front" if side==0 else "Back",
                              "width":w,"height":h,"objects":objects})
                if side==0:
                    preview=svg_preview(bg,objects,w,h)
            preview_bytes=preview.encode("utf-8")
            preview_ext="svg"
            if cairosvg:
                try:
                    preview_bytes=cairosvg.svg2png(bytestring=preview_bytes,output_width=600)
                    preview_ext="png"
                except (OSError, ValueError):
                    pass
            data["pages"]=pages
            data["generator"]="zenvibe-doorhanger-complete-preview-v2"
            t.json_data=json.dumps(data,ensure_ascii=False)
            t.preview.save("doorhanger-complete-%03d-%s.%s"%(idx+1,t.pk,preview_ext),ContentFile(preview_bytes),save=False)
            with transaction.atomic():
                t.save(update_fields=["json_data","preview"])
            changed+=1
        self.stdout.write(self.style.SUCCESS("Updated %d door-hanger previews and pages."%changed))
