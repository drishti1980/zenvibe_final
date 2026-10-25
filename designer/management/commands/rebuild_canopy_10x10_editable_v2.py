import copy
import math
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-canopy-7page-editable-v2"
LOGICAL_W = 1200

PALETTES = [
    ("#0B1F3A","#0F766E","#F8FAFC","#F59E0B"),
    ("#111827","#2563EB","#F9FAFB","#22C55E"),
    ("#3B0764","#7E22CE","#FFF7ED","#F59E0B"),
    ("#172554","#1D4ED8","#EFF6FF","#F97316"),
    ("#052E16","#16A34A","#F0FDF4","#EAB308"),
    ("#450A0A","#DC2626","#FFF7ED","#F59E0B"),
    ("#1F2937","#0891B2","#ECFEFF","#F43F5E"),
    ("#0F172A","#7C3AED","#FAF5FF","#14B8A6"),
    ("#422006","#CA8A04","#FFFBEB","#7C3AED"),
    ("#0C4A6E","#0284C7","#F0F9FF","#F97316"),
    ("#134E4A","#0D9488","#F0FDFA","#FB7185"),
    ("#312E81","#4F46E5","#EEF2FF","#F59E0B"),
    ("#3F3F46","#71717A","#FAFAFA","#E11D48"),
    ("#1E3A8A","#60A5FA","#EFF6FF","#FBBF24"),
    ("#3F6212","#84CC16","#F7FEE7","#0EA5E9"),
    ("#701A75","#D946EF","#FDF4FF","#22C55E"),
    ("#4C0519","#BE123C","#FFF1F2","#14B8A6"),
    ("#164E63","#06B6D4","#ECFEFF","#F59E0B"),
    ("#292524","#A16207","#FAFAF9","#0EA5E9"),
    ("#1C1917","#EA580C","#FFF7ED","#06B6D4"),
]

FAMILIES = [
    "geometric_sweep","diagonal_ribbon","center_badge","corner_burst","wave_motion",
    "hex_brand","luxury_frame","sport_stripes","tech_grid","festival_confetti",
    "split_angle","diamond_focus","circle_orbit","minimal_lines","shield_mark",
    "sunburst","leaf_arc","chevron_stack","block_modern","spotlight"
]

VARIANTS = ["Prime","Edge","Bold","Studio","Pro"]


def obj_base(kind, name, left=0, top=0, fill="#111827", **kw):
    d = {
        "id": name,
        "type": kind,
        "name": name,
        "left": float(left),
        "top": float(top),
        "fill": fill,
        "opacity": float(kw.pop("opacity", 1)),
        "angle": float(kw.pop("angle", 0)),
        "customerEditable": True,
        "locked": False,
        "selectable": True,
        "evented": True,
    }
    d.update(kw)
    return d


def rect(name,x,y,w,h,fill,**kw):
    return obj_base("rect",name,x,y,fill,width=float(w),height=float(h),**kw)

def textbox(name,x,y,w,text,size,fill,weight=600,align="center",angle=0,font="Montserrat",**kw):
    return obj_base(
        "textbox",name,x,y,fill,width=float(w),text=text,fontSize=float(size),
        font=font,fontFamily=font,fontWeight=weight,textAlign=align,
        lineHeight=1.0,angle=angle,**kw
    )

def line(name,x1,y1,x2,y2,stroke,width=4,**kw):
    return obj_base("line",name,0,0,stroke,points=[float(x1),float(y1),float(x2),float(y2)],
                    stroke=stroke,strokeWidth=float(width),**kw)

def polygon(name,points,fill,stroke=None,sw=0,**kw):
    return obj_base("polygon",name,0,0,fill,points=[[float(x),float(y)] for x,y in points],
                    stroke=stroke,strokeWidth=float(sw),**kw)

def path(name,d,left,top,fill,stroke=None,sw=0,scaleX=1,scaleY=1,angle=0,**kw):
    return obj_base("path",name,left,top,fill,path=d,stroke=stroke,strokeWidth=float(sw),
                    scaleX=float(scaleX),scaleY=float(scaleY),angle=angle,**kw)

