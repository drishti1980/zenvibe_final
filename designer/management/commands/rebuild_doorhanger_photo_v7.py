"""Photo-led luxury door hangers: 100 complete 2-sided designs.

The calendar gallery is photo-led; this installer gives door hangers the same
visual completeness: themed photography + brand + strong headline + offer +
contact details. Five *different* layouts per industry, not colour swaps.

Images are cached locally and embedded into Fabric page JSON. The full gallery
preview is a front/back product mockup rendered from those exact page objects.
No storefront UI changes; no contact with zenvibe.ca. Rebuilds generated rows
in-place, preserves PKs and customer SavedDesign references, and backs up JSON.

python manage.py rebuild_doorhanger_photo_v7 --dry-run
python manage.py rebuild_doorhanger_photo_v7 --apply
python manage.py rebuild_doorhanger_photo_v7 --product-id 170 --apply

Optional: --photo-dir DIRECTORY uses 01.jpg ... 20.jpg (or .png/.webp).
Otherwise uses a cached local image or fetches a curated Unsplash photo.
If photographs cannot be obtained, it FAILS WITHOUT database changes instead
of silently declaring an empty vector card to be "premium".
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError

from designer.models import Product, DesignTemplate, SavedDesign
from designer.management.commands.rebuild_doorhanger_luxury_100 import (
    Art, THEMES, STYLES, EDITIONS, safe_text_size, source_dimensions,
    GENERATOR as V6_GENERATOR, LEGACY_GENERATORS,
)

GENERATOR = "zenvibe-doorhanger-premium-photo-v7"
# Curated photos: original theme order remains identical to THEMES.
PHOTO_IDS = (
    "photo-1497366754035-f200968a6e72",  # Corporate office
    "photo-1600596542815-ffad4c1539a9",  # Beautiful home
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
)
assert len(PHOTO_IDS) == len(THEMES) == 20
RESAMPLE = Image.Resampling.LANCZOS


def edition_for(index):
    # Mix different art directions within the *first visible gallery row*.
    # Every industry still receives all 5 different compositions across 100.
    return (index // 20 + index % 5) % 5


def _font(px, bold=False):
    """Available system fonts are not required on the production server."""
    names = (("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf")
             if bold else
             ("DejaVuSans.ttf", "LiberationSans-Regular.ttf", "arial.ttf"))
    for name in names:
        try:
            return ImageFont.truetype(name, max(7, round(px)))
        except OSError:
            continue
    return ImageFont.load_default()


def _hex(color, alpha=255):
    try:
        rgb = ImageColor.getrgb(str(color))
    except ValueError:
        rgb = (40, 40, 40)
    return (*rgb[:3], alpha)


def _source_image(data):
    if len(data) > 6_000_000:
        raise CommandError("Photograph exceeds the 6MB source size limit")
    try:
        with Image.open(io.BytesIO(data)) as src:
            src.load()
            if src.width < 450 or src.height < 450:
                raise CommandError("Photo resolution is too low for printable design")
            if src.width * src.height > 40_000_000:
                raise CommandError("Photo is larger than 40 megapixels")
            return ImageOps.exif_transpose(src).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise CommandError("Invalid or unreadable photograph: %s" % exc)


def _jpeg(image, quality=88):
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _uri(data):
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def _photo_source(theme_index, root, user_dir=None):
    """Use custom licensed artwork first, cached image second, remote last."""
    root.mkdir(parents=True, exist_ok=True)
    candidates = []
    if user_dir:
        for extension in ("jpg", "jpeg", "png", "webp"):
            candidates += [
                user_dir / ("%02d.%s" % (theme_index+1, extension)),
                user_dir / ("%03d.%s" % (theme_index+1, extension)),
            ]
    candidates.append(root / ("%02d.jpg" % (theme_index+1)))
    for path in candidates:
        if path.exists():
            return _source_image(path.read_bytes()), str(path)
    image_id = PHOTO_IDS[theme_index]
    # Only one request per theme; reuse the image for all five independent layouts.
    # Force ordinary JPEG so both Windows Pillow and Fabric receive a stable type.
    url = "https://images.unsplash.com/%s?fit=crop&w=1050&h=1400&q=86&fm=jpg" % image_id
    try:
        req = Request(url, headers={"User-Agent":"ZenvibeDesignSeeder/1.0"})
        with urlopen(req, timeout=14) as response:
            content_type=response.headers.get_content_type()
            if content_type not in ("image/jpeg","image/png","image/webp"):
                raise CommandError("Photo source returned unexpected Content-Type: "+content_type)
            data=response.read(6_000_001)
        image=_source_image(data)
        # Persist the exact original/crop source for reproducible reruns.
        cached=root / ("%02d.jpg" % (theme_index+1))
        cached.write_bytes(_jpeg(image))
        return image, url
    except (OSError, ValueError, CommandError) as exc:
        raise CommandError(
            "Door-hanger industry photo %02d unavailable: %s. "
            "No templates have been changed. Provide a licensed photo via "
            "--photo-dir (01.jpg ... 20.jpg), or restore internet access." %
            (theme_index+1, exc)
        )


def _crop(source, width, height, edition, seed=0):
    ww=max(180,int(width));hh=max(180,int(height))
    centres=((.50,.48),(.52,.42),(.47,.51),(.62,.51),(.43,.43))
    cx,cy=centres[edition%len(centres)]
    # A dedicated crop for each layout avoids stretching any photograph.
    cropped=ImageOps.fit(source,(ww,hh),method=RESAMPLE,centering=(cx,cy))
    return _jpeg(cropped,quality=87)


def _add_photo(art, photo_bytes, x,y,w,h, name):
    return art.add("image",name,x,y,w,h,"transparent",
        src=_uri(photo_bytes),baseSrc=_uri(photo_bytes),
        fieldType="replaceable-industry-photo",manualReplacement=True,
        customerEditable=True,selectable=True,evented=True,
        backgroundAsset=False)


def _label(art, name, text, x,y,w,h,color,relative=.052,bold=False, align="center"):
    size=safe_text_size(text,w,h,art.w*relative)
    return art.text(name,text,x,y,w,h,color,size,
                    bold=bold,align=align,spacing=0)


def _accent(art,w,h,edition,theme,foil,ink,panel):
    # Distinct decorative signatures across the five editions.
    # Keep the entire knob-hole region clear (safe area starts at .255 H).
    if edition==0:
        art.rect(w*.10,h*.275,w*.80,h*.004,foil,"Elegant thin rule")
        art.circle(w*.5,h*.285,w*.013,foil,"Editorial seal")
    elif edition==1:
        art.rect(w*.10,h*.27,w*.80,h*.010,foil,"Bold editorial rail")
        art.rect(w*.10,h*.28,w*.24,h*.005,ink,"Secondary rail")
    elif edition==2:
        for j in range(5):
            art.circle(w*(.23+j*.135),h*.278,w*.011,foil,"Botanical pearls")
    elif edition==3:
        art.rect(w*.11,h*.28,w*.025,h*.036,foil,"Architectural monogram")
        art.rect(w*.15,h*.28,w*.025,h*.036,ink,"Offset line")
    else:
        art.circle(w*.17,h*.281,w*.017,foil,"Gallery detail")
        art.circle(w*.83,h*.281,w*.017,foil,"Gallery detail")


def _back(index,w,h,source):
    theme=index%20;edition=edition_for(index)
    brand,headline,subtitle,cta,benefits,motif,accent=THEMES[theme]
    style=STYLES[edition]
    bg=style["bg"];ink=style["ink"];muted=style["muted"]
    foil="#E6C893" if style["light"] else accent
    a=Art(w,h)
    a.rect(0,0,w,h,bg,"Locked substrate",editable=False)
    a.rect(w*.10,h*.27,w*.80,h*.006,foil,"Premium hairline")
    _label(a,"Editable brand",brand,w*.12,h*.288,w*.76,h*.042,ink,.058,True)
    pic=_crop(source,w*.75,h*.23,edition,theme)
    _add_photo(a,pic,w*.125,h*.36,w*.75,h*.23,"Change back-page industry photo")
    a.rect(w*.10,h*.600,w*.80,h*.006,foil,"Section rule")
    _label(a,"Editable back headline","WHY CHOOSE US",w*.08,h*.620,w*.84,h*.066,ink,.08,True)
    for j,benefit in enumerate(benefits):
        yy=h*(.704+j*.060)
        a.circle(w*.165,yy+h*.017,w*.010,foil,"Editable feature bullet")
        _label(a,"Editable feature %s"%(j+1),benefit,
               w*.215,yy,w*.69,h*.047,ink,.051,j==0,align="left")
    a.rect(w*.10,h*.899,w*.80,h*.050,foil,"Contact highlight")
    _label(a,"Editable call to action",cta,w*.125,h*.901,w*.75,h*.043,
           "#172C32",.047,True)
    _label(a,"Editable website","YOURBRAND.COM",w*.12,h*.960,w*.76,h*.028,
           ink,.029,False)
    a.validate()
    return {"name":"Back","width":w,"height":h,"canvas":{"width":w,"height":h},
            "background":bg,"objects":a.objects}


def _front(index,w,h,source):
    theme=index%20;edition=edition_for(index)
    brand,headline,subtitle,cta,benefits,motif,accent=THEMES[theme]
    style=STYLES[edition]
    bg=style["bg"];ink=style["ink"];muted=style["muted"]
    foil="#D9B780" if style["light"] else accent
    a=Art(w,h)
    a.rect(0,0,w,h,bg,"Locked substrate",editable=False)
    _accent(a,w,h,edition,theme,foil,ink,style["panel"])
    _label(a,"Editable brand",brand,w*.10,h*.298,w*.80,h*.041,ink,.054,True)
    if edition==0:  # Photography hero, headline below
        photo=(.08,.365,.84,.345)
        title=(.08,.728,.84,.102)
        sub=(.11,.839,.78,.041)
    elif edition==1:  # Bold magazine headline, photography below
        title=(.075,.359,.85,.123)
        photo=(.09,.503,.82,.264)
        sub=(.10,.792,.80,.044)
    elif edition==2:  # Immersive cover image, quiet type underneath
        photo=(.08,.355,.84,.400)
        title=(.075,.776,.85,.098)
        sub=(.10,.881,.80,.032)
    elif edition==3:  # Split-column architectural gallery
        photo=(.075,.397,.46,.355)
        title=(.555,.454,.39,.184)
        sub=(.10,.784,.80,.052)
    else:  # Contemporary image with layered band
        photo=(.10,.358,.80,.327)
        title=(.075,.708,.85,.119)
        sub=(.10,.849,.80,.041)

    px,py,pw,ph=photo
    image_bytes=_crop(source,w*pw,h*ph,edition,theme)
    _add_photo(a,image_bytes,w*px,h*py,w*pw,h*ph,"Replace main industry photograph")
    # Editable photo framing; not the empty rectangle used in V6.
    if edition in (0,3):
        a.rect(w*.085,h*(py+ph+.009),w*.83,h*.006,foil,"Photo accent stroke")
    elif edition==4:
        a.rect(w*.10,h*.692,w*.80,h*.009,foil,"Layered gold divider")
    tx,ty,tw,th=title
    _label(a,"Editable headline",headline,w*tx,h*ty,w*tw,h*th,ink,
           .089 if edition!=3 else .068,True)
    sx,sy,sw,sh=sub
    _label(a,"Editable supporting copy",subtitle,w*sx,h*sy,w*sw,h*sh,
           muted,.044,False)
    # Small editable foil details complete the frame without repeating colour-only layouts.
    a.rect(w*.11,h*.956,w*.11,h*.003,foil,"Footer foil detail")
    a.rect(w*.78,h*.956,w*.11,h*.003,foil,"Footer foil balance")
    # CTA is a distinct large typographic band with strong colour contrast.
    # Special edition 2 uses a narrower callout because its photograph is taller.
    cta_y=.913 if edition==2 else .896
    a.rect(w*.10,h*cta_y,w*.80,h*.055,foil,"Editable action strip")
    _label(a,"Editable call to action",cta,w*.12,h*(cta_y+.004),w*.76,h*.045,
           "#172C32",.050,True)
    _label(a,"Editable website","YOURBRAND.COM",w*.12,h*.971,w*.76,h*.025,
           ink,.028,False)
    a.validate()
    return {"name":"Front","width":w,"height":h,"canvas":{"width":w,"height":h},
            "background":bg,"objects":a.objects}


def _draw_objects(page, scale):
    w=round(page["width"]*scale);h=round(page["height"]*scale)
    img=Image.new("RGBA",(w,h),(255,255,255,0))
    drawer=ImageDraw.Draw(img,"RGBA")
    for o in page["objects"]:
        kind=o["type"]
        x=round(float(o["left"])*scale);y=round(float(o["top"])*scale)
        ww=round(float(o["width"])*scale);hh=round(float(o["height"])*scale)
        fill=_hex(o.get("fill") or "#FFFFFF")
        if kind=="rect":
            if ww>0 and hh>0:
                rad=min(ww//3,round(float(o.get("rx") or 0)*scale))
                drawer.rounded_rectangle((x,y,x+ww,y+hh),radius=max(0,rad),fill=fill)
        elif kind=="circle":
            drawer.ellipse((x,y,x+ww,y+hh),fill=fill)
        elif kind=="ellipse":
            drawer.ellipse((x,y,x+ww,y+hh),fill=fill)
        elif kind=="image":
            src=str(o.get("src") or "")
            if not src.startswith("data:image/jpeg;base64,"):
                raise CommandError("Image must be an embedded valid JPEG")
            with Image.open(io.BytesIO(base64.b64decode(src.split(",",1)[1]))) as decoded:
                photo=ImageOps.exif_transpose(decoded).convert("RGB")
                photo=ImageOps.fit(photo,(ww,hh),method=RESAMPLE)
            img.paste(photo,(x,y))
        elif kind=="textbox":
            font=_font(float(o.get("fontSize") or 18)*scale,
                      str(o.get("fontWeight")) in ("bold","700"))
            text=str(o.get("text") or "")
            lines=text.split("\n")
            ink=_hex(o.get("fill") or "#222222")
            align=o.get("textAlign","center")
            anchor="ma" if align=="center" else "ra" if align=="right" else "la"
            tx=x+ww/2 if align=="center" else x+ww if align=="right" else x
            line_h=float(o.get("fontSize") or 18)*scale*1.1
            for j,line in enumerate(lines):
                drawer.text((tx,y+j*line_h),line,font=font,fill=ink,anchor=anchor)
    # Gallery mask is NOT a manufacturing dieline. A realistic door-hanger
    # hole/slit is deliberately visible only in thumbnail mockups.
    mask=Image.new("L",(w,h),255)
    m=ImageDraw.Draw(mask)
    cx=w//2;cy=round(h*.13);radius=round(w*.089)
    m.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=0)
    m.rectangle((cx+radius*.80,cy-radius*.08,w,cy+radius*.08),fill=0)
    img.putalpha(mask)
    return img


def _mockup(front,back,edition):
    """Portrait front-led photo mockup sized to the EXISTING gallery card.

    The previous 1080x860 horizontal image shrank a physical door hanger into
    a tiny box in a 8.5:11 portrait card. This artwork uses the same editorial
    density as the photo-calendar gallery without changing storefront CSS.
    """
    cw,ch=900,1160
    canvas=Image.new("RGB",(cw,ch),(242,240,237))
    d=ImageDraw.Draw(canvas)
    for y in range(ch):
        shade=int(249-16*y/ch)
        d.line((0,y,cw,y),fill=(shade,shade-1,shade-2))
    d.rounded_rectangle((18,18,cw-18,ch-18),radius=22,
                        fill=(249,248,245),outline=(218,215,209),width=2)
    d.text((50,52),"PHOTO-LED  •  CUSTOMISABLE",
           font=_font(24,True),fill=(54,63,66))
    d.text((45,ch-62),"FRONT ARTWORK" if not back else "FRONT  /  BACK",
           font=_font(20,True),fill=(97,98,96))
    # The front dominates the card. The actual back design is shown as a
    # smaller second product, never as an invented placeholder.
    if back:
        f1=min(.90,(ch-235)/max(1,front["height"]),500/max(1,front["width"]))
        f2=min(.62,(ch-420)/max(1,back["height"]),270/max(1,back["width"]))
        p1=_draw_objects(front,f1)
        p2=_draw_objects(back,f2)
        pieces=((p1,65+(500-p1.width)//2,125+(930-p1.height)//2),
                (p2,570+(270-p2.width)//2,280+(730-p2.height)//2))
    else:
        f1=min(.93,(ch-210)/max(1,front["height"]),750/max(1,front["width"]))
        p1=_draw_objects(front,f1)
        pieces=((p1,(cw-p1.width)//2,115+(945-p1.height)//2),)
    for picture,x,y in pieces:
        shadow=Image.new("RGBA",(picture.width+30,picture.height+30),(0,0,0,0))
        silhouette=picture.getchannel("A")
        blur=silhouette.filter(ImageFilter.GaussianBlur(13))
        shadow.paste((0,0,0,125),
                     (14,14,14+picture.width,14+picture.height),blur)
        canvas.paste(shadow,(x-14,y-14),shadow)
        canvas.paste(picture,(x,y),picture)
    out=io.BytesIO()
    canvas.save(out,format="PNG",optimize=True)
    return out.getvalue()


def _master(index,pages,source):
    tag=THEMES[index%20][0]
    direction=EDITIONS[edition_for(index)]
    signature=hashlib.sha256(json.dumps([
        [(o["type"],o["name"],o["left"],o["top"],o["width"],
          o["height"],o.get("text")) for o in page["objects"]]
        for page in pages
    ],sort_keys=True).encode()).hexdigest()
    return {
        "generator":GENERATOR,"version":7,
        "templateType":"editable-master","editorNative":True,"editable":True,
        "designFamily":tag,"composition":direction,"compositionSignature":signature,
        "width":pages[0]["width"],"height":pages[0]["height"],
        "pageCount":len(pages),"pages":pages,
        "previewComplete":True,
        "photoSource":("curated-photography" if source.startswith("https://") else Path(source).name),
        "photoEditable":True,
        "printNote":"Use manufacturer-supplied door-hole dimensions for production cutting.",
    }


class Command(BaseCommand):
    help="Install/refresh 100 photo-led premium door hangers and gallery mockups safely."

    def add_arguments(self,p):
        p.add_argument("--product-id",type=int)
        p.add_argument("--photo-dir",default="",help="Optional 01.jpg ... 20.jpg licensed originals")
        mode=p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        products=Product.objects.filter(is_active=True,name__icontains="door hanger")
        if opts["product_id"]:
            products=products.filter(pk=opts["product_id"])
        if not products.exists():
            raise CommandError("No active door-hanger product found")
        for product in products:
            self.rebuild(product,opts)

    def rebuild(self,product,opts):
        existing=list(DesignTemplate.objects.filter(product=product,is_active=True)
                      .order_by("pk"))
        known={}
        accepted=LEGACY_GENERATORS | {V6_GENERATOR,GENERATOR}
        for t in existing:
            match=re.match(r"^ZV Door Hanger\s+(\d{1,3})\b",t.name)
            if not match:
                raise CommandError("Non-generated door-hanger master found. Refusing overwrite.")
            idx=int(match.group(1))-1
            if not 0<=idx<100 or idx in known:
                raise CommandError("Duplicate/out-of-range generated door-hanger index")
            data=t.json_data
            if isinstance(data,str):
                try:data=json.loads(data)
                except (ValueError,TypeError):raise CommandError("Malformed template JSON")
            if not isinstance(data,dict) or data.get("generator") not in accepted:
                raise CommandError("Unrecognised generated master; refusing unsafe overwrite")
            known[idx]=t
        w,h=source_dimensions(product,list(known.values()))
        surfaces=list(product.print_surfaces.filter(is_active=True)
                      .order_by("sort_order","id"))
        if len(surfaces)>2 or any(
            float(s.print_width_in or 0)<=0 or float(s.print_height_in or 0)<=0
            for s in surfaces
        ):
            raise CommandError("Door-hanger surfaces require 1 or 2 valid Admin print faces")
        side_count=len(surfaces) if surfaces else 2
        photo_root=Path(settings.MEDIA_ROOT)/"template_photo_library"/"doorhanger"
        supplied=Path(opts["photo_dir"]) if opts["photo_dir"] else None
        # Dry-run is fully offline: validate placeholder photographs, all 100
        # geometry layouts, and preview construction without touching disk.
        if opts["dry_run"]:
            sample=Image.new("RGB",(1000,1400),(166,177,167))
            photo_sources=[(sample,"DRY-RUN SAMPLE")]*20
        else:
            photo_sources=[_photo_source(i,photo_root,supplied) for i in range(20)]
        built=[]
        unique=set()
        for idx in range(100):
            source,label=photo_sources[idx%20]
            pages=[_front(idx,w,h,source)]
            if side_count==2:
                pages.append(_back(idx,w,h,source))
            for side,surface in enumerate(surfaces):
                pages[side]["name"]=surface.label
                pages[side]["physical"]={
                    "widthIn":float(surface.print_width_in),
                    "heightIn":float(surface.print_height_in),"unit":"in",
                }
            master=_master(idx,pages,label)
            if master["compositionSignature"] in unique:
                raise CommandError("Duplicate template artwork: %03d"%(idx+1))
            unique.add(master["compositionSignature"])
            # Render from the same editorial objects used by the live editor.
            png=_mockup(pages[0],pages[1] if len(pages)>1 else None,edition_for(idx))
            name="ZV Door Hanger %03d · %s · %s"%(idx+1,THEMES[idx%20][0],EDITIONS[edition_for(idx)])
            built.append((idx,name,master,png))
        self.stdout.write(self.style.SUCCESS(
            "Validated 100 complete photo-led door-hanger templates; "
            "%d configured pages; source IDs preserved."%side_count
        ))
        if opts["dry_run"]:
            self.stdout.write("Dry run only; no database changes or photo downloads.")
            return
        backup=Path(settings.BASE_DIR)/"template_backups"
        backup.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        destination=backup/("doorhanger-%d-before-v7-%s.jsonl.gz"%(product.pk,stamp))
        with gzip.open(destination,"wt",encoding="utf-8") as out:
            for t in existing:
                out.write(json.dumps({
                    "pk":t.pk,"product_id":t.product_id,"name":t.name,
                    "json_data":t.json_data,
                    "preview":t.preview.name if t.preview else "",
                    "is_active":t.is_active,
                },ensure_ascii=False,default=str)+"\n")
        references=set(SavedDesign.objects.filter(
            source_template_id__in=[t.pk for t in known.values()]
        ).values_list("source_template_id",flat=True))
        with transaction.atomic():
            for idx,name,data,png in built:
                previous=known.get(idx)
                if previous is not None and previous.pk in references:
                    # Keep the original source unchanged for an existing saved
                    # design, but retire it from the public template gallery.
                    previous.is_active=False
                    previous.save(update_fields=["is_active"])
                    t=DesignTemplate(product=product)
                else:
                    t=previous or DesignTemplate(product=product)
                t.name=name
                t.json_data=data
                t.is_active=True
                # Content-addressed filenames prevent repeated preview
                # suffixes after a safe rerun. Never delete old media before
                # the transaction commits: customer references may depend on it.
                filename="doorhanger-photo-v7-%d-%03d-%s.png"%(
                    product.pk,idx+1,hashlib.sha256(png).hexdigest()[:16]
                )
                storage_name="template_previews/"+filename
                if t.preview.storage.exists(storage_name):
                    t.preview.name=storage_name
                else:
                    t.preview.save(filename,ContentFile(png),save=False)
                t.save()
        self.stdout.write(self.style.SUCCESS(
            "Installed 100 photo-rich front/back templates and full gallery "
            "mockups; unreferenced template IDs reused, saved-design sources archived; backup: %s"%destination
        ))
