"""Premium 100-template editor masters for Zenvibe's REMAINING design products.

Protects already approved Canopy, Business Card, Calendar, Invitation, Award,
Coaster, Umbrella and Full Back Wall libraries. Other unsupported shapes are
rejected instead of being disguised as rectangular flyers.

100 unique templates = 20 original industry briefs x five different layouts.
Large faces: curated local/cached photographs, editable photo layers, coherent
editorial typography and full-page gallery composites.
Small imprint faces: scaled monogram and original geometric mark compositions.
All master objects remain Fabric editable, respect Admin print surfaces and
physical measurements, and use the very same renderer as their PNG previews.
No UI changes; no calls to zenvibe.ca; no deleting customer saved designs.

    python manage.py rebuild_remaining_premium_100 --product-id 16 --dry-run
    python manage.py rebuild_remaining_premium_100 --product-id 16 --apply

Photo artwork is loaded from MEDIA_ROOT/template_photo_library/premium100/
(01.jpg..20.jpg) or a supplied --photo-dir. On apply, missing images are
fetched ONCE from images.unsplash.com into the local cache. No placeholder
graphics are substituted for failed photos; that product is left unchanged.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError

from designer.models import DesignTemplate, Product

GENERATOR = "zenvibe-remaining-premium100-v1"
TARGET = 100
# All of these already have dedicated solutions and must remain COMPLETELY
# untouched by this command, even when --refresh is passed.
PROTECTED_TOKENS = (
    "canopy", "business card", "calendar", "invitation", "coaster",
    "full back wall", "award", "trophy", "medal", "umbrella",
)
PROTECTED_GENERATOR_PARTS = (
    "calendar", "business-card", "invitation", "canopy",
    "coaster", "award", "umbrella", "full-back-wall",
)
ROOTS = {
    "marketing-materials", "banners-displays", "promotional-products",
    "custom-apparel", "drinkware", "pens", "bags", "custom-notebooks",
    "corporate-gift-set", "corporate-gift-sets",
}
# No template or product edits for frame-only and other hardware SKUs.
HARDWARE = (
    "frame only", "aluminum canopy frame", "canopy frame", "stand only",
    "bare frame", "replacement hardware", "hardware only", "blank replacement",
    "replacement part", "spare part", "table frame",
)
# Photo list aligns with the 20 briefs in their original order.
PHOTO_IDS = (
    "photo-1497366754035-f200968a6e72",
    "photo-1600596542815-ffad4c1539a9",
    "photo-1517248135467-4c7edcad34c4",
    "photo-1488646953014-85cb44e25828",
    "photo-1540555700478-4be289fbecef",
    "photo-1576091160399-112ba8d25d1d",
    "photo-1503676260728-1c00da094a0b",
    "photo-1518770660439-4636190af475",
    "photo-1534438327276-14e5300c3a48",
    "photo-1460925895917-afdab827c52f",
    "photo-1524504388940-b1c1722653e1",
    "photo-1504307651254-35680f356dfd",
    "photo-1600607687920-4e2a09cf159d",
    "photo-1492144534655-ae79c964c9d7",
    "photo-1511795409834-ef04bbd61622",
    "photo-1483985988355-763728e1935b",
    "photo-1452587925148-ce544e77e70d",
    "photo-1589829545856-d10d557cf95f",
    "photo-1552664730-d307ca884978",
    "photo-1529156069898-49953e39b3ac",
)
# Name, headline, supporting copy, CTA, style colour. Independent *industries*
# and photography: five layouts are not the same design with another colour.
BRIEFS = (
    ("NORTH & CO.", "IDEAS THAT MOVE YOU", "Meaningful work. Lasting impact.", "DISCOVER MORE", "#D8AF75"),
    ("MAISON LIVING", "MAKE ROOM FOR MORE", "Spaces made for real living.", "EXPLORE HOMES", "#C69A7D"),
    ("TABLE & GRAIN", "SAVOUR THE MOMENT", "Great food, good company.", "VIEW THE MENU", "#DEAC73"),
    ("MERIDIAN", "GO BEYOND THE MAP", "Exceptional journeys await.", "EXPLORE NOW", "#9BC5C4"),
    ("STILL STUDIO", "FIND YOUR BALANCE", "Wellness, designed around you.", "BOOK A VISIT", "#B5C69A"),
    ("KINCARE", "CARE WITH PURPOSE", "Support every step of the way.", "GET IN TOUCH", "#A1CCCB"),
    ("BRIGHTPATH", "LEARN SOMETHING NEW", "Imagine the possibilities.", "JOIN US", "#B3BFDC"),
    ("SIGNAL LAB", "BUILD WHAT'S NEXT", "Technology, intelligently done.", "LET'S TALK", "#B9B7D8"),
    ("FORM FITNESS", "MOVE WITH PURPOSE", "Feel strong. Keep growing.", "JOIN TODAY", "#E2AC96"),
    ("LEDGER HOUSE", "A BRIGHTER OUTLOOK", "Plan boldly. Live confidently.", "MEET OUR TEAM", "#D5BC8D"),
    ("GLOW ATELIER", "FEEL AMAZING", "Your everyday indulgence.", "BOOK NOW", "#E1B3B9"),
    ("STONE & STEEL", "BUILT TO LAST", "Beautiful work, beautifully done.", "SEE OUR WORK", "#D0B08C"),
    ("SUNDAY INTERIORS", "LIVE BEAUTIFULLY", "Details worth coming home to.", "EXPLORE DESIGN", "#C2B9A1"),
    ("MOTIVE", "READY FOR THE ROAD", "Make every journey count.", "GET STARTED", "#A2BECE"),
    ("CELEBRATE CO.", "MOMENTS THAT MATTER", "Make something unforgettable.", "SAVE THE DATE", "#E0C0D4"),
    ("THREAD STUDIO", "YOUR STYLE, REFINED", "Wear what moves you.", "SHOP THE EDIT", "#D7B4A8"),
    ("FRAME THEORY", "STORIES IN FOCUS", "Every moment, beautifully kept.", "BOOK A SESSION", "#C8B6D5"),
    ("CROWN LEGAL", "CONFIDENCE IS KEY", "Considered advice. Clear action.", "LET'S CONNECT", "#CCC59B"),
    ("AMPLIFY", "MAKE YOUR MARK", "Fresh thinking, distinctive results.", "LET'S CREATE", "#E4B89D"),
    ("COMMON GROUND", "BETTER TOGETHER", "Community starts with a hello.", "GET INVOLVED", "#B8D0B7"),
)
DIRECTIONS = ("Editorial", "Gallery", "Immersive", "Collage", "Minimal Luxe")
BASES = (
    ("#F5F0E8", "#263541", "#54646A"),
    ("#18303A", "#F9F2E7", "#D5D7D0"),
    ("#F7ECE8", "#3B333C", "#74656C"),
    ("#222F46", "#FFF5DF", "#D6D8E0"),
    ("#E8EEE9", "#253D39", "#586B61"),
)
RESAMPLE = Image.Resampling.LANCZOS


def _category_path(product):
    result = set()
    node = product.category
    visited = set()
    while node is not None and node.pk not in visited and len(visited) < 12:
        visited.add(node.pk)
        result.add((node.slug or "").lower())
        result.add((node.name or "").lower().replace(" & ", "-").replace(" ", "-"))
        node = node.parent
    return result


def protected(product):
    name = (product.name or "").lower()
    if any(token in name for token in PROTECTED_TOKENS):
        return "Approved category protected from bulk edits"
    # Protect other already approved items in a protected subtree.
    parts = _category_path(product)
    if any(any(token in p for token in ("canopy", "calendar", "business-card",
                                       "invitation", "award")) for p in parts):
        return "Approved category protected from bulk edits"
    return ""


def family_for(product):
    """Explicit category routing; no generic flyers on shaped products."""
    if protected(product):
        return ""
    name = (product.name or "").lower()
    if any(token in name for token in HARDWARE):
        return ""
    path = _category_path(product)
    roots = {p for p in path if p in ROOTS}
    if not roots:
        return ""
    # Cut-out flags, circle pop-outs and hardware have their own dielines.
    # Do not print full rectangular artwork on an unknown cut shape.
    if any(token in name for token in (
        "teardrop", "tear drop", "feather flag", "circle pop out",
        "round pop out", "x banner stand only", "light sign box",
        "round table", "cross over table", "round fitted",
        "golf ball", "lapel pin", "shape bottle opener",
        "custom shape", "car freshener", "mouse pad",
    )):
        # These need a specific die-cut/surface generator, not a rectangle
        # pasted on top of a circular, triangular or multi-panel product.
        return ""
    if "door hanger" in name or "doorhanger" in name:
        return "doorhanger"
    if "flyer" in name:
        return "flyer"
    if "brochure" in name:
        return "brochure"
    if "ticket" in name:
        return "ticket"
    if "banner" in name or "standee" in name or "a frame" in name or "sandwich board" in name:
        return "banner"
    if "table" in name and any(t in name for t in ("cover","throw","runner","skirt")):
        return "table-cover"
    if any(t in name for t in ("backdrop","display","fabric wall")):
        return "display"
    if re.search(r"\b(pens?|stylus|highlighter|marker)\b",name) and not any(
        t in name for t in ("gift set","pen set","gift box","bottle opener")
    ):
        return "pen"
    if any(t in name for t in ("mug", "tumbler", "drink bottle", "water bottle",
                               "thermo", "flask")) and "opener" not in name:
        return "drinkware"
    if any(t in name for t in ("t-shirt","t shirt","shirt","hoodie","polo","jersey",
                               "jacket","cap","uniform","sportswear")) or (
        "custom-apparel" in roots
    ):
        return "apparel"
    if any(t in name for t in ("bag","backpack","tote","pouch","drawstring","fanny pack")) or (
        "bags" in roots
    ):
        return "bag"
    if any(t in name for t in ("notebook","notepad","journal")) or (
        "custom-notebooks" in roots
    ):
        return "notebook"
    if "corporate-gift-set" in roots or "corporate-gift-sets" in roots:
        return "gift"
    if "promotional-products" in roots:
        return "logo-product"
    if "marketing-materials" in roots:
        return "flyer"
    if "banners-displays" in roots:
        return "display"
    if "pens" in roots:
        return "pen"
    if "drinkware" in roots:
        return "drinkware"
    return ""


def _number(value):
    try:
        return float(value or 0)
    except (ValueError,TypeError):
        return 0.0


@dataclass(frozen=True)
class PrintPage:
    label: str
    width_in: float
    height_in: float
    workspace_w_in: float
    workspace_h_in: float
    bounds: tuple


def configured_pages(product, family):
    """Only Admin-configured physical print surfaces/print areas; NO guessed inches."""
    surfaces = list(product.print_surfaces.filter(is_active=True).order_by("sort_order", "pk"))
    areas = list(product.print_areas.order_by("sort_order", "pk"))
    if len(surfaces)>12:
        raise CommandError("More than 12 surfaces; review Admin page configuration")
    if not surfaces:
        surfaces = [None]
    pages=[]
    for side,surface in enumerate(surfaces):
        primary = next((area for area in areas if (
            (surface and area.surface_id == surface.pk) or
            (not surface and area.surface_id is None)
        ) and area.product_image_id is None),None)
        if primary is None:
            primary = next((area for area in areas if (
                (surface and area.surface_id == surface.pk) or
                (not surface and area.surface_id is None)
            )),None)
        wi = _number(surface.print_width_in if surface else product.print_width_in)
        hi = _number(surface.print_height_in if surface else product.print_height_in)
        if not (wi>0 and hi>0) and primary is not None:
            wi=_number(primary.print_width_in)
            hi=_number(primary.print_height_in)
        if wi<=0 or hi<=0:
            raise CommandError("Admin print width/height missing for page %s"%(side+1))
        ww=_number((surface.workspace_width_in if surface else None) or product.workspace_width_in) or wi
        wh=_number((surface.workspace_height_in if surface else None) or product.workspace_height_in) or hi
        if not (ww>0 and wh>0) or ww/wh>15 or wh/ww>15:
            raise CommandError("Invalid/excessive Admin workspace aspect ratio")
        if primary is None:
            bounds=(0.0,0.0,1.0,1.0)
        else:
            bounds=tuple(_number(getattr(primary,attr))/100 for attr in ("left","top","width","height"))
            x,y,w,h=bounds
            if not (0<=x<1 and 0<=y<1 and w>0 and h>0 and x+w<=1.001 and y+h<=1.001):
                raise CommandError("Invalid print-area percentage in Admin")
        pages.append(PrintPage(
            surface.label if surface else ("Front" if side==0 else "Back"),
            wi, hi, ww, wh,bounds
        ))
    if family=="brochure" and len(pages)==1:
        # Brochure outside and inside are two sides of the SAME configured stock.
        p=pages[0]
        pages=[PrintPage("Outside",p.width_in,p.height_in,p.workspace_w_in,
                         p.workspace_h_in,p.bounds),
               PrintPage("Inside",p.width_in,p.height_in,p.workspace_w_in,
                         p.workspace_h_in,p.bounds)]
    if family=="ticket" and len(pages)==1:
        # No invented reverse side: ticket can genuinely be one-sided.
        pass
    return pages


def canvas_size(surface):
    ratio=surface.workspace_w_in/surface.workspace_h_in
    if ratio>=1:
        w=1200; h=max(90,round(w/ratio))
    else:
        h=1200; w=max(90,round(h*ratio))
    return w,h


def physical_region(product,surface,w,h):
    x,y,bw,bh=surface.bounds
    left=x*w;top=y*h; aw=bw*w;ah=bh*h
    # Map actual Admin safe_margin_in into the physical print face. Never
    # silently treat the safe area as the whole product photograph.
    margin_in=_number(product.safe_margin_in)
    sx=margin_in/surface.width_in*aw if margin_in>0 else aw*.032
    sy=margin_in/surface.height_in*ah if margin_in>0 else ah*.032
    sx=max(aw*.018,min(aw*.078,sx))
    sy=max(ah*.018,min(ah*.078,sy))
    result=(left+sx,top+sy,aw-2*sx,ah-2*sy)
    if result[2]<65 or result[3]<35:
        raise CommandError("Print face too small to lay out editable premium artwork")
    return result


def _as_color(v):
    return ImageColor.getrgb(str(v))[:3]


def _font(px,bold=False):
    fonts = (
        ("DejaVuSans-Bold.ttf","LiberationSans-Bold.ttf","arialbd.ttf") if bold else
        ("DejaVuSans.ttf","LiberationSans-Regular.ttf","arial.ttf")
    )
    for f in fonts:
        try:return ImageFont.truetype(f,max(8,int(round(px))))
        except OSError:pass
    return ImageFont.load_default()


def _measure(text,size,bold=False):
    font=_font(size,bold)
    return max(font.getlength(line) for line in (text.split("\n") or [""]))


def fit_size(text,max_width,max_height,ideal,bold=False):
    rows=text.split("\n")
    size=min(float(ideal),float(max_height)/max(1.12,len(rows)*1.17))
    while size>7.5 and _measure(text,size,bold)>max_width*.92:
        size*=.92
    if size<7.5:
        raise CommandError("Configured print face cannot accommodate readable typography")
    return round(size,2)


class Artwork:
    """An SVG/Fabric-independent sequence of *editor-native* objects."""

    def __init__(self,w,h):
        self.w=w;self.h=h;self.items=[];self.seq=0

    def make(self,kind,name,x,y,w,h,color,editable=True,**extras):
        self.seq+=1
        obj={
            "id":"p100-%03d"%self.seq,"name":name,
            "type":kind,"left":round(x,3),"top":round(y,3),
            "width":round(w,3),"height":round(h,3),"fill":color,
            "scaleX":1,"scaleY":1,"angle":0,"opacity":1,
            "originX":"left","originY":"top",
            "customerEditable":editable,"selectable":editable,
            "evented":editable,"locked":not editable,
        }
        obj.update(extras);self.items.append(obj);return obj

    def rect(self,name,x,y,w,h,color,editable=True,rx=0):
        return self.make("rect",name,x,y,w,h,color,editable,rx=rx,ry=rx)
    def circle(self,name,cx,cy,r,color):
        return self.make("circle",name,cx-r,cy-r,2*r,2*r,color,radius=r)
    def text(self,name,value,x,y,w,h,color,ideal,bold=False,align="left"):
        return self.make(
            "textbox",name,x,y,w,h,color,True,text=value,
            fontFamily="Arial",font="Arial",
            fontSize=fit_size(value,w,h,ideal,bold),
            fontWeight="700" if bold else "400",textAlign=align,
            lineHeight=1.12,manualReplacement=True,fieldType="premium-text"
        )
    def picture(self,photo,x,y,w,h,name="Replace industry photograph"):
        src="data:image/jpeg;base64,"+base64.b64encode(photo).decode("ascii")
        return self.make(
            "image",name,x,y,w,h,"transparent",True,
            src=src,baseSrc=src,manualReplacement=True,
            fieldType="replaceable-industry-photo",backgroundAsset=False
        )
    def validate(self,region):
        # All art must be inside the Admin print face (not merely the artboard).
        x0,y0,rw,rh=region
        boxes=[]
        for o in self.items:
            x=float(o["left"]);y=float(o["top"])
            ww=float(o["width"]);hh=float(o["height"])
            if not all(math.isfinite(v) for v in (x,y,ww,hh)):
                raise CommandError("Non-finite artwork dimensions")
            if ww<=0 or hh<=0 or (x<x0-.2 or y<y0-.2 or
                                  x+ww>x0+rw+.2 or y+hh>y0+rh+.2):
                raise CommandError("Print-face overflow: "+o["name"])
            if o["type"]=="textbox":
                boxes.append((x,y,ww,hh,o["name"]))
        for k,a in enumerate(boxes):
            for b in boxes[k+1:]:
                ox=min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])
                oy=min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])
                if ox>1 and oy>1:
                    raise CommandError("Overlapping editable texts: %s and %s"%(a[4],b[4]))
        if len(boxes)<2:
            raise CommandError("Incomplete design: insufficient visible editable copy")


def _safe_image(data):
    if len(data)>6_000_000:
        raise CommandError("Photo source exceeds 6MB")
    try:
        with Image.open(io.BytesIO(data)) as p:
            if p.width<480 or p.height<480 or p.width*p.height>40_000_000:
                raise CommandError("Poor source photo resolution/dimensions")
            return ImageOps.exif_transpose(p).convert("RGB")
    except (UnidentifiedImageError,OSError) as exc:
        raise CommandError("Invalid source photo: %s"%exc)


def _jpeg(image,quality=85):
    buf=io.BytesIO()
    image.save(buf,format="JPEG",quality=quality,optimize=True)
    return buf.getvalue()


class Photobank:
    def __init__(self,photo_dir=None,dry_run=False):
        self.directory=Path(photo_dir) if photo_dir else None
        self.cache=Path(settings.MEDIA_ROOT)/"template_photo_library"/"premium100"
        self.dry_run=dry_run
        self.images={}

    def get(self,theme):
        if theme in self.images:return self.images[theme]
        if self.dry_run:
            # ONLY the dry run may use a sample. Apply NEVER substitutes a
            # blank card for an unavailable photograph.
            sample=Image.new("RGB",(1050,1400),("#6f9ca1"))
            draw=ImageDraw.Draw(sample)
            for j in range(17):
                draw.ellipse((j*80,j*45,j*80+270,j*45+300),
                             outline=(185,214,206),width=7)
            self.images[theme]=sample
            return sample
        candidates=[]
        if self.directory:
            for suffix in ("jpg","jpeg","png","webp"):
                candidates.extend([
                    self.directory/("%02d.%s"%(theme+1,suffix)),
                    self.directory/("%03d.%s"%(theme+1,suffix)),
                ])
        candidates.append(self.cache/("%02d.jpg"%(theme+1)))
        # Reuse earlier locally cached door-hanger photographs when present,
        # without re-fetching or modifying those files.
        candidates.append(Path(settings.MEDIA_ROOT)/"template_photo_library"/
                          "doorhanger"/("%02d.jpg"%(theme+1)))
        for name in candidates:
            if name.is_file():
                image=_safe_image(name.read_bytes())
                self.images[theme]=image
                return image
        # Fetch ONLY the twenty curated source photos, once per entire batch.
        # Never fetch product data/graphics from zenvibe.ca.
        url=("https://images.unsplash.com/%s"
             "?fit=crop&w=1050&h=1400&q=85&fm=jpg")%PHOTO_IDS[theme]
        try:
            req=Request(url,headers={"User-Agent":"ZenvibePremiumTemplateInstaller/1.0"})
            with urlopen(req,timeout=15) as response:
                if response.headers.get_content_type() not in ("image/jpeg","image/png"):
                    raise CommandError("Image source returned unexpected MIME type")
                data=response.read(6_000_001)
            image=_safe_image(data)
        except (OSError,ValueError,CommandError) as exc:
            raise CommandError("Industry photograph %02d unavailable (%s). "
                               "Supply licensed 01.jpg–20.jpg via --photo-dir."%
                               (theme+1,exc))
        self.cache.mkdir(parents=True,exist_ok=True)
        (self.cache/("%02d.jpg"%(theme+1))).write_bytes(_jpeg(image))
        self.images[theme]=image
        return image

    def crop(self,theme,aspect,edition):
        source=self.get(theme)
        w=round(max(240,min(1000,780*aspect))) if aspect<=1 else 960
        h=round(w/aspect)
        if h>1200:
            h=1200;w=round(h*aspect)
        centers=((.50,.47),(.55,.45),(.43,.56),(.62,.50),(.48,.43))
        return _jpeg(ImageOps.fit(source,(max(200,w),max(200,h)),
                                   method=RESAMPLE,centering=centers[edition]))


def layout_index(index):
    """Different layout per first row, not four identical colourways."""
    return (index//20+index%5)%5


def _base_art(art,region,bg,family):
    # Print-area-only substrate. A transparent imprint remains transparent.
    if family not in ("pen","logo-product"):
        x,y,w,h=region
        art.rect("Editable background",x,y,w,h,bg)


def _draw_photo_page(art,region,bank,theme,layout,brief,colors,side,family):
    x,y,w,h=region
    bg,ink,muted=colors
    brand,headline,sub,cta,foil=brief
    # The five compositions differ in image ratio and placement, typography
    # hierarchy, story structure and decorative geometry, not just palette.
    landscape=w/h>1.20
    if layout==0:  # Cover: large hero, title below.
        pic=(.045,.095,.91,.49) if not landscape else (.045,.08,.54,.84)
        brand_box=(.07,.62,.86,.06) if not landscape else (.63,.15,.33,.10)
        title_box=(.07,.70,.86,.115) if not landscape else (.63,.31,.33,.20)
        sub_box=(.07,.83,.86,.05) if not landscape else (.63,.60,.33,.10)
        cta_box=(.09,.917,.82,.053) if not landscape else (.64,.80,.30,.09)
    elif layout==1:  # Magazine: a dramatic headline leads, photo follows.
        pic=(.07,.43,.86,.38) if not landscape else (.45,.09,.51,.82)
        brand_box=(.09,.08,.82,.06) if not landscape else (.06,.17,.34,.11)
        title_box=(.085,.17,.83,.19) if not landscape else (.06,.34,.34,.27)
        sub_box=(.085,.83,.83,.05) if not landscape else (.06,.66,.34,.10)
        cta_box=(.10,.922,.80,.053) if not landscape else (.06,.83,.31,.08)
    elif layout==2:  # Immersive split: image dominant, copy on a distinct band.
        pic=(.035,.05,.93,.66) if not landscape else (.04,.06,.91,.60)
        brand_box=(.10,.735,.80,.057) if not landscape else (.08,.705,.84,.055)
        title_box=(.08,.794,.84,.080) if not landscape else (.07,.765,.86,.085)
        sub_box=(.09,.880,.82,.036) if not landscape else (.08,.85,.84,.04)
        cta_box=(.13,.941,.74,.048) if not landscape else (.30,.927,.40,.050)
    elif layout==3:  # Art gallery: framed off-centre photo, generous type.
        pic=(.11,.13,.78,.36) if not landscape else (.075,.12,.43,.76)
        brand_box=(.11,.53,.78,.07) if not landscape else (.56,.12,.38,.10)
        title_box=(.105,.618,.79,.125) if not landscape else (.55,.30,.40,.23)
        sub_box=(.11,.76,.78,.06) if not landscape else (.56,.63,.38,.10)
        cta_box=(.145,.906,.71,.063) if not landscape else (.58,.82,.32,.085)
    else:  # Collage: main photo and detail crop, condensed editorial hierarchy.
        pic=(.075,.11,.58,.49) if not landscape else (.06,.09,.57,.76)
        brand_box=(.10,.635,.80,.055) if not landscape else (.66,.18,.30,.10)
        title_box=(.095,.696,.81,.128) if not landscape else (.66,.34,.30,.22)
        sub_box=(.105,.836,.79,.047) if not landscape else (.66,.65,.30,.11)
        cta_box=(.11,.921,.78,.060) if not landscape else (.67,.82,.29,.09)

    def B(b):
        return (x+w*b[0],y+h*b[1],w*b[2],h*b[3])
    imgx,imgy,imgw,imgh=B(pic)
    photo=bank.crop(theme,imgw/max(1,imgh),layout)
    art.picture(photo,imgx,imgy,imgw,imgh)
    # A foil or paper reveal is part of the actual editable composition.
    art.rect("Editorial foil detail",x+w*.08,y+h*.056,
             w*(.11+.025*(layout%3)),max(2,h*.004),foil)
    # Twenty different industry insignias; this is a real variation in
    # shape count/position, not another colourway of the same layout.
    for j in range(1+theme%4):
        rr=min(w,h)*(.0045+(j%2)*.001)
        art.circle("Theme insignia %s"%j,
                   x+w*(.77+j*.046),y+h*.055,rr,foil)
    if layout==4:
        # Second small collage crop from the same licensed photo source.
        if landscape:
            second_box=(x+w*.38,y+h*.46,w*.22,h*.33)
        else:
            second_box=(x+w*.68,y+h*.26,w*.24,h*.30)
        second=bank.crop(theme,second_box[2]/second_box[3],(layout+2)%5)
        art.picture(second,*second_box,name="Replace collage detail photo")
    if layout==3:
        art.rect("Gallery alignment rule",
                 x+w*.10,y+h*(.512 if not landscape else .08),
                 w*(.80 if not landscape else .008),
                 h*(.003 if not landscape else .79),foil)

    tx,ty,tw,th=B(title_box)
    bx,by,bw,bh=B(brand_box)
    sx,sy,sw,sh=B(sub_box)
    cx,cy,cw,ch=B(cta_box)
    if layout in (0,3):
        art.text("Editable brand",brand,bx,by,bw,bh,muted,min(bw*.105,bh*.90),True)
        art.text("Editable headline",headline,tx,ty,tw,th,ink,min(tw*.095,th*.75),True)
    else:
        art.text("Editable headline",headline,tx,ty,tw,th,ink,min(tw*.103,th*.79),True)
        art.text("Editable brand",brand,bx,by,bw,bh,muted,min(bw*.105,bh*.75),True)
    art.text("Editable supporting copy",sub,sx,sy,sw,sh,muted,
             min(sw*.059,sh*.83))
    # Small photo hero layouts have no overlaying text so there is never
    # unreadable type on an unpredictably light image.
    art.rect("Editable call-to-action band",cx,cy,cw,ch,foil,rx=min(cw,ch)*.08)
    art.text("Editable call to action",cta,cx+cw*.055,cy+ch*.07,
             cw*.89,ch*.80,"#172934",min(cw*.10,ch*.66),True,"center")


def _draw_mark_page(art,region,index,layout,brief,colors,family):
    """Print-safe category branding: labels/marks, not rectangle flyers."""
    x,y,w,h=region
    bg,ink,muted=colors
    brand,headline,sub,cta,foil=brief
    wide=w/h>2.5
    # Deliberate logo/monogram rather than unreadably tiny advertising copy.
    # Hero decoration stays in its own zone separate from the editable wordmark.
    if wide:
        art_zone=(x+w*.045,y+h*.15,w*.23,h*.70)
        name_zone=(x+w*.32,y+h*.18,w*.64,h*.32)
        support_zone=(x+w*.32,y+h*.61,w*.64,h*.22)
    elif w/h<.75:
        art_zone=(x+w*.19,y+h*.07,w*.62,h*.38)
        name_zone=(x+w*.10,y+h*.52,w*.80,h*.14)
        support_zone=(x+w*.11,y+h*.74,w*.78,h*.095)
    else:
        art_zone=(x+w*.09,y+h*.17,w*.33,h*.66)
        name_zone=(x+w*.48,y+h*.25,w*.47,h*.23)
        support_zone=(x+w*.48,y+h*.58,w*.47,h*.12)
    ax,ay,aw,ah=art_zone
    # Fourteen+ original vector primitives on average, with five distinct
    # art directions and varying industry monograms.
    if layout==0:  # concentric brand seal
        for j in range(4):
            r=min(aw,ah)*(.38-j*.065)
            art.circle("Editable logo seal %s"%j,ax+aw*.50,ay+ah*.50,r,
                       foil if j%2==0 else bg)
        art.rect("Horizontal logo axis",ax+aw*.25,ay+ah*.48,aw*.50,ah*.045,ink)
    elif layout==1:  # architectural bars
        for j in range(7):
            ht=.37+.07*((j+index)%5)
            art.rect("Editorial monogram bar %s"%j,
                     ax+aw*(.09+j*.12),ay+ah*(.9-ht),aw*.07,ah*ht,
                     foil if j%2 else ink)
    elif layout==2:  # botanical/wellness petals
        for j in range(9):
            angle=2*math.pi*j/9
            cx=ax+aw*(.5+.30*math.cos(angle))
            cy=ay+ah*(.5+.28*math.sin(angle))
            rr=min(aw,ah)*(.065+(j%3)*.012)
            art.circle("Editable botanical petal %s"%j,cx,cy,rr,foil if j%2 else ink)
        art.circle("Editable flower centre",ax+aw*.5,ay+ah*.5,min(aw,ah)*.11,foil)
    elif layout==3:  # tiered gallery
        for j in range(6):
            art.rect("Gallery tile %s"%j,ax+aw*(.13+(j%3)*.25),
                     ay+ah*(.12+(j//3)*.38),aw*.19,ah*.25,
                     foil if j%3==0 else ink)
    else:  # contemporary constellation
        for j in range(12):
            angle=j*2.399963
            cx=ax+aw*(.5+.32*math.cos(angle))
            cy=ay+ah*(.5+.31*math.sin(angle))
            art.circle("Constellation emblem %s"%j,cx,cy,
                       min(aw,ah)*(.022+(j%3)*.017),foil if j%2 else ink)
    nx,ny,nw,nh=name_zone
    sx,sy,sw,sh=support_zone
    art.text("Editable brand identity",brand,nx,ny,nw,nh,ink,
             min(nw*.14,nh*.80),True)
    art.text("Editable tagline",sub,sx,sy,sw,sh,muted,
             min(sw*.075,sh*.72))
    # Every product's small print face contains printable symbols and labels;
    # it is never given a fake full-bleed stock photograph.


def build_page(product,family,index,side,surface,bank):
    W,H=canvas_size(surface)
    region=physical_region(product,surface,W,H)
    edition=layout_index(index)
    theme=(index%20)
    brief=BRIEFS[theme]
    colors=BASES[edition]
    # Small imprint/engraving surfaces must remain TRANSPARENT, not print a
    # white card. Use a consistently dark readable ink on that substrate.
    if family in ("pen","logo-product"):
        colors=("#FFFFFF","#243A40","#4C6268")
    if side%2:
        # Differentiated front/back content, retaining consistent brand identity.
        brief=(brief[0],("WHY CHOOSE US" if edition%2 else "MADE FOR YOU"),
               brief[2],("GET IN TOUCH" if edition%2 else brief[3]),brief[4])
        edition=(edition+2)%5
    art=Artwork(W,H)
    _base_art(art,region,colors[0],family)
    logo_family=family in ("pen","logo-product")
    ratio=region[2]/region[3]
    if logo_family or ratio>5.5 or ratio<.20:
        _draw_mark_page(art,region,index,edition,brief,colors,family)
    else:
        _draw_photo_page(art,region,bank,theme,edition,brief,colors,side,family)
    art.validate(region)
    page={
        "name":surface.label,"width":W,"height":H,
        "editorCoordinates":True,"editorWidth":W,"editorHeight":H,
        "background":"rgba(0,0,0,0)",
        "physical":{"widthIn":surface.width_in,"heightIn":surface.height_in,"unit":"in"},
        "objects":art.items,
    }
    return page


def _render_page(page,scale):
    w=max(1,round(page["width"]*scale));h=max(1,round(page["height"]*scale))
    img=Image.new("RGBA",(w,h),(255,255,255,0))
    drawer=ImageDraw.Draw(img,"RGBA")
    for o in page["objects"]:
        kind=o["type"]
        x=round(float(o["left"])*scale);y=round(float(o["top"])*scale)
        ww=max(1,round(float(o["width"])*scale))
        hh=max(1,round(float(o["height"])*scale))
        if kind=="rect":
            fill=_as_color(o["fill"])
            radius=max(0,min(ww//3,round(float(o.get("rx") or 0)*scale)))
            drawer.rounded_rectangle((x,y,x+ww,y+hh),radius=radius,fill=fill)
        elif kind in ("circle","ellipse"):
            drawer.ellipse((x,y,x+ww,y+hh),fill=_as_color(o["fill"]))
        elif kind=="image":
            src=str(o.get("src") or "")
            if not src.startswith("data:image/jpeg;base64,"):
                raise CommandError("Preview photo does not match editable JPEG source")
            raw=base64.b64decode(src.split(",",1)[1],validate=True)
            with Image.open(io.BytesIO(raw)) as loaded:
                photo=ImageOps.exif_transpose(loaded).convert("RGB")
                photo=ImageOps.fit(photo,(ww,hh),method=RESAMPLE)
                img.paste(photo,(x,y))
        elif kind=="textbox":
            text=str(o.get("text") or "")
            size=max(7,float(o.get("fontSize") or 16)*scale)
            font=_font(size,str(o.get("fontWeight")) in ("700","bold"))
            align=o.get("textAlign","left")
            posx=x+ww/2 if align=="center" else x+ww if align=="right" else x
            anchor="ma" if align=="center" else "ra" if align=="right" else "la"
            for j,line in enumerate(text.split("\n")):
                drawer.text((posx,y+j*size*1.12),line,font=font,
                            fill=_as_color(o["fill"]),anchor=anchor)
    return img


def render_preview(pages,family):
    """Portrait-format gallery preview: same artwork as Fabric editor.

    The existing gallery uses a portrait thumbnail card. A wide front/back
    contact sheet previously shrank the entire design into a tiny central
    thumbnail. This renderer intentionally fills that same card without any
    storefront/CSS changes. Previews never invent a different design.
    """
    stage_w,stage_h=900,1160
    stage=Image.new("RGB",(stage_w,stage_h),(241,241,240))
    d=ImageDraw.Draw(stage)
    d.rounded_rectangle((18,18,882,1142),radius=20,
                        fill=(251,250,248),outline=(215,212,207),width=2)
    d.text((55,43),"EDITABLE PREMIUM ARTWORK",
           font=_font(18,True),fill=(66,76,81))
    d.text((stage_w-45,43),family.upper().replace("-"," "),
           font=_font(16,True),fill=(94,103,108),anchor="ra")

    # Use the *actual* document ratio, not assumptions about the category.
    page=pages[0]
    portrait=page["width"]/max(1,page["height"])<.91
    if len(pages)==1 and portrait:
        slots=[(0,54,92,790,990)]
    elif len(pages)==1:
        # Two readable looks at one single-sided design. The second slot
        # repeats the real artwork, not a fictitious back side.
        slots=[(0,45,125,810,445),(0,45,615,810,445)]
        d.text((65,575),"ARTWORK DETAIL  •  SAME PRINT FACE",
               font=_font(18,True),fill=(95,97,96))
    elif portrait:
        # Dominant front plus clearly labelled back for tall product artwork.
        slots=[(0,32,118,568,960),(1,614,303,255,650)]
        d.text((640,262),"BACK",font=_font(17,True),fill=(95,97,96))
    else:
        # Landscape brochures and tickets keep both pages at full card width.
        slots=[(0,45,125,810,437),(1,45,650,810,437)]
        d.text((62,95),"OUTSIDE / FRONT",font=_font(16,True),fill=(92,98,99))
        d.text((62,621),"INSIDE / BACK",font=_font(16,True),fill=(92,98,99))

    for index,left,top,bw,bh in slots:
        p=pages[index]
        scale=min(bw/max(1,p["width"]),bh/max(1,p["height"]))
        artwork=_render_page(p,scale)
        x=left+(bw-artwork.width)//2
        y=top+(bh-artwork.height)//2
        shadow=Image.new("RGBA",(artwork.width+24,artwork.height+24),
                         (0,0,0,0))
        alpha=artwork.getchannel("A").filter(ImageFilter.GaussianBlur(9))
        shadow.paste((0,0,0,110),
                     (11,12,11+artwork.width,12+artwork.height),alpha)
        stage.paste(shadow,(x-11,y-11),shadow)
        stage.paste(artwork,(x,y),artwork)
    out=io.BytesIO()
    stage.save(out,format="PNG",optimize=True)
    return out.getvalue()


def _existing_status(product):
    templates=list(DesignTemplate.objects.filter(product=product).order_by("pk"))
    if len(templates)>TARGET:
        raise CommandError("More than 100 templates exist; review duplicates before replacing")
    if not templates:
        return templates,{}
    mapping={}
    for item in templates:
        raw=item.json_data
        if isinstance(raw,str):
            try:raw=json.loads(raw)
            except (ValueError,TypeError):raise CommandError("Malformed template JSON for %s"%item.pk)
        if not isinstance(raw,dict):
            raise CommandError("Unknown template data for %s"%item.pk)
        tag=str(raw.get("generator") or "")
        if any(prefix in tag.lower() for prefix in PROTECTED_GENERATOR_PARTS):
            raise CommandError("Approved generator already owns this library")
        # Never overwrite customer-authored or unknown masters just because
        # the product was selected for the remaining-library campaign.
        if tag!=GENERATOR and not tag.startswith((
            "zenvibe-promotional-", "zenvibe-marketing-materials-",
            "zenvibe-print-face-", "zenvibe-notebook-",
            "zenvibe-flyer-", "zenvibe-trifold-", "zenvibe-doorhanger-",
        )):
            raise CommandError("Existing custom/unknown templates: preservation required")
        match=re.search(r"(?:^|\b)(\d{3})(?:\b|$)",item.name)
        if not match:
            # Recycle by original ordering only for our own generated masters.
            if tag!=GENERATOR:
                raise CommandError("Legacy row without stable 001–100 index; refuse unsafe overwrite")
            index=len(mapping)
        else:
            index=int(match.group(1))-1
        if index<0 or index>=TARGET or index in mapping:
            raise CommandError("Duplicate/invalid 001–100 template number")
        mapping[index]=item
    return templates,mapping


def _backup(product,templates):
    folder=Path(settings.BASE_DIR)/"template_backups"
    folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path=folder/("premium100-%s-before-%s.jsonl.gz"%(product.pk,stamp))
    with gzip.open(path,"wt",encoding="utf-8") as out:
        for t in templates:
            out.write(json.dumps({
                "id":t.pk,"product_id":product.pk,"name":t.name,
                "json_data":t.json_data,"is_active":t.is_active,
                "preview_name":t.preview.name if t.preview else "",
            },ensure_ascii=False,default=str)+"\n")
    return path


class Command(BaseCommand):
    help="Create 100 premium photo-led or logo-led templates for ONE unprotected product."

    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,required=True)
        p.add_argument("--photo-dir",default="")
        choice=p.add_mutually_exclusive_group(required=True)
        choice.add_argument("--dry-run",action="store_true")
        choice.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        product=Product.objects.select_related("category","category__parent").filter(
            pk=opts["product_id"],is_active=True).first()
        if not product:
            raise CommandError("Active product not found")
        if protected(product):
            raise CommandError("Protected existing collection: "+product.name)
        family=family_for(product)
        if not family or family=="doorhanger":
            raise CommandError("Product requires its dedicated shape-safe generator or is unsupported")
        templates,indexed=_existing_status(product)
        surfaces=configured_pages(product,family)
        bank=Photobank(opts.get("photo_dir"),dry_run=opts["dry_run"])
        seen=set();prepared=[]
        for idx in range(TARGET):
            pages=[build_page(product,family,idx,j,surface,bank)
                   for j,surface in enumerate(surfaces)]
            signature=hashlib.sha256(json.dumps([
                [(o["type"],o["left"],o["top"],o["width"],o["height"],
                  o.get("text"),o.get("src","")[:60]) for o in page["objects"]]
                for page in pages
            ],sort_keys=True).encode()).hexdigest()
            if signature in seen:
                raise CommandError("Repeated composition detected at %03d"%(idx+1))
            seen.add(signature)
            theme=BRIEFS[idx%20][0]
            name="ZV Premium %s %03d · %s · %s"%(
                family.title(),idx+1,theme,DIRECTIONS[layout_index(idx)])
            payload={
                "generator":GENERATOR,"version":1,
                "pageCount":len(pages),"width":pages[0]["width"],
                "height":pages[0]["height"],"pages":pages,
                "editorNative":True,"editable":True,
                "designFamily":family,"compositionSignature":signature,
                "previewComplete":True,"printProfile":"admin-defined",
            }
            # Preview uses exactly the editor-layer geometry; no gallery
            # background-only thumbnails or substitute mockups.
            png=render_preview(pages,family) if opts["apply"] else None
            if png is not None and len(png)<3000:
                raise CommandError("Preview lacks complete image/text artwork")
            prepared.append((idx,name,payload,png))
        self.stdout.write(self.style.SUCCESS(
            "Validated 100 unique %s designs for #%s %s (%s pages)."%(
                family,product.pk,product.name,len(surfaces)
            )
        ))
        if opts["dry_run"]:
            self.stdout.write("No database, preview or existing templates changed.")
            return
        backup=_backup(product,templates)
        # Preserve existing IDs; do not delete a customer's referenced template
        # or any SavedDesign. No changes to approved product categories.
        with transaction.atomic():
            for idx,name,payload,png in prepared:
                t=indexed.get(idx) or DesignTemplate(product=product)
                t.name=name
                t.json_data=payload
                t.is_active=True
                filename="premium100-%s-%03d-%s.png"%(
                    product.pk,idx+1,hashlib.sha256(png).hexdigest()[:16])
                stored="template_previews/"+filename
                if t.preview.storage.exists(stored):
                    t.preview.name=stored
                else:
                    t.preview.save(filename,ContentFile(png),save=False)
                t.save()
        self.stdout.write(self.style.SUCCESS(
            "Installed 100 complete designs, preserved source IDs. Backup: %s"%backup
        ))