def circle(name,x,y,r,fill,stroke=None,sw=0,**kw):
    return obj_base("circle",name,x,y,fill,radius=float(r),stroke=stroke,strokeWidth=float(sw),**kw)

def ellipse(name,x,y,rx,ry,fill,stroke=None,sw=0,**kw):
    return obj_base("ellipse",name,x,y,fill,rx=float(rx),ry=float(ry),stroke=stroke,strokeWidth=float(sw),**kw)


# Original vector path library. These are editable Fabric path objects, not raster artwork.
SVG_PATHS = {
    "star": "M50 0 L61 35 L98 35 L68 57 L79 92 L50 71 L21 92 L32 57 L2 35 L39 35 Z",
    "leaf": "M5 45 C20 5 75 0 95 5 C90 48 55 88 10 92 C30 65 48 45 76 25 C48 38 28 48 5 45 Z",
    "shield": "M50 0 L92 16 L85 62 C80 80 66 92 50 100 C34 92 20 80 15 62 L8 16 Z",
    "hex": "M25 0 L75 0 L100 50 L75 100 L25 100 L0 50 Z",
    "spark": "M50 0 L60 38 L100 50 L60 62 L50 100 L40 62 L0 50 L40 38 Z",
    "wave": "M0 55 C22 10 48 10 72 55 C92 92 118 92 140 55 L140 100 L0 100 Z",
    "mountain": "M0 100 L30 54 L48 74 L72 24 L100 100 Z",
    "bolt": "M58 0 L18 56 L47 56 L34 100 L82 42 L53 42 Z",
    "badge": "M50 0 L62 12 L80 10 L88 28 L100 40 L92 58 L95 78 L76 86 L64 100 L48 92 L30 98 L20 80 L2 70 L10 50 L4 32 L22 20 L34 4 Z",
    "drop": "M50 0 C70 30 90 52 90 70 C90 91 72 108 50 108 C28 108 10 91 10 70 C10 52 30 30 50 0 Z",
}

def add_icon(objs, icon, name, x, y, size, fill, angle=0, opacity=1):
    scale = size / 100.0
    objs.append(path(name, SVG_PATHS[icon], x, y, fill, scaleX=scale, scaleY=scale, angle=angle, opacity=opacity))


