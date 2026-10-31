"""Rebuild the 100 tri-fold brochure masters with finished, premium artwork.

Only ACTIVE Marketing Materials products whose names say "tri-fold brochure"
are eligible. Never touches Canopy, Business Cards, Calendars, Flyers, Bi-Folds
or any other category. 20 curated business concepts x 5 genuinely different
art directions; each design has TWO editable pages with THREE real fold panels.

Existing V1, marketing V1, premium 100 and print V2 generated master IDs are
reused when safe. SavedDesign-referenced masters are archived unchanged, then
replaced by new active masters. A gzipped record backup precedes writes.
Preview = actual rendered Fabric objects, with large cover-first mockup.
No placeholder "REPLACE PHOTO" rectangles, no stock images from zenvibe.ca.

Run:
    python manage.py rebuild_trifold_luxury_v3 --product-id 345 --dry-run
    python manage.py rebuild_trifold_luxury_v3 --product-id 345 --apply

Optional --photo-dir must provide licensed 01.jpg...20.jpg originals. Otherwise
the same cached licensed photos used by the other premium template libraries
are loaded; a missing photo fails safely rather than producing blank artwork.

The guides mark nominal equal-thirds folds; vendor-specific flap widths,
bleed and die lines must be confirmed before press production.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from designer.models import DesignTemplate, Product, SavedDesign
from designer.management.commands.rebuild_remaining_premium_100 import (
    Artwork, Photobank, BRIEFS, BASES, PrintPage, configured_pages,
    canvas_size, physical_region, _render_page, _font, _category_path, protected,
)

GENERATOR = "zenvibe-trifold-luxury-v3"
COUNT = 100
DIRECTIONS = (
    "Editorial Maison", "Cinematic Gallery", "Organic Atelier",
    "Architectural Studio", "Contemporary Collection",
)
# Verified generated-master identifiers only; refuse arbitrary custom rows.
ALLOWED_GENERATORS = {
    GENERATOR,
    "zenvibe-trifold-brochure-v1-json-svg",
    "zenvibe-marketing-materials-v1-json-svg",
    "zenvibe-marketing-print-premium-panels-v2",
    "zenvibe-remaining-premium100-v1",
    "zenvibe-print-face-luxury-v1",
}
# Industry-specific service stories rather than repeating the same
# placeholder marketing message across 100 designs.
FEATURES = (
    ("Brand strategy", "Creative direction", "Personal service"),
    ("Beautiful properties", "Trusted local guidance", "Inspired interiors"),
    ("Seasonal menus", "Made with intention", "Gather around"),
    ("Handpicked journeys", "Unforgettable places", "Tailored escapes"),
    ("Restorative rituals", "Mindful moments", "Gentle care"),
    ("Personal wellbeing", "Compassionate support", "Trusted expertise"),
    ("Creative learning", "Confident progress", "Real opportunities"),
    ("Modern systems", "Secure solutions", "Better connections"),
    ("Focused coaching", "Stronger habits", "Feel your best"),
    ("Clear advice", "Practical planning", "Peace of mind"),
    ("Expert treatments", "Considered beauty", "Time for yourself"),
    ("Skilled craftsmanship", "Beautiful finishes", "Built with purpose"),
    ("Material stories", "Thoughtful interiors", "Timeless spaces"),
    ("Professional service", "Exceptional care", "Everyday confidence"),
    ("Personal celebrations", "Thoughtful details", "Unforgettable events"),
    ("Modern essentials", "Made to be worn", "Curated collections"),
    ("Authentic moments", "Beautiful portraits", "Stories preserved"),
    ("Trusted guidance", "Clear communication", "Personal attention"),
    ("Creative ideas", "Distinctive identity", "Brighter results"),
    ("Local people", "Stronger connections", "Room to grow"),
)
assert len(FEATURES) == len(BRIEFS) == 20


def is_trifold(product):
    if protected(product):
        return False
    name = re.sub(r"[\s_-]+", " ", (product.name or "").lower())
    return (
        bool(re.search(r"\btri\s*fold\b", name))
        and "brochure" in name
        and "marketing-materials" in _category_path(product)
    )


def art_direction(idx):
    # The FIRST 5 gallery cards use five visually different compositions.
    # All 20 industries receive all five directions across the collection.
    return ((idx // 20) + (idx % 5)) % 5


def _padbox(box, padding):
    x,y,w,h=box
    return (x+padding,y+padding,w-2*padding,h-2*padding)


def _in(box, fractional):
    x,y,w,h=box
    fx,fy,fw,fh=fractional
    return x+w*fx,y+h*fy,w*fw,h*fh


def _split_text(value, max_width=17, max_rows=2):
    """Intentional line breaks; gallery preview and Fabric wrap identically."""
    words=str(value).strip().split()
    if not words:
        return "YOUR STORY"
    rows=[]
    while words and len(rows)<max_rows:
        if len(rows)==max_rows-1:
            rows.append(" ".join(words))
            break
        line=[]
        while words and (not line or len(" ".join(line+[words[0]])) <= max_width):
            line.append(words.pop(0))
        rows.append(" ".join(line))
    return "\n".join(rows)


def _text(art,name,content,box,color,cap=42,bold=False,align="left",lines=2):
    x,y,w,h=box
    text=_split_text(content,max(10,int(w/max(12,cap)*1.9)),lines) if lines>1 else content
    # All text is explicitly editable. Rely on the shared font measurement and
    # bounds checking; no 7pt unprintable labels.
    obj=art.text(name,text,x,y,w,h,color,min(cap,h*.66,w*.18),bold,align)
    return obj


def _photo(art,bank,theme,edition,rect,name):
    x,y,w,h=rect
    if w<35 or h<35:
        raise CommandError("Configured printable panel too small for photographs")
    source=bank.crop(theme,w/h,edition)
    art.picture(source,x,y,w,h,name=name)


def _body(art,panel,bg):
    # Panel paper fills its WHOLE physical panel; editorial content is inset.
    x,y,w,h=panel
    art.rect("Editable luxury paper",x,y,w,h,bg)


def _accent(art,panel,edition,foil,ink,theme):
    x,y,w,h=panel
    # Five independent editorial signatures, not single-position dots.
    if edition==0:
        art.rect("Gold editorial baseline",x+w*.09,y+h*.074,w*.27,h*.004,foil)
    elif edition==1:
        art.rect("Double-line folio A",x+w*.085,y+h*.065,w*.48,h*.006,ink)
        art.rect("Double-line folio B",x+w*.085,y+h*.080,w*.19,h*.003,foil)
    elif edition==2:
        for j in range(3):
            art.circle("Botanical folio %s"%j,
                       x+w*(.15+j*.09),y+h*.084,
                       min(w,h)*(.009+j*.001),foil)
    elif edition==3:
        art.rect("Architectural folio",x+w*.085,y+h*.056,w*.014,h*.065,foil)
        art.rect("Architectural crossline",x+w*.106,y+h*.068,w*.20,h*.004,ink)
    else:
        art.circle("Signature mark",x+w*.15,y+h*.086,min(w,h)*.017,foil)
        art.rect("Signature caption line",x+w*.20,y+h*.084,w*.34,h*.004,foil)


def _page_panel(surface,panel,region,n=3):
    # A fold line is a physical division of the FULL page, not the
    # percentage-inset print region. Keep a safe gap from each edge.
    W,H=canvas_size(surface)
    xmin=panel*W/n
    xmax=(panel+1)*W/n
    rx,ry,rw,rh=region
    inset=min(W*.019,(xmax-xmin)*.06)
    left=max(xmin+inset,rx)
    right=min(xmax-inset,rx+rw)
    if right-left<115 or rh<360:
        raise CommandError("Tri-fold panel too small: verify landscape Admin inches and print areas")
    return (left,ry,right-left,rh)


def _panel_role(side,panel):
    # Outside flat sheet, looking at its printed face:
    # left = tucked-in flap, centre = back cover, right = front cover.
    if side==0:return ("flap","back","cover")[panel]
    return ("intro","offer","contact")[panel]


def _copy(theme,role):
    brand,headline,sub,cta,foil=BRIEFS[theme]
    feat=FEATURES[theme]
    # Every role tells a DIFFERENT part of the industry's story.
    if role=="cover":return brand,headline,sub,cta
    if role=="back":return brand,"GET IN TOUCH",feat[2],"YOURBRAND.COM"
    if role=="flap":return brand,"THE LITTLE DETAILS",feat[0],"EXPLORE MORE"
    if role=="intro":return brand,feat[0].upper(),sub,feat[1]
    if role=="offer":return brand,feat[1].upper(),feat[2],cta
    return brand,"LET'S CONNECT",sub,"YOURBRAND.COM"


def _cover(art,panel,index,edition,bank,colors):
    theme=index%20
    brand,headline,sub,cta=_copy(theme,"cover")
    paper,ink,muted=colors
    foil=BRIEFS[theme][4]
    x,y,w,h=panel
    # Full front cover colour and photography: the hero is a real JPEG,
    # editable independently, never a screenshot or REPLACE PHOTO frame.
    dark=edition in (1,3)
    if dark:
        paper="#172E39";ink="#FFF6E8";muted="#E5DDC9"
    _body(art,panel,paper)
    _accent(art,panel,edition,foil,ink,theme)

    if edition==0:       # Editorial Maison: image then commanding title
        photo=(.06,.155,.88,.46)
        eyebrow=(.11,.106,.78,.037)
        title=(.075,.643,.85,.145)
        subbox=(.09,.802,.82,.052)
        ctabox=(.10,.891,.80,.063)
    elif edition==1:     # Cinematic Gallery: type before panoramic art
        eyebrow=(.09,.128,.82,.050)
        title=(.075,.206,.85,.155)
        photo=(.07,.401,.86,.373)
        subbox=(.08,.800,.84,.045)
        ctabox=(.10,.894,.80,.061)
    elif edition==2:     # Organic Atelier: tall hero and quiet lower identity
        photo=(.06,.132,.88,.56)
        eyebrow=(.09,.716,.82,.044)
        title=(.075,.772,.85,.105)
        subbox=(.09,.881,.82,.041)
        ctabox=(.20,.936,.60,.044)
    elif edition==3:     # Architectural Studio: bespoke stacked image
        eyebrow=(.09,.122,.82,.045)
        photo=(.11,.209,.78,.362)
        title=(.075,.613,.85,.155)
        subbox=(.09,.791,.82,.051)
        ctabox=(.115,.896,.77,.061)
    else:                # Contemporary Collection: two genuinely different crops
        eyebrow=(.09,.115,.82,.044)
        photo=(.07,.187,.59,.411)
        detail=(.69,.258,.24,.34)
        title=(.075,.633,.85,.143)
        subbox=(.09,.794,.82,.052)
        ctabox=(.11,.895,.78,.064)

    _photo(art,bank,theme,edition,_in(panel,photo),"Replace front-cover photograph")
    if edition==4:
        _photo(art,bank,theme,(edition+2)%5,_in(panel,detail),
               "Replace cover-detail photograph")

    brand_box=_in(panel,eyebrow)
    title_box=_in(panel,title)
    sub_box=_in(panel,subbox)
    cx,cy,cw,ch=_in(panel,ctabox)
    _text(art,"Editable cover brand",brand,brand_box,ink,29,True,lines=1)
    _text(art,"Editable cover headline",headline,title_box,ink,49,True,lines=3)
    _text(art,"Editable cover subtitle",sub,sub_box,muted,24,False,lines=2)
    art.rect("Premium cover booking band",cx,cy,cw,ch,foil,rx=min(cw,ch)*.08)
    _text(art,"Editable cover action",cta,
          (cx+cw*.06,cy+ch*.08,cw*.88,ch*.81),
          "#172B33",24,True,align="center",lines=1)


def _flap(art,panel,index,edition,bank,colors):
    theme=index%20
    brand,headline,sub,cta=_copy(theme,"flap")
    paper,ink,muted=colors
    foil=BRIEFS[theme][4]
    x,y,w,h=panel
    _body(art,panel,paper)
    _accent(art,panel,(edition+2)%5,foil,ink,theme)
    # Less content than cover. Fold-in flap feels like a premium introduction.
    if edition in (0,3):
        image=(.11,.148,.78,.485)
        heading=(.095,.676,.81,.090)
        desc=(.10,.790,.80,.062)
    elif edition==1:
        heading=(.095,.175,.81,.105)
        image=(.10,.320,.80,.417)
        desc=(.10,.783,.80,.067)
    elif edition==2:
        image=(.12,.182,.76,.52)
        heading=(.09,.743,.82,.091)
        desc=(.10,.859,.80,.050)
    else:
        heading=(.095,.165,.81,.113)
        image=(.10,.33,.80,.386)
        desc=(.10,.786,.80,.062)
    _photo(art,bank,theme,(edition+1)%5,_in(panel,image),
           "Replace fold-in feature photograph")
    _text(art,"Editable flap title",headline,_in(panel,heading),ink,37,True,lines=3)
    _text(art,"Editable flap description",sub,_in(panel,desc),muted,23,lines=2)
    _text(art,"Editable flap action",cta,_in(panel,(.10,.914,.80,.045)),foil,23,True,lines=1)


def _back(art,panel,index,edition,bank,colors):
    theme=index%20
    brand,headline,sub,cta=_copy(theme,"back")
    paper,ink,muted=colors
    foil=BRIEFS[theme][4]
    x,y,w,h=panel
    _body(art,panel,paper)
    _accent(art,panel,(edition+1)%5,foil,ink,theme)
    # Intentional whitespace, but real artwork—not empty geometric swatches.
    _text(art,"Editable back brand",brand,_in(panel,(.09,.144,.82,.054)),
          ink,33,True,lines=1)
    _photo(art,bank,theme,(edition+3)%5,_in(panel,(.10,.262,.80,.375)),
           "Replace back-cover photograph")
    _text(art,"Editable back heading","LET'S CONNECT",
          _in(panel,(.09,.674,.82,.081)),ink,37,True)
    _text(art,"Editable back subheading",sub,
          _in(panel,(.09,.784,.82,.050)),muted,23,lines=2)
    _text(art,"Editable contact website",cta,
          _in(panel,(.09,.895,.82,.052)),foil,25,True,lines=1)


def _inside(art,panel,index,edition,bank,colors,role):
    theme=index%20
    brand,headline,sub,cta=_copy(theme,role)
    paper,ink,muted=colors
    foil=BRIEFS[theme][4]
    x,y,w,h=panel
    # The inside spread harmonises across 3 panels, but each panel has a
    # distinct visual job rather than three repeated photo/text cards.
    if role=="intro":
        _body(art,panel,paper)
        _accent(art,panel,edition,foil,ink,theme)
        _text(art,"Editable introduction label","DISCOVER",
              _in(panel,(.09,.138,.82,.048)),muted,23,True,lines=1)
        _text(art,"Editable introduction headline",headline,
              _in(panel,(.085,.216,.83,.118)),ink,44,True,lines=3)
        _photo(art,bank,theme,(edition+1)%5,
               _in(panel,(.09,.394,.82,.364)),"Replace introduction photograph")
        _text(art,"Editable introduction story",sub,
              _in(panel,(.09,.802,.82,.085)),muted,23,lines=3)
    elif role=="offer":
        _body(art,panel,"#F2EBDD" if edition in (1,3) else "#E9EEE8")
        _accent(art,panel,(edition+1)%5,foil,"#2B3F43",theme)
        _photo(art,bank,theme,(edition+2)%5,
               _in(panel,(.10,.150,.80,.400)),"Replace service photograph")
        _text(art,"Editable service headline",headline,
              _in(panel,(.085,.592,.83,.125)),"#2B3F43",41,True,lines=3)
        _text(art,"Editable service description",sub,
              _in(panel,(.09,.757,.82,.060)),"#536467",23,lines=2)
        _text(art,"Editable service action",cta,
              _in(panel,(.09,.887,.82,.055)),"#936F43",24,True,lines=1)
    else:
        _body(art,panel,paper)
        _accent(art,panel,(edition+3)%5,foil,ink,theme)
        _text(art,"Editable inside connection title",headline,
              _in(panel,(.085,.145,.83,.120)),ink,44,True,lines=3)
        _photo(art,bank,theme,edition,
               _in(panel,(.105,.323,.79,.323)),"Replace community photograph")
        _text(art,"Editable closing story",sub,
              _in(panel,(.09,.705,.82,.080)),muted,23,lines=3)
        cx,cy,cw,ch=_in(panel,(.09,.868,.82,.073))
        art.rect("Inside connection button",cx,cy,cw,ch,foil,rx=min(cw,ch)*.08)
        _text(art,"Editable contact CTA",cta,
              (cx+cw*.06,cy+ch*.08,cw*.88,ch*.82),
              "#192C32",24,True,align="center",lines=1)


def build_page(product,index,side,surface,bank):
    if side not in (0,1):
        raise CommandError("Tri-fold must have exactly 2 physical sides")
    W,H=canvas_size(surface)
    if W/H < 1.05:
        raise CommandError("Tri-fold requires a LANDSCAPE sheet configured in Admin")
    region=physical_region(product,surface,W,H)
    art=Artwork(W,H)
    edition=art_direction(index)
    theme=index%20
    paper,ink,muted=BASES[edition]
    # Full-bleed paper is visually continuous across the three panels;
    # fold-safe content is a separate inset from the actual Admin print area.
    art.rect("Editable continuous brochure substrate",*region,paper)
    for panel_index in range(3):
        role=_panel_role(side,panel_index)
        cell=_page_panel(surface,panel_index,region)
        if role=="cover":
            _cover(art,cell,index,edition,bank,(paper,ink,muted))
        elif role=="back":
            _back(art,cell,index,edition,bank,(paper,ink,muted))
        elif role=="flap":
            _flap(art,cell,index,edition,bank,(paper,ink,muted))
        else:
            _inside(art,cell,index,edition,bank,(paper,ink,muted),role)
    art.validate(region)
    page={
        "name":"Outside" if side==0 else "Inside",
        "width":W,"height":H,"editorCoordinates":True,
        "editorWidth":W,"editorHeight":H,
        "physical":{"widthIn":surface.width_in,"heightIn":surface.height_in,
                    "unit":"in"},
        "foldGuides":[1/3,2/3],
        "foldPanelCount":3,"foldStyle":"nominal-roll-fold",
        "panelRoles":[_panel_role(side,i) for i in range(3)],
        "background":"rgba(0,0,0,0)",
        "objects":art.items,
    }
    return page


def _page_image(page,scale):
    # Render exactly the same Fabric objects used by the editor.
    return _render_page(page,scale)


def _preview(pages):
    """Gallery portrait thumbnail with big cover + two actual flat spreads.

    The first image should look like a designed brochure, not a tiny contact
    sheet of six placeholder panels on a grey square. This 1000x1200 mockup
    gives the rightmost outside (front cover) the dominant visual position.
    """
    if len(pages)!=2:
        raise CommandError("Tri-fold preview requires Outside + Inside")
    stage=Image.new("RGB",(1000,1200),(241,239,235))
    dr=ImageDraw.Draw(stage)
    dr.rounded_rectangle((17,17,983,1183),radius=26,
                         fill=(249,247,242),outline=(214,209,200),width=2)
    dr.text((51,40),"THE BROCHURE COLLECTION",
            font=_font(25,True),fill=(37,48,54))

    # Outside sheet: rightmost panel = the physical front cover.
    source=pages[0]
    full=_page_image(source,1)
    cover=full.crop((round(full.width*2/3),0,full.width,full.height))
    cover.thumbnail((530,960),Image.Resampling.LANCZOS)
    xx=52+(525-cover.width)//2;yy=126+(960-cover.height)//2
    shadow=Image.new("RGBA",(cover.width+34,cover.height+34),(0,0,0,0))
    shadow_mask=Image.new("L",(cover.width,cover.height),205)
    blur=shadow_mask.filter(ImageFilter.GaussianBlur(12))
    shadow.paste((0,0,0,140),(17,17,17+cover.width,17+cover.height),blur)
    stage.paste(shadow,(xx-17,yy-17),shadow)
    stage.paste(cover,(xx,yy),cover)
    dr=ImageDraw.Draw(stage)
    dr.text((58,1110),"FRONT COVER",font=_font(22,True),fill=(77,81,78))

    # Keep both actual spreads visible, but secondary to the primary cover.
    for j,top in ((0,265),(1,678)):
        sheet=pages[j]
        small=_page_image(sheet,min(360/sheet["width"],310/sheet["height"]))
        x=610+(345-small.width)//2
        y=top+(315-small.height)//2
        stage.paste(small,(x,y),small)
        dr=ImageDraw.Draw(stage)
        dr.text((618,top-18),"OUTSIDE" if j==0 else "INSIDE",
                font=_font(18,True),fill=(68,75,76))
        # Nominal fold guides are shown only in the gallery/editor proof.
        # Production print objects never include these vertical lines.
        for fraction in sheet.get("foldGuides",[]):
            fx=x+int(small.width*fraction)
            for ly in range(y,y+small.height,20):
                dr.line((fx,ly,fx,min(ly+8,y+small.height)),
                        fill=(197,156,85),width=2)
    output=io.BytesIO()
    stage.save(output,format="PNG",optimize=True)
    return output.getvalue()


def _load_master(row):
    value=row.json_data
    if isinstance(value,str):
        try:value=json.loads(value)
        except (ValueError,TypeError):
            raise CommandError("Invalid JSON in existing tri-fold template #%d"%row.pk)
    if not isinstance(value,dict):
        raise CommandError("Invalid master type on tri-fold #%d"%row.pk)
    return value


def _existing(product):
    rows=list(DesignTemplate.objects.filter(product=product).order_by("pk"))
    active=[r for r in rows if r.is_active]
    if len(active)>COUNT:
        raise CommandError("More than 100 active tri-fold masters; review duplicates first")
    mapping={}
    for row in active:
        data=_load_master(row)
        gen=str(data.get("generator") or "")
        if gen not in ALLOWED_GENERATORS:
            raise CommandError(
                "Unknown or customer-made tri-fold master #%d (%s) not overwritten"%
                (row.pk,gen)
            )
        # Existing V1 library uses names "ZV Tri-Fold 001 · ...", V2 uses
        # "ZV Premium Tri-Fold 001 · ...". Use the FIRST stable 3-digit code.
        m=re.search(r"(?<!\d)(\d{3})(?!\d)",row.name or "")
        if not m:
            m=re.search(r"(?<!\d)(\d{3})(?!\d)",str(data.get("designCode","")))
        if not m:
            raise CommandError("Existing generated master #%d has no 001..100 index"%row.pk)
        idx=int(m.group(1))-1
        if not (0<=idx<COUNT) or idx in mapping:
            raise CommandError("Duplicate or invalid tri-fold template index %s"%idx)
        mapping[idx]=row
    return rows,mapping


def _backup(product,rows):
    folder=Path(settings.BASE_DIR)/"template_backups"
    folder.mkdir(parents=True,exist_ok=True)
    fn=folder/("trifold-%d-before-luxury-v3-%s.jsonl.gz"%(
        product.pk,datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    ))
    with gzip.open(fn,"wt",encoding="utf-8") as stream:
        for r in rows:
            stream.write(json.dumps({
                "pk":r.pk,"product_id":r.product_id,"name":r.name,
                "is_active":r.is_active,"preview":r.preview.name if r.preview else "",
                "json_data":r.json_data,
            },ensure_ascii=False,default=str)+"\n")
    return fn


def _sheet_pair(width, height):
    """Validate *physical inches*, never substitute pixel canvas dimensions."""
    try:
        w=float(width)
        h=float(height)
    except (TypeError, ValueError):
        return None
    if not all((w>0, h>0, w<=100, h<=100, w>h)):
        return None
    return (round(w,3),round(h,3))


def _previous_sheet_dimensions(originals):
    """Read existing generated masters; refuse inconsistent historical sizes.

    Legacy V1 stores document.physical, even where its values were defaulted.
    The fallback reuses exactly that old print-sheet size, with a warning that
    it still requires manufacturer verification. No made-up new measurement.
    """
    candidates=set()
    for row in originals:
        if not row.is_active:
            continue
        data=_load_master(row)
        if str(data.get("generator") or "") not in ALLOWED_GENERATORS:
            continue
        doc=data.get("document")
        doc=doc if isinstance(doc,dict) else {}
        sources=[
            doc.get("physical"),
            data.get("physical"),
        ]
        pages=data.get("pages")
        if isinstance(pages,list) and pages:
            page=pages[0]
            if isinstance(page,dict):
                sources.append(page.get("physical"))
        for source in sources:
            if not isinstance(source,dict):
                continue
            w=source.get("widthIn",source.get("width_in"))
            h=source.get("heightIn",source.get("height_in"))
            pair=_sheet_pair(w,h)
            if pair is not None:
                candidates.add(pair)
    if len(candidates)>1:
        raise CommandError(
            "Existing generated tri-folds disagree on physical sheet size "
            "(inches): %s. Set consistent dimensions in product Admin first."%
            ", ".join("%g x %g"%p for p in sorted(candidates))
        )
    return next(iter(candidates),None)


def _explicit_variant_sheet(product):
    """An already configured product variant may supply real print inches."""
    sizes=set()
    for variant in product.size_variants.filter(is_active=True):
        if variant.print_width_in is None or variant.print_height_in is None:
            continue
        pair=_sheet_pair(variant.print_width_in,variant.print_height_in)
        if pair is None:
            raise CommandError(
                "Active size variant %s has invalid tri-fold print inches"%variant.name
            )
        sizes.add(pair)
    if len(sizes)>1:
        raise CommandError(
            "Product has different active print sizes %s; select/configure one "
            "physical sheet size in Admin before rebuilding one 100-template gallery."%
            ", ".join("%g x %g"%p for p in sorted(sizes))
        )
    return next(iter(sizes),None)


def _missing_admin_sheet(product,originals,override=None):
    """Resolve a missing sheet from existing facts, not arbitrary defaults."""
    variant=_explicit_variant_sheet(product)
    old=_previous_sheet_dimensions(originals)
    if override:
        pair=_sheet_pair(*override)
        if pair is None:
            raise CommandError("Supplied physical sheet inches must be positive and landscape")
        return pair,"explicit command-line sheet dimensions"
    if variant and old and variant!=old:
        raise CommandError(
            "Configured size-variant print size (%g x %g in) conflicts with "
            "existing generated template metadata (%g x %g in). "
            "Check Admin before generating."%(variant+old)
        )
    if variant:
        return variant,"existing active ProductSizeVariant print dimensions"
    if old:
        return old,"legacy generated template physical metadata (NOT printer-verified)"
    raise CommandError(
        "Product #%s has no Admin print inches, configured size-variant inches "
        "or historical template sheet measurements. Configure the product's "
        "physical print width/height in Admin, or supply --sheet-width-in and "
        "--sheet-height-in from the actual supplier specification."%product.pk
    )


def resolve_trifold_pages(product, originals, override=None, log=None):
    """Use Admin first; fall back to explicit historical/variant data safely.

    This function does NOT save product settings or modify templates.
    """
    if override and not all(v is not None for v in override):
        raise CommandError("Provide BOTH --sheet-width-in and --sheet-height-in")
    if override and all(v is not None for v in override):
        if _sheet_pair(*override) is None:
            raise CommandError("Supplied sheet width and height must be valid landscape inches")

    try:
        pages=configured_pages(product,"brochure")
    except CommandError as exc:
        if "Admin print width/height missing" not in str(exc):
            raise
        # A partially configured surface is an Admin error: never override it
        # with an unrelated legacy template-size guess.
        if product.print_surfaces.filter(is_active=True).exists():
            raise CommandError(
                "An active Admin print surface is missing physical dimensions. "
                "Fix that specific surface rather than inheriting legacy sizes."
            ) from exc
        pair,source=_missing_admin_sheet(product,originals,override)
        w,h=pair
        ww=float(product.workspace_width_in or w)
        wh=float(product.workspace_height_in or h)
        if ww<=0 or wh<=0 or ww/wh>15 or wh/ww>15:
            raise CommandError("Invalid product workspace ratio; correct Admin values")

        # Respect any real print-area percentage already configured in Admin.
        bounds=(0.0,0.0,1.0,1.0)
        for area in product.print_areas.order_by("sort_order","pk"):
            if area.surface_id is not None or area.product_image_id is not None:
                continue
            try:
                bx,by,bw,bh=(float(getattr(area,v))/100 for v in
                            ("left","top","width","height"))
            except (TypeError,ValueError):
                raise CommandError("Admin print-area bounds are invalid")
            if not (0<=bx<1 and 0<=by<1 and bw>0 and bh>0
                    and bx+bw<=1.001 and by+bh<=1.001):
                raise CommandError("Admin print-area bounds exceed the workspace")
            bounds=(bx,by,bw,bh)
            break
        pages=[
            PrintPage("Outside",w,h,ww,wh,bounds),
            PrintPage("Inside",w,h,ww,wh,bounds),
        ]
        if log:
            log(
                "Admin print dimensions missing for #%d. Reusing %g x %g inches "
                "from %s. No product settings changed. CONFIRM WITH PRINTER "
                "BEFORE PRODUCTION."%(product.pk,w,h,source)
            )
    else:
        if override and _sheet_pair(*override)!=(round(pages[0].width_in,3),
                                                  round(pages[0].height_in,3)):
            raise CommandError(
                "Explicit inches conflict with configured Admin print surfaces; "
                "change Admin if those are incorrect."
            )
    if len(pages)!=2 or any(face.width_in<=face.height_in for face in pages):
        raise CommandError("Tri-fold requires two landscape Outside/Inside print faces")
    return pages


class Command(BaseCommand):
    help="Install 100 finished, luxury tri-fold designs without touching other categories."

    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,required=True)
        p.add_argument("--photo-dir",default="",help="Licensed 01.jpg..20.jpg original photography")
        p.add_argument("--sheet-width-in",type=float,default=None,
                       help="Physical print width in inches ONLY when Admin is missing it")
        p.add_argument("--sheet-height-in",type=float,default=None,
                       help="Physical print height in inches ONLY when Admin is missing it")
        mode=p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--contact-sheet",action="store_true",
                          help="Render all 100 real-photo gallery mockups into one JPEG proof; no database changes")
        mode.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        product=Product.objects.select_related("category","category__parent").filter(
            pk=opts["product_id"],is_active=True
        ).first()
        if not product or not is_trifold(product):
            raise CommandError("Only active Marketing Materials TRI-FOLD BROCHURE products can be changed")
        originals,mapping=_existing(product)
        width=opts.get("sheet_width_in")
        height=opts.get("sheet_height_in")
        if (width is None)!=(height is None):
            raise CommandError("Use --sheet-width-in and --sheet-height-in together")
        override=(width,height) if width is not None else None
        pages_cfg=resolve_trifold_pages(
            product,originals,override=override,
            log=lambda msg: self.stdout.write(self.style.WARNING(msg)),
        )
        photos=Photobank(opts.get("photo_dir"),dry_run=opts["dry_run"])
        built=[]; signatures=set()
        for idx in range(COUNT):
            pages=[build_page(product,idx,side,face,photos)
                   for side,face in enumerate(pages_cfg)]
            signature=hashlib.sha256(json.dumps([
                [(o["type"],o["left"],o["top"],o["width"],o["height"],
                  o.get("text"),str(o.get("src",""))[:60]) for o in p["objects"]]
                for p in pages
            ],sort_keys=True).encode()).hexdigest()
            if signature in signatures:
                raise CommandError("Repeated tri-fold composition at index %03d"%(idx+1))
            signatures.add(signature)
            family=BRIEFS[idx%20][0]
            direction=DIRECTIONS[art_direction(idx)]
            name="ZV Tri-Fold %03d · %s · %s"%(idx+1,family,direction)
            document={
                "generator":GENERATOR,"version":3,
                "templateType":"editable-master","editable":True,
                "editorNative":True,"previewComplete":True,
                "width":pages[0]["width"],"height":pages[0]["height"],
                "pageCount":2,"pages":pages,
                "compositionSignature":signature,
                "designFamily":family,"direction":direction,
                "brochure":{"type":"tri-fold","panelsPerSide":3,
                    "outsideOrder":["Fold-In Flap","Back Cover","Front Cover"],
                    "insideOrder":["Introduction","Services","Contact"],
                    "foldGuideOnly":True},
                "productionNote":"Nominal one-third folds. Verify fold-in flap, bleed and trim with printer.",
            }
            preview=_preview(pages) if (opts["apply"] or opts["contact_sheet"]) else None
            if preview is not None and len(preview)<9000:
                raise CommandError("Incomplete gallery preview at %03d"%(idx+1))
            built.append((idx,name,document,preview))

        self.stdout.write(self.style.SUCCESS(
            "Validated 100 professional, editable tri-fold masters "
            "(200 sides / 600 correctly bounded panels) for product #%d %s"%
            (product.pk,product.name)
        ))
        if opts["dry_run"]:
            self.stdout.write(
                "Dry run complete; database/preview unchanged. Existing active masters: %d"%
                sum(r.is_active for r in originals)
            )
            return
        if opts["contact_sheet"]:
            # Real photographs and actual editorial template objects, not the
            # synthetic dry-run photo fixture. One visual proof for ALL 100.
            cols=10; rows=10; tile_w=250; tile_h=365
            sheet=Image.new("RGB",(cols*tile_w,rows*tile_h),"#F4F1EC")
            drawing=ImageDraw.Draw(sheet)
            for idx,name,document,preview in built:
                with Image.open(io.BytesIO(preview)) as opened:
                    tile=opened.convert("RGB")
                    tile.thumbnail((232,325),Image.Resampling.LANCZOS)
                xx=(idx%cols)*tile_w+9+(232-tile.width)//2
                yy=(idx//cols)*tile_h+5+(325-tile.height)//2
                sheet.paste(tile,(xx,yy))
                drawing.text(((idx%cols)*tile_w+10,(idx//cols)*tile_h+337),
                             "%03d  %s"%(idx+1,BRIEFS[idx%20][0][:20]),
                             fill="#243641",font=_font(14,True))
            folder=Path(settings.BASE_DIR)/"template_reports"
            folder.mkdir(parents=True,exist_ok=True)
            path=folder/("trifold_v3_100_contact_sheet_%d.jpg"%product.pk)
            sheet.save(path,format="JPEG",quality=88,optimize=True)
            self.stdout.write(self.style.SUCCESS(
                "100-design visual contact sheet (real photographs; database unchanged): %s"%path
            ))
            return
        backup=_backup(product,originals)
        references=set(SavedDesign.objects.filter(
            source_template_id__in=[r.pk for r in mapping.values()]
        ).values_list("source_template_id",flat=True))
        with transaction.atomic():
            for idx,name,document,preview in built:
                old=mapping.get(idx)
                if old is not None and old.pk in references:
                    # Preserve historical source JSON exactly for customer
                    # designs already in their carts/orders/saved drafts.
                    old.is_active=False
                    old.save(update_fields=["is_active"])
                    row=DesignTemplate(product=product)
                else:
                    row=old or DesignTemplate(product=product)
                row.name=name
                row.json_data=document
                row.is_active=True
                filename="trifold-luxury-v3-%d-%03d-%s.png"%(
                    product.pk,idx+1,hashlib.sha256(preview).hexdigest()[:14]
                )
                stored="template_previews/"+filename
                if row.preview.storage.exists(stored):
                    row.preview.name=stored
                else:
                    row.preview.save(filename,ContentFile(preview),save=False)
                row.save()
            active=DesignTemplate.objects.filter(product=product,is_active=True).count()
            if active!=COUNT:
                raise CommandError("Expected 100 active tri-fold designs, found %d"%active)
        self.stdout.write(self.style.SUCCESS(
            "INSTALLED: 100 distinct active tri-folds. Archived %d referenced "
            "original(s), reused other template IDs. Backup: %s"%
            (len(references),backup)
        ))
