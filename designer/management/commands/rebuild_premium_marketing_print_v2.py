"""Professionally composed Flyers / Bi-Fold / Tri-Fold galleries (100 each).

ONLY three marketing products are eligible. Canopy, Calendars, Business Cards,
Invitations and every other category are untouched.

This fixes:
* full-colour, category-led photo + editorial typography (not empty shapes);
* 20 industry briefs x 5 different compositions = 100 distinct templates;
* bi-fold outside/inside with TWO genuine fold panels on each page;
* tri-fold outside/inside with THREE panels on each page in print order;
* true panel boundaries and per-panel safe insets; no cross-fold text;
* all photos, text and vector accents independently editable in Fabric;
* print-only fold lines NEVER baked into the actual printable design;
* gallery preview composed from exactly the same editor object geometry;
* backups, saved-design reference preservation and stable active count=100.

    python manage.py rebuild_premium_marketing_print_v2 --all --dry-run
    python manage.py rebuild_premium_marketing_print_v2 --all --apply
    python manage.py rebuild_premium_marketing_print_v2 --product-id 62 --dry-run

Needs actual Admin print dimensions. Uses the same cached/curated photographs as
the premium calendar-quality products. No access to zenvibe.ca.
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
from django.db.models import Q
from PIL import Image, ImageDraw, ImageFilter

from designer.models import Product, DesignTemplate, SavedDesign
from designer.management.commands.rebuild_remaining_premium_100 import (
    Artwork, Photobank, BRIEFS, BASES, DIRECTIONS, TARGET,
    canvas_size, physical_region, _render_page, _font, protected,
    configured_pages, layout_index, _category_path,
)

GENERATOR = "zenvibe-marketing-print-premium-panels-v2"
SAFE_LEGACY_PREFIXES = (
    "zenvibe-flyer-", "zenvibe-trifold-", "zenvibe-marketing-materials-",
    "zenvibe-print-face-", "zenvibe-remaining-premium100-",
    GENERATOR,
)


def product_kind(product):
    name=re.sub(r"[\s_-]+"," ",(product.name or "").lower())
    if protected(product):
        return ""
    # Scope is strict: a product whose name merely mentions 'flyer' outside
    # Marketing Materials must NEVER be modified by this repair.
    category_path=_category_path(product)
    if "marketing-materials" not in category_path:
        return ""
    # Explicit only: never match other promotional products with the word
    # 'fold', 'flyer' or 'card' inside their descriptions.
    if re.search(r"\btri ?fold\b",name) and "brochure" in name:
        return "trifold"
    if re.search(r"\bbi ?fold\b",name) and "brochure" in name:
        return "bifold"
    if re.search(r"\bflyers?\b",name):
        return "flyer"
    return ""


def _wrap(text, max_lines=2, max_chars=16):
    """Balanced headlines without relying on per-browser word wrapping."""
    words=str(text or "").split()
    if not words:
        return "YOUR STORY"
    rows=[]
    while words and len(rows)<max_lines:
        if len(rows)==max_lines-1:
            rows.append(" ".join(words))
            break
        line=[]
        while words and (not line or len(" ".join(line+[words[0]]))<=max_chars):
            line.append(words.pop(0))
        rows.append(" ".join(line))
    return "\n".join(rows)


def _label(art,name,text,bounds,color,weight=False,ideal=38,align="center"):
    x,y,w,h=bounds
    return art.text(name,text,x,y,w,h,color,min(ideal,h*.69,w*.18),
                    bold=weight,align=align)


def _box(x,y,w,h,rel):
    return (x+w*rel[0],y+h*rel[1],w*rel[2],h*rel[3])


def _photo(art,bank,theme,edition,frame,name="Replace editorial photograph"):
    x,y,w,h=frame
    if min(w,h)<25:
        raise CommandError("Photo frame too narrow for print-ready brochure art")
    source=bank.crop(theme,w/h,edition)
    art.picture(source,x,y,w,h,name=name)


def _safe_panel(surface,region,panel_index,panel_count):
    """Use ACTUAL W/n fold positions, not inset region/n, for perfect fit."""
    W,H=canvas_size(surface)
    rx,ry,rw,rh=region
    start=W*panel_index/panel_count
    end=W*(panel_index+1)/panel_count
    # Fold-safe separation; without this, lines of text can cross fold edges.
    gap=min(W*.024,(end-start)*.075)
    left=max(start+gap,rx)
    right=min(end-gap,rx+rw)
    if right-left<95:
        raise CommandError("Fold panel too small for professional editable layout")
    return left,ry,right-left,rh


def _panel_role(kind,side,panel):
    if kind=="bifold":
        return ("back","cover")[panel] if side==0 else ("story","services")[panel]
    if side==0:
        return ("flap","back","cover")[panel]
    return ("story","services","contact")[panel]


def _panel_copy(theme,role):
    brand,title,subtitle,cta,accent=BRIEFS[theme]
    headline={
        "cover": title,
        "back":"THE DETAILS",
        "flap":"DISCOVER MORE",
        "story":"OUR STORY",
        "services":"MADE FOR YOU",
        "contact":"LET'S CONNECT",
    }[role]
    foot={
        "cover":cta,"back":"YOURBRAND.COM","flap":"EXPLORE NOW",
        "story":"READ OUR STORY","services":"FIND OUT MORE","contact":"GET IN TOUCH"
    }[role]
    return brand,headline,subtitle,foot,accent


def _panel_art(art,region,index,edition,role,bank,side):
    """Five genuinely different balanced photo/story hierarchies per panel.

    Every text box lies inside a single panel, away from the physical fold.
    Copy and images use the same Fabric objects that render in the preview.
    """
    theme=index%20
    brand,title,subtitle,cta,accent=_panel_copy(theme,role)
    x,y,w,h=region
    bg,ink,muted=BASES[edition]
    # Alternate cover/panel tones for a connected luxury spread.
    if role in ("back","story") and edition%2==0:
        bg="#EAE4DB";ink="#293D45";muted="#637076"
    # Every panel's artwork is independent, replaceable, bounded and visible.
    art.rect("Editable panel paper",x,y,w,h,bg)
    foil=accent
    art.rect("Editorial section rule",x+w*.08,y+h*.065,
             w*(.13+.025*(edition%4)),max(1,h*.004),foil)
    art.circle("Edition seal",x+w*.89,y+h*.079,
               min(w,h)*(.009+.003*(index%4)),foil)

    # Non-overlapping object bands; the five editions materially move
    # photography, brand, headline and the call-to-action.
    if edition==0:  # Gallery cover: photo up top, oversized clear heading
        photo=(.07,.145,.86,.405)
        brand_pos=(.08,.57,.84,.059)
        title_pos=(.08,.652,.84,.113)
        sub_pos=(.09,.785,.82,.054)
        cta_pos=(.12,.875,.76,.061)
    elif edition==1:  # Editorial: typography first, photograph below
        brand_pos=(.09,.132,.82,.060)
        title_pos=(.075,.224,.85,.139)
        photo=(.09,.397,.82,.335)
        sub_pos=(.09,.766,.82,.052)
        cta_pos=(.11,.870,.78,.066)
    elif edition==2:  # Immersive art: full-width photo, clean lower caption
        photo=(.045,.125,.91,.52)
        brand_pos=(.085,.671,.83,.051)
        title_pos=(.075,.733,.85,.095)
        sub_pos=(.09,.836,.82,.045)
        cta_pos=(.13,.918,.74,.050)
    elif edition==3:  # Architectural split: framed photo and stacked headline
        brand_pos=(.095,.135,.81,.060)
        photo=(.16,.246,.68,.345)
        title_pos=(.09,.622,.82,.120)
        sub_pos=(.10,.777,.80,.048)
        cta_pos=(.135,.878,.73,.068)
    else:  # Collage: different image geometry, two independent image areas
        brand_pos=(.09,.105,.82,.055)
        photo=(.08,.188,.57,.420)
        second=(.68,.268,.24,.34)
        title_pos=(.07,.639,.86,.125)
        sub_pos=(.09,.787,.82,.048)
        cta_pos=(.12,.883,.76,.065)

    # The photo panel is visually dominant; nothing prints over the photograph.
    _photo(art,bank,theme,edition,_box(x,y,w,h,photo))
    if edition==4:
        _photo(art,bank,theme,(edition+2)%5,
               _box(x,y,w,h,second),"Replace second collage photograph")

    # For photo-heavy formats, fit only printable, sufficiently large type.
    # Short role-specific copy prevents the over-wide center alignment and
    # overlapping headings seen in the old 100-template brochure libraries.
    brand_box=_box(x,y,w,h,brand_pos)
    headline_box=_box(x,y,w,h,title_pos)
    subtitle_box=_box(x,y,w,h,sub_pos)
    call_box=_box(x,y,w,h,cta_pos)
    _label(art,"Editable business name",brand,brand_box,muted,True,
           min(42,w*.092),align="center")
    _label(art,"Editable panel headline",
           _wrap(title,2,15 if w<480 else 22),
           headline_box,ink,True,min(60,w*.112))
    _label(art,"Editable supporting copy",subtitle,subtitle_box,
           muted,False,min(34,w*.063))
    cx,cy,cw,ch=call_box
    art.rect("Editable action band",cx,cy,cw,ch,foil,rx=ch*.08)
    _label(art,"Editable panel CTA",cta,
           (cx+cw*.05,cy+ch*.085,cw*.90,ch*.76),
           "#18282C",True,min(35,w*.076))
    art.rect("Signature footer detail",x+w*.10,y+h*.968,
             w*.18,h*.003,foil)


def _flyer_art(art,region,index,bank):
    """Photo-driven hero-page typography—not generic brochure panel art."""
    x,y,w,h=region
    edition=layout_index(index)
    theme=index%20
    brand,headline,subtitle,cta,accent=BRIEFS[theme]
    bg,ink,muted=BASES[edition]
    art.rect("Editable flyer background",x,y,w,h,bg)
    art.rect("Elegant flyer kicker",x+w*.07,y+h*.047,w*.17,h*.004,accent)
    art.circle("Flyer signature",x+w*.89,y+h*.066,
               min(w,h)*(.012+.003*(index%3)),accent)
    if edition==0:  # magazine cover
        photo=(.065,.118,.87,.50)
        brand_pos=(.09,.066,.82,.045)
        title_pos=(.075,.647,.85,.122)
        sub_pos=(.085,.789,.83,.051)
        cta_pos=(.10,.881,.80,.075)
    elif edition==1: # headline first, large photography beneath
        brand_pos=(.10,.085,.80,.048)
        title_pos=(.08,.166,.84,.185)
        photo=(.075,.379,.85,.393)
        sub_pos=(.09,.795,.82,.048)
        cta_pos=(.10,.887,.80,.071)
    elif edition==2: # immersive landscape photo and crisp lower copy
        photo=(.045,.065,.91,.608)
        brand_pos=(.09,.693,.82,.045)
        title_pos=(.06,.754,.88,.111)
        sub_pos=(.085,.873,.83,.036)
        cta_pos=(.18,.925,.64,.053)
    elif edition==3: # asymmetric art + title stack
        photo=(.07,.19,.54,.585)
        brand_pos=(.09,.10,.82,.05)
        title_pos=(.645,.275,.285,.244)
        sub_pos=(.645,.569,.28,.104)
        cta_pos=(.12,.848,.76,.077)
    else: # real two-photo story collage
        brand_pos=(.10,.075,.80,.050)
        photo=(.065,.161,.535,.450)
        secondary=(.625,.244,.31,.36)
        title_pos=(.085,.649,.83,.126)
        sub_pos=(.095,.80,.81,.049)
        cta_pos=(.12,.890,.76,.066)
    _photo(art,bank,theme,edition,_box(x,y,w,h,photo))
    if edition==4:
        _photo(art,bank,theme,(edition+2)%5,
               _box(x,y,w,h,secondary),"Replace detail photograph")
    _label(art,"Editable brand",brand,_box(x,y,w,h,brand_pos),
           muted,True,min(45,w*.065))
    # An asymmetric edition uses fewer, shorter words on its slim right rail.
    display_title=_wrap(headline,3 if edition==3 else 2,
                        10 if edition==3 else 24)
    _label(art,"Editable main headline",display_title,
           _box(x,y,w,h,title_pos),ink,True,
           min(70,w*(.10 if edition!=3 else .046)))
    _label(art,"Editable supporting description",subtitle,
           _box(x,y,w,h,sub_pos),muted,False,min(34,w*.051))
    cx,cy,cw,ch=_box(x,y,w,h,cta_pos)
    art.rect("Premium CTA panel",cx,cy,cw,ch,accent,rx=min(cw,ch)*.08)
    _label(art,"Editable call to action",cta,
           (cx+cw*.06,cy+ch*.09,cw*.88,ch*.76),"#172C32",
           True,min(38,w*.075))
    art.rect("Bottom foil line",x+w*.11,y+h*.973,w*.78,h*.003,accent)


def make_marketing_page(product,kind,index,side,surface,bank):
    W,H=canvas_size(surface)
    region=physical_region(product,surface,W,H)
    art=Artwork(W,H)
    edition=layout_index(index)
    if kind=="flyer":
        if side:
            raise CommandError("Flyers must have one artwork page")
        _flyer_art(art,region,index,bank)
        folds=[]
    else:
        n=2 if kind=="bifold" else 3
        folds=[i/n for i in range(1,n)]
        # One continuous paper colour beneath all fold-safe panels prevents
        # the vertical blank strips and disconnected-card look of old masters.
        rx,ry,rw,rh=region
        art.rect("Editable cohesive brochure base",rx,ry,rw,rh,
                 BASES[edition][0])
        # Cover outside placement: bi [back,cover]; tri [flap,back,cover].
        # The inside is a real 2/3-panel spread, not a duplicated cover.
        for panel in range(n):
            role=_panel_role(kind,side,panel)
            panel_box=_safe_panel(surface,region,panel,n)
            # Changing panel role changes copy and photo architecture. Keep
            # the panel colours harmonised, but not monochrome duplicates.
            panel_edition=(edition+panel+(side%2))%5
            _panel_art(art,panel_box,index,panel_edition,role,bank,side)
    art.validate(region)
    return {
        "name":surface.label if kind=="flyer" else ("Outside" if side==0 else "Inside"),
        "width":W,"height":H,
        "editorCoordinates":True,"editorWidth":W,"editorHeight":H,
        "physical":{"widthIn":surface.width_in,"heightIn":surface.height_in,"unit":"in"},
        "background":"rgba(0,0,0,0)",
        "foldGuides":folds, "foldPanelCount":len(folds)+1,
        "objects":art.items,
    }


def _preview(pages,kind):
    """Existing portrait gallery card shows full cover and a real page 2."""
    canvas=Image.new("RGB",(900,1160),(243,242,239))
    d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((14,14,886,1146),radius=16,fill=(250,249,246),
                        outline=(214,215,217),width=2)
    d.text((42,40),{"flyer":"PREMIUM FLYER","bifold":"BI-FOLD COLLECTION",
                    "trifold":"TRI-FOLD COLLECTION"}[kind],
           font=_font(25,True),fill=(41,53,62))
    areas=[(0,35,95,830,960)] if len(pages)==1 else [
        (0,30,96,840,587),(1,112,724,676,345)
    ]
    for index,left,top,width,height in areas:
        page=pages[index]
        scale=min(width/max(1,page["width"]),height/max(1,page["height"]))
        rendered=_render_page(page,scale)
        x=left+(width-rendered.width)//2
        y=top+(height-rendered.height)//2
        shadow=Image.new("RGBA",(rendered.width+28,rendered.height+28),
                         (0,0,0,0))
        alpha=rendered.getchannel("A").filter(ImageFilter.GaussianBlur(8))
        shadow.paste((0,0,0,110),(12,12,12+rendered.width,12+rendered.height),alpha)
        canvas.paste(shadow,(x-12,y-12),shadow)
        canvas.paste(rendered,(x,y),rendered)
        # Folds only in the PREVIEW proof, not in Fabric printable artwork.
        fold=page.get("foldGuides",[])
        d=ImageDraw.Draw(canvas)
        for fraction in fold:
            fx=x+int(rendered.width*fraction)
            for y0 in range(y,y+rendered.height,18):
                d.line((fx,y0,fx,min(y0+8,y+rendered.height)),
                       fill=(196,143,74),width=2)
        if len(pages)>1:
            d.text((x+12,y+12),"OUTSIDE" if index==0 else "INSIDE",
                   font=_font(17,True),fill=(40,48,54))
    out=io.BytesIO()
    canvas.save(out,format="PNG",optimize=True)
    return out.getvalue()


def _guard_existing(product):
    all_rows=list(DesignTemplate.objects.filter(product=product).order_by("pk"))
    current=[row for row in all_rows if row.is_active]
    if len(current)>100:
        raise CommandError("More than 100 active templates. Resolve duplicates first.")
    indexed={}
    for row in current:
        data=row.json_data
        if isinstance(data,str):
            try:data=json.loads(data)
            except (ValueError,TypeError):raise CommandError("Malformed master %s"%row.pk)
        if not isinstance(data,dict):
            raise CommandError("Unrecognised template data on %s"%row.pk)
        generator=str(data.get("generator") or "")
        if not generator.startswith(SAFE_LEGACY_PREFIXES):
            raise CommandError("Unknown/customer-authored master %s; will NOT overwrite"%row.pk)
        matches=re.search(r"(?:^|\b)(\d{3})(?:\b|$)",row.name or "")
        if not matches:
            # Older auto-generated flyers must be mapped from their own
            # stable sequential ID, not by a guessed index when revisions
            # include customer-linked records.
            code=str(data.get("flyer_code") or data.get("designCode") or "")
            matches=re.search(r"(\d{3})$",code)
        if not matches:
            raise CommandError("Template %s has no stable 001..100 index"%row.pk)
        idx=int(matches.group(1))-1
        if not (0<=idx<100) or idx in indexed:
            raise CommandError("Duplicate/out-of-range template index")
        indexed[idx]=row
    return all_rows,indexed


def _save_backup(product,templates):
    folder=Path(settings.BASE_DIR)/"template_backups"
    folder.mkdir(parents=True,exist_ok=True)
    tag=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path=folder/("marketing-print-%s-before-v2-%s.jsonl.gz"%(product.pk,tag))
    with gzip.open(path,"wt",encoding="utf-8") as out:
        for t in templates:
            out.write(json.dumps({
                "pk":t.pk,"product_id":t.product_id,"name":t.name,
                "is_active":t.is_active,"json_data":t.json_data,
                "preview":t.preview.name if t.preview else "",
            },ensure_ascii=False,default=str)+"\n")
    return path


class Command(BaseCommand):
    help="Build 100 professional editable flyers, bi-fold or tri-fold brochures."

    def add_arguments(self,p):
        scope=p.add_mutually_exclusive_group(required=True)
        scope.add_argument("--product-id",type=int)
        scope.add_argument("--all",action="store_true",
                           help="ONLY active flyer / bi-fold / tri-fold brochure products")
        p.add_argument("--photo-dir",default="",
                       help="Optional licensed 01.jpg..20.jpg industry photos")
        mode=p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        if opts["all"]:
            products=list(Product.objects.filter(is_active=True).filter(
                Q(name__icontains="flyer")|Q(name__icontains="fold")
            ).select_related("category","category__parent").order_by("pk"))
            products=[p for p in products if product_kind(p)]
        else:
            products=list(Product.objects.filter(
                pk=opts["product_id"],is_active=True
            ).select_related("category","category__parent"))
        if not products:
            raise CommandError("No eligible active flyer/bi-fold/tri-fold products")
        jobs=[]
        for product in products:
            kind=product_kind(product)
            if not kind:
                raise CommandError("Unsupported/protected product: %s"%product.name)
            rows,indexed=_guard_existing(product)
            surfaces=configured_pages(product,"brochure" if kind!="flyer" else "flyer")
            if kind=="flyer" and len(surfaces)!=1:
                raise CommandError("Flyer requires exactly 1 Admin print page")
            if kind!="flyer" and len(surfaces)!=2:
                raise CommandError("%s needs Outside and Inside pages"%kind)
            if kind!="flyer" and any(s.width_in<=s.height_in for s in surfaces):
                raise CommandError(
                    "%s requires landscape folding stock; check Admin print inches"%kind
                )
            jobs.append((product,kind,rows,indexed,surfaces))
        bank=Photobank(opts.get("photo_dir"),dry_run=opts["dry_run"])
        failures=[]
        for product,kind,rows,indexed,surfaces in jobs:
            try:
                built=[];signatures=set()
                for idx in range(TARGET):
                    pages=[make_marketing_page(product,kind,idx,side,surf,bank)
                           for side,surf in enumerate(surfaces)]
                    key=hashlib.sha256(json.dumps([
                        [(o["type"],o["left"],o["top"],o["width"],o["height"],
                          o.get("text"),o.get("src","")[:32]) for o in p["objects"]]
                        for p in pages
                    ],sort_keys=True).encode()).hexdigest()
                    if key in signatures:
                        raise CommandError("Repeated layout at %03d"%(idx+1))
                    signatures.add(key)
                    theme=BRIEFS[idx%20][0]
                    name="ZV %s %03d · %s · %s"%(
                        {"flyer":"Premium Flyer","bifold":"Premium Bi-Fold",
                         "trifold":"Premium Tri-Fold"}[kind],
                        idx+1,theme,DIRECTIONS[layout_index(idx)])
                    data={
                        "generator":GENERATOR,"version":2,"templateType":"editable-master",
                        "editable":True,"editorNative":True,"pageCount":len(pages),
                        "width":pages[0]["width"],"height":pages[0]["height"],
                        "pages":pages,"printProfile":"admin-defined",
                        "designFamily":kind,"compositionSignature":key,
                        "previewComplete":True,
                    }
                    png=_preview(pages,kind) if opts["apply"] else None
                    built.append((idx,name,data,png))
                self.stdout.write(self.style.SUCCESS(
                    "Validated 100 distinct %s designs for #%s %s (%d real page(s))."%(
                        kind,product.pk,product.name,len(surfaces)
                    )
                ))
                if opts["dry_run"]:
                    continue
                backup=_save_backup(product,rows)
                linked=set(SavedDesign.objects.filter(
                    source_template_id__in=[t.pk for t in indexed.values()]
                ).values_list("source_template_id",flat=True))
                with transaction.atomic():
                    for idx,name,data,png in built:
                        old=indexed.get(idx)
                        if old is not None and old.pk in linked:
                            old.is_active=False
                            old.save(update_fields=["is_active"])
                            master=DesignTemplate(product=product)
                        else:
                            master=old or DesignTemplate(product=product)
                        master.name=name
                        master.json_data=data
                        master.is_active=True
                        filename="marketing-premium-v2-%s-%03d-%s.png"%(
                            product.pk,idx+1,hashlib.sha256(png).hexdigest()[:12]
                        )
                        store="template_previews/"+filename
                        if master.preview.storage.exists(store):
                            master.preview.name=store
                        else:
                            master.preview.save(filename,ContentFile(png),save=False)
                        master.save()
                count=DesignTemplate.objects.filter(product=product,is_active=True).count()
                if count!=100:
                    raise CommandError("Installed %d active designs, expected 100"%count)
                self.stdout.write(self.style.SUCCESS(
                    "Installed 100 aligned layouts; customer sources preserved; backup: %s"%backup
                ))
            except Exception as exc:
                failures.append("%s %s: %s"%(product.pk,product.name,exc))
                self.stderr.write("FAILED: "+failures[-1])
        if failures:
            raise CommandError("%d marketing libraries need attention:\n%s"%(
                len(failures),"\n".join(failures)
            ))
        self.stdout.write(self.style.SUCCESS(
            "All requested marketing libraries validated." if opts["dry_run"] else
            "All requested marketing libraries installed."
        ))