def family_decoration(family, idx, w, h, p):
    bg, primary, light, accent = p
    o=[]
    if family=="geometric_sweep":
        o += [
            polygon("geo_a",[(0,0),(w*.42,0),(w*.25,h),(0,h)],primary),
            polygon("geo_b",[(w*.18,0),(w*.62,0),(w*.44,h),(w*.08,h)],accent,opacity=.35),
        ]
    elif family=="diagonal_ribbon":
        o += [
            polygon("diag_a",[(0,h*.15),(w*.70,0),(w,h*.25),(0,h*.58)],primary),
            polygon("diag_b",[(0,h*.67),(w,h*.38),(w,h*.56),(0,h*.88)],accent),
        ]
    elif family=="center_badge":
        o += [circle("badge_outer",w*.41,h*.20,min(w,h)*.16,primary),
              circle("badge_inner",w*.435,h*.235,min(w,h)*.125,light)]
        add_icon(o,"badge","badge_svg",w*.455,h*.255,min(w,h)*.085,accent)
    elif family=="corner_burst":
        for n,(x,y,a) in enumerate([(0,0,0),(w,0,90),(w,h,180),(0,h,270)]):
            add_icon(o,"spark",f"spark_{n}",x-(55 if x else 0),y-(55 if y else 0),110,accent,a,.8)
    elif family=="wave_motion":
        add_icon(o,"wave","wave_1",0,h*.55,w,primary,0,.9)
        add_icon(o,"wave","wave_2",0,h*.68,w,accent,0,.45)
    elif family=="hex_brand":
        for n,(x,y,s) in enumerate([(w*.08,h*.12,.18),(w*.72,h*.10,.14),(w*.68,h*.62,.22)]):
            add_icon(o,"hex",f"hex_{n}",x,y,min(w,h)*s,primary if n!=1 else accent,15*n,.85)
    elif family=="luxury_frame":
        m=min(w,h)*.04
        o += [rect("frame_1",m,m,w-2*m,h-2*m,"rgba(0,0,0,0)",stroke=accent,strokeWidth=max(2,min(w,h)*.007)),
              rect("frame_2",m*1.8,m*1.8,w-3.6*m,h-3.6*m,"rgba(0,0,0,0)",stroke=primary,strokeWidth=max(2,min(w,h)*.003))]
        add_icon(o,"leaf","leaf_l",m*.5,h*.08,min(w,h)*.18,accent,-25,.8)
        add_icon(o,"leaf","leaf_r",w-m*3.5,h*.72,min(w,h)*.18,accent,155,.8)
    elif family=="sport_stripes":
        for n in range(5):
            x=-w*.1+n*w*.22
            o.append(polygon(f"stripe_{n}",[(x,0),(x+w*.11,0),(x+w*.32,h),(x+w*.21,h)],
                             primary if n%2==0 else accent,opacity=.55))
    elif family=="tech_grid":
        step=max(55,int(w/10))
        for x in range(0,int(w)+1,step): o.append(line(f"gx{x}",x,0,x,h,primary,2,opacity=.18))
        for y in range(0,int(h)+1,step): o.append(line(f"gy{y}",0,y,w,y,primary,2,opacity=.18))
        add_icon(o,"bolt","tech_bolt",w*.77,h*.10,min(w,h)*.18,accent,10,.85)
    elif family=="festival_confetti":
        icons=["star","spark","hex","drop"]
        for n in range(10):
            x=(n*137+idx*19)%max(1,int(w-90)); y=(n*83+idx*31)%max(1,int(h-90))
            add_icon(o,icons[n%4],f"conf_{n}",x,y,35+(n%3)*15,accent if n%2 else primary,n*17,.45)
    elif family=="split_angle":
        o += [polygon("split_1",[(0,0),(w*.58,0),(w*.40,h),(0,h)],primary),
              polygon("split_2",[(w*.58,0),(w,0),(w,h),(w*.40,h)],accent,opacity=.82)]
    elif family=="diamond_focus":
        o += [polygon("diamond",[(w*.5,h*.06),(w*.82,h*.5),(w*.5,h*.94),(w*.18,h*.5)],primary,opacity=.75)]
        add_icon(o,"spark","diamond_spark",w*.44,h*.38,min(w,h)*.12,accent)
    elif family=="circle_orbit":
        r=min(w,h)*.13
        for n in range(4):
            o.append(circle(f"orbit_{n}",w*.5-r + math.cos(n*math.pi/2)*r*1.7,
                            h*.5-r + math.sin(n*math.pi/2)*r*1.7,r,primary if n%2==0 else accent,opacity=.28))
    elif family=="minimal_lines":
        o += [line("ml1",w*.08,h*.20,w*.92,h*.20,primary,8),
              line("ml2",w*.08,h*.80,w*.70,h*.80,accent,4),
              rect("mlbar",w*.08,h*.25,w*.025,h*.42,primary)]
    elif family=="shield_mark":
        add_icon(o,"shield","shield",w*.38,h*.16,min(w,h)*.30,primary)
        add_icon(o,"star","shield_star",w*.455,h*.245,min(w,h)*.12,light)
    elif family=="sunburst":
        cx,cy=w*.50,h*.50
        for n in range(12):
            a=2*math.pi*n/12
            x2=cx+math.cos(a)*w*.46; y2=cy+math.sin(a)*h*.46
            o.append(line(f"sun_{n}",cx,cy,x2,y2,accent if n%2 else primary,8,opacity=.4))
        add_icon(o,"spark","sun_core",w*.44,h*.39,min(w,h)*.12,primary)
    elif family=="leaf_arc":
        for n in range(5):
            add_icon(o,"leaf",f"leaf_{n}",w*(.05+n*.11),h*(.05+n*.07),min(w,h)*.12,
                     primary if n%2==0 else accent,-40+n*12,.55)
    elif family=="chevron_stack":
        for n in range(4):
            y=h*(.12+n*.18)
            o.append(polygon(f"chev_{n}",[(w*.08,y),(w*.42,y+h*.10),(w*.08,y+h*.20),
                                         (w*.28,y+h*.10)],primary if n%2==0 else accent,opacity=.7))
    elif family=="block_modern":
        o += [rect("block1",0,0,w*.34,h,primary),rect("block2",w*.34,0,w*.13,h*.44,accent),
              rect("block3",w*.72,h*.62,w*.28,h*.38,accent,opacity=.75)]
    elif family=="spotlight":
        o += [polygon("spot_l",[(0,0),(w*.48,h*.50),(0,h)],primary,opacity=.72),
              polygon("spot_r",[(w,0),(w*.52,h*.50),(w,h)],accent,opacity=.62)]
    return o


