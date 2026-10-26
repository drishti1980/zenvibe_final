"""Regenerate coaster gallery previews from saved editable template JSON.

Requires Pillow. No artwork or customer designs are modified.
"""
from __future__ import annotations
import io
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import DesignTemplate
from PIL import Image, ImageDraw, ImageFont, ImageColor

SIZE=800
SCALE=SIZE/1000

def rgb(value):
    if not value or str(value).lower() in ("transparent","none","null"):
        return None
    try: return ImageColor.getrgb(str(value))
    except (ValueError,TypeError): return None

def font(size, family=""):
    n=max(9,round(float(size or 18)*SCALE))
    serif="georgia" in family.lower() or "serif" in family.lower()
    names=(["DejaVuSerif-Bold.ttf","C:/Windows/Fonts/georgiab.ttf"] if serif
           else ["DejaVuSans-Bold.ttf","C:/Windows/Fonts/arialbd.ttf"])
    for name in names:
        try: return ImageFont.truetype(name,n)
        except OSError: pass
    return ImageFont.load_default()

def render(objects,shape):
    im=Image.new("RGB",(SIZE,SIZE),"#ffffff")
    d=ImageDraw.Draw(im)
    for ob in objects:
        if not isinstance(ob,dict): continue
        kind=str(ob.get("type","")).lower()
        x=float(ob.get("left") or 0)*SCALE
        y=float(ob.get("top") or 0)*SCALE
        sx=float(ob.get("scaleX") or 1)
        sy=float(ob.get("scaleY") or 1)
        fill=rgb(ob.get("fill"))
        stroke=rgb(ob.get("stroke"))
        sw=max(1,round(float(ob.get("strokeWidth") or 1)*SCALE))
        if kind=="rect":
            w=float(ob.get("width") or 0)*SCALE*sx
            h=float(ob.get("height") or 0)*SCALE*sy
            d.rectangle((x,y,x+w,y+h),fill=fill,outline=stroke,width=sw)
        elif kind in ("circle","ellipse"):
            if kind=="circle":
                rx=ry=float(ob.get("radius") or 0)*SCALE
            else:
                rx=float(ob.get("rx") or 0)*SCALE
                ry=float(ob.get("ry") or 0)*SCALE
            rx*=sx;ry*=sy
            angle=float(ob.get("angle") or 0)
            if angle and kind=="ellipse":
                pad=max(4,int(max(rx,ry)*2+8))
                layer=Image.new("RGBA",(pad*2,pad*2))
                ld=ImageDraw.Draw(layer)
                ld.ellipse((pad-rx,pad-ry,pad+rx,pad+ry),fill=fill,outline=stroke,width=sw)
                layer=layer.rotate(-angle,resample=Image.Resampling.BICUBIC)
                im.paste(layer,(round(x+rx-pad),round(y+ry-pad)),layer)
                d=ImageDraw.Draw(im)
            else:
                d.ellipse((x,y,x+2*rx,y+2*ry),fill=fill,outline=stroke,width=sw)
        elif kind=="line" and all(k in ob for k in ("x1","y1","x2","y2")):
            points=tuple(float(ob[k])*SCALE for k in ("x1","y1","x2","y2"))
            d.line(points,fill=stroke or fill,width=sw)
        elif kind in ("text","textbox","i-text"):
            value=str(ob.get("text") or "")
            if not value: continue
            ft=font(ob.get("fontSize"),str(ob.get("fontFamily") or ""))
            width=float(ob.get("width") or 300)*SCALE
            align=ob.get("textAlign","left")
            line_h=max(12,int(float(ob.get("fontSize") or 18)*SCALE*1.25))
            for j,part in enumerate(value.split("\n")):
                bbox=d.textbbox((0,0),part,font=ft)
                tw=bbox[2]-bbox[0]
                tx=x+(width-tw)/2 if align=="center" else (x+width-tw if align=="right" else x)
                d.text((tx,y+j*line_h),part,fill=fill or "#222222",font=ft)
    if shape=="circle":
        mask=Image.new("L",(SIZE,SIZE),0)
        ImageDraw.Draw(mask).ellipse((0,0,SIZE-1,SIZE-1),fill=255)
        bg=Image.new("RGB",(SIZE,SIZE),"#f4f5f7")
        bg.paste(im,mask=mask)
        return bg
    return im

def artwork(template):
    data=template.json_data or {}
    for page in (data.get("pages") or data.get("adminPages") or []):
        if isinstance(page,dict) and isinstance(page.get("objects"),list) and page["objects"]:
            return page["objects"]
    return None

class Command(BaseCommand):
    help="Rebuild coaster previews without modifying editable JSON."

    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,required=True)
        parser.add_argument("--shape",choices=("circle","square"),default="circle")
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        if opts["dry_run"]==opts["apply"]:
            raise CommandError("Specify exactly one of --dry-run or --apply")
        qs=DesignTemplate.objects.filter(
            product_id=opts["product_id"],is_active=True,
            json_data__generator__startswith="zenvibe-promotional-"
        ).order_by("id")
        previews=[]
        for template in qs:
            objects=artwork(template)
            if not objects:
                raise CommandError(f"Template {template.id} has no editable objects")
            try:
                image=render(objects,opts["shape"])
                buf=io.BytesIO()
                image.save(buf,format="PNG",optimize=True)
                previews.append((template,buf.getvalue()))
            except Exception as exc:
                raise CommandError(f"Template {template.id}: {exc}") from exc
        if not previews: raise CommandError("No generated coaster templates found")
        self.stdout.write(f"Validated {len(previews)} previews.")
        if opts["dry_run"]:
            self.stdout.write("No files or database rows changed.")
            return
        for template,png in previews:
            name=f"coaster-{template.id}-{opts['shape']}-v4.png"
            template.preview.save(name,ContentFile(png),save=False)
            template.save(update_fields=["preview"])
        self.stdout.write(self.style.SUCCESS(f"Updated {len(previews)} previews."))
