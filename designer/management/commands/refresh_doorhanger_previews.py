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
    GENERATOR_ID, door_page, KINDS, THEMES, uri,
)
try:
    import cairosvg
except (ImportError, OSError):
    cairosvg=None

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
            w=int(data.get("width",450));h=int(data.get("height",1100))
            pages=[]
            for side in range(2):
                bg,objects=door_page(idx,side,w,h)
                # A consistent content panel protects text from diagonal
                # backgrounds and makes the preview match the editable editor.
                panel={"id":"door-content-panel","type":"rect","left":w*.065,
                       "top":h*.265,"width":w*.87,"height":h*.68,
                       "fill":"#FFFFFF","opacity":.97,
                       "selectable":False,"evented":False}
                objects.insert(1,panel)
                if side==0:
                    positions={
                        "photo_front":(.13,.30,.74,.22),
                        "headline":(.12,.56,.76,None),
                        "subhead":(.12,.66,.76,None),
                        "offer":(.12,.76,.76,None),
                        "contact":(.12,.87,.76,None),
                    }
                    for obj in objects:
                        oid=obj.get("id")
                        if oid not in positions: continue
                        xx,yy,ww,hh=positions[oid]
                        obj["left"]=w*xx
                        obj["top"]=h*yy
                        obj["width"]=w*ww
                        if hh is not None: obj["height"]=h*hh
                        if oid!="photo_front":
                            obj["fill"]="#203442"
                            obj["textAlign"]="center"
                            obj["fontSize"]=min(float(obj.get("fontSize",20)),w*.048 if oid=="headline" else w*.032)
                else:
                    for obj in objects:
                        if obj.get("type") in ("textbox","text"):
                            obj["fill"]="#203442"
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