def brand_content(w,h,p,idx,variant,wall=False):
    bg, primary, light, accent=p
    size=min(w,h)
    if wall:
        return [
            textbox("brand_kicker",w*.09,h*.16,w*.82,"PROFESSIONAL EVENT BRANDING",max(16,size*.045),accent,700),
            textbox("brand_name",w*.08,h*.29,w*.84,"YOUR COMPANY",max(30,size*.115),light,800),
            textbox("tagline",w*.15,h*.49,w*.70,"YOUR MESSAGE • YOUR EVENT • YOUR BRAND",max(14,size*.040),light,550),
            textbox("contact",w*.18,h*.73,w*.64,"www.yourcompany.com   •   000 000 0000",max(12,size*.032),accent,650),
        ]
    return [
        textbox("top_logo",w*.34,h*.37,w*.32,"YOUR LOGO",max(23,size*.055),light,800),
        textbox("top_company",w*.31,h*.46,w*.38,"COMPANY NAME",max(17,size*.040),light,700),
    ]


def canopy_top_page(family,idx,p,variant,width_in,height_in,label):
    w=LOGICAL_W; h=LOGICAL_W
    bg,primary,light,accent=p
    # Top geometry: four roof triangles meeting in the centre plus editable valances.
    o=[rect("page_bg",0,0,w,h,bg)]
    m=w*.055; val=w*.085; cx=cy=w/2
    o += [
        polygon("roof_top",[(m,m),(w-m,m),(cx,cy)],primary),
        polygon("roof_right",[(w-m,m),(w-m,h-m),(cx,cy)],accent,opacity=.72),
        polygon("roof_bottom",[(w-m,h-m),(m,h-m),(cx,cy)],primary,opacity=.86),
        polygon("roof_left",[(m,h-m),(m,m),(cx,cy)],accent,opacity=.58),
        rect("valance_top",m,0,w-2*m,val,primary),
        rect("valance_bottom",m,h-val,w-2*m,val,primary),
        rect("valance_left",0,m,val,h-2*m,primary),
        rect("valance_right",w-val,m,val,h-2*m,primary),
    ]
    o += family_decoration(family,idx,w,h,p)
    o += brand_content(w,h,p,idx,variant,wall=False)
    # Repeated editable edge branding like the public canopy editor.
    o += [
        textbox("val_top",w*.25,val*.14,w*.50,"YOUR WEBSITE • COMPANY NAME",29,light,700,angle=180),
        textbox("val_bottom",w*.25,h-val*.82,w*.50,"YOUR WEBSITE • COMPANY NAME",29,light,700),
        textbox("val_left",val*.10,h*.25,h*.50,"YOUR LOGO • COMPANY",29,light,700,angle=-90),
        textbox("val_right",w-val*.06,h*.25,h*.50,"YOUR LOGO • COMPANY",29,light,700,angle=90),
    ]
    # Guides are editable but visually light.
    o += [
        line("seam_1",m,m,w-m,h-m,"#EF4444",2,opacity=.55),
        line("seam_2",w-m,m,m,h-m,"#EF4444",2,opacity=.55),
    ]
    return page(label,w,h,width_in,height_in,bg,o)


def wall_page(family,idx,p,variant,width_in,height_in,label,half=False,inside=False):
    w=LOGICAL_W
    h=max(260,round(w*(height_in/width_in)))
    bg,primary,light,accent=p
    # Inside faces intentionally reverse a decorative accent, not the text itself.
    o=[rect("page_bg",0,0,w,h,bg)]
    o += family_decoration(family,idx+(3 if inside else 0),w,h,p)
    # Brand panel / logo zone.
    card_w=w*.34 if not half else w*.30
    card_h=h*.46
    o += [
        rect("brand_panel",w*.08,h*.19,card_w,card_h,light,opacity=.94),
        textbox("panel_logo",w*.11,h*.26,card_w*.82,"YOUR LOGO",max(26,min(w,h)*.11),primary,800),
        textbox("panel_company",w*.11,h*.45,card_w*.82,"COMPANY NAME",max(15,min(w,h)*.055),primary,700),
    ]
    o += brand_content(w,h,p,idx,variant,wall=True)
    if half:
        o.append(rect("half_wall_band",0,h*.82,w,h*.18,primary))
        o.append(textbox("half_wall_band_text",w*.12,h*.855,w*.76,"EVENTS • TRADE SHOWS • PROMOTIONS",
                         max(13,min(w,h)*.04),light,700))
    return page(label,w,h,width_in,height_in,bg,o)


def page(label,w,h,width_in,height_in,bg,objects):
    return {
        "name": label,
        "surfaceKey": label.lower().replace(" ","-"),
        "background": bg,
        "width": int(w),
        "height": int(h),
        "canvas": {"width": int(w), "height": int(h)},
        "physical": {"widthIn": float(width_in), "heightIn": float(height_in), "unit": "in"},
        "safeMarginIn": 2,
        "objects": objects,
    }


def build_pages(product, idx):
    surfaces=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
    if len(surfaces) != 7:
        raise CommandError(
            f"Product {product.id} must have exactly 7 active Admin print surfaces before rebuilding "
            f"these templates. Found {len(surfaces)}."
        )
    p=PALETTES[idx%len(PALETTES)]
    family=FAMILIES[idx//5]
    variant=VARIANTS[idx%5]
    pages=[]
    for pos,s in enumerate(surfaces):
        wi=float(s.print_width_in); hi=float(s.print_height_in)
        if pos==0:
            pages.append(canopy_top_page(family,idx,p,variant,wi,hi,s.label))
        else:
            half=("Half" in s.label)
            inside=("Inside" in s.label)
            pages.append(wall_page(family,idx,p,variant,wi,hi,s.label,half=half,inside=inside))
    return pages, family, variant, p


def esc(v):
    return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def preview_svg(page):
    w=page["width"]; h=page["height"]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">']
    out.append(f'<rect width="{w}" height="{h}" fill="{esc(page.get("background","#fff"))}"/>')
    for o in page["objects"]:
        t=o["type"]; fill=o.get("fill","none"); op=o.get("opacity",1)
        if fill=="rgba(0,0,0,0)": fill="none"
        if t=="rect":
            out.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" '
                       f'fill="{fill}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>')
        elif t=="polygon":
            pts=" ".join(f'{x},{y}' for x,y in o["points"])
            out.append(f'<polygon points="{pts}" fill="{fill}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>')
        elif t=="circle":
            r=o["radius"]; out.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{fill}" opacity="{op}"/>')
        elif t=="ellipse":
            out.append(f'<ellipse cx="{o["left"]+o["rx"]}" cy="{o["top"]+o["ry"]}" rx="{o["rx"]}" ry="{o["ry"]}" fill="{fill}" opacity="{op}"/>')
        elif t=="line":
            x1,y1,x2,y2=o["points"]; out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{o.get("stroke","#111")}" stroke-width="{o.get("strokeWidth",2)}" opacity="{op}"/>')
        elif t=="path":
            transform=f'translate({o["left"]} {o["top"]}) scale({o.get("scaleX",1)} {o.get("scaleY",1)}) rotate({o.get("angle",0)} 50 50)'
            out.append(f'<path d="{esc(o["path"])}" fill="{fill}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" transform="{transform}" opacity="{op}"/>')
        elif t=="textbox":
            x=o["left"]+o.get("width",0)/2
            y=o["top"]+o.get("fontSize",20)
            out.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="{esc(o.get("font","Arial"))}" '
                       f'font-size="{o.get("fontSize",20)}" font-weight="{o.get("fontWeight",600)}" '
                       f'fill="{fill}" opacity="{op}">{esc(o.get("text",""))}</text>')
    out.append("</svg>")
    return "".join(out)


class Command(BaseCommand):
    help = "Build 100 original, fully editable, 7-page 10x10 canopy templates with vector/SVG-style Fabric paths."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=391)
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--replace", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self,*args,**opts):
        try:
            product=Product.objects.get(pk=opts["product_id"])
        except Product.DoesNotExist:
            raise CommandError(f'Product {opts["product_id"]} does not exist.')

        count=max(1,min(int(opts["count"]),100))
        surfaces=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
        if len(surfaces)!=7:
            raise CommandError(
                f"Configure exactly 7 active ProductPrintSurface rows in Admin first. Found {len(surfaces)}."
            )

        self.stdout.write(f"Product: {product.id} {product.name}")
        self.stdout.write("Admin surfaces:")
        for n,s in enumerate(surfaces,1):
            self.stdout.write(f"  {n}. {s.label}: {s.print_width_in} x {s.print_height_in} in")

        if opts["dry_run"]:
            pages,family,variant,pal=build_pages(product,0)
            self.stdout.write(self.style.SUCCESS(
                f"DRY RUN OK: {count} templates, {len(pages)} pages each, first family={family}/{variant}."
            ))
            return

        if opts["replace"]:
            deleted,_=DesignTemplate.objects.filter(
                product=product,
                json_data__generator__in=[GENERATOR,"zenvibe-canopy-7page-v1"]
            ).delete()
            self.stdout.write(f"Removed prior generated canopy records: {deleted}")

        seen=set()
        for idx in range(count):
            pages,family,variant,pal=build_pages(product,idx)
            # Material uniqueness signature: family + variant + object structure counts.
            signature=(family,variant,tuple(len(p["objects"]) for p in pages))
            if signature in seen:
                raise CommandError(f"Duplicate structure generated at index {idx+1}")
            seen.add(signature)

            data={
                "version":2,
                "templateType":"editable-master",
                "reconstructed":True,
                "generator":GENERATOR,
                "designFamily":family,
                "variant":variant,
                "designCode":f"canopy10-v2-{idx+1:03d}",
                "designName":f"{family.replace('_',' ').title()} {variant}",
                "pageCount":7,
                "unit":"in",
                "pages":copy.deepcopy(pages),
                "adminPages":copy.deepcopy(pages),
                "editable":True,
                "editorNative":True,
                "editorSchema":"fabric-primitives-v1",
                "vectorArtwork":True,
                "svgStylePaths":True,
                "source":{
                    "type":"original-editor-native-vector-composition",
                    "note":"Original ZenVibe canopy composition. Artwork is stored as editable Fabric primitives and paths; preview SVG is not the editor master."
                },
            }
            name=f"Canopy 10x10 V2 {idx+1:03d} · {family.replace('_',' ').title()} · {variant}"
            tpl,created=DesignTemplate.objects.update_or_create(
                product=product,name=name,
                defaults={"json_data":data,"is_active":True}
            )
            svg=preview_svg(pages[0]).encode("utf-8")
            tpl.preview.save(f"canopy10_v2_{idx+1:03d}.svg",ContentFile(svg),save=False)
            tpl.save(update_fields=["preview","json_data","is_active","updated_at"])
            self.stdout.write(f"{idx+1:03d}/{count}: {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Created/updated {count} fully editable 7-page canopy templates for product {product.id}."
        ))
