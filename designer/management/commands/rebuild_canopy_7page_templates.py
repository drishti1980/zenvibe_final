from __future__ import annotations

import copy
import hashlib
import json
import math
from html import escape
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product

try:
    import cairosvg
except Exception:
    cairosvg = None


GENERATOR_ID = "zenvibe-canopy-7page-v1"
MEDIA_DIR = "generated_canopy_7page_templates"

# Reference dimensions from the supplied 10x10 combo example:
# 1 x canopy top, 2 x full-wall faces, 4 x half-wall faces.
SURFACES = [
    ("Canopy Top", 120.0, 120.0),
    ("Full Back Wall - Outside", 117.0, 80.0),
    ("Full Back Wall - Inside", 117.0, 80.0),
    ("Left Half Wall - Outside", 117.0, 38.0),
    ("Left Half Wall - Inside", 117.0, 38.0),
    ("Right Half Wall - Outside", 117.0, 38.0),
    ("Right Half Wall - Inside", 117.0, 38.0),
]

PALETTES = [
    ("Emerald Lime", "#073f36", "#1fc29c", "#d9ef55", "#ffffff", "#092e28"),
    ("Navy Gold", "#101b49", "#1d3d91", "#d8aa45", "#ffffff", "#0b1232"),
    ("Black Copper", "#111111", "#2b2b2b", "#c87846", "#ffffff", "#050505"),
    ("Burgundy Rose", "#66172e", "#a32f54", "#e8a9b5", "#ffffff", "#441020"),
    ("Royal Purple", "#3d1b61", "#6d3b96", "#d6bdff", "#ffffff", "#28103f"),
    ("Teal Coral", "#005a61", "#07858c", "#ff776c", "#ffffff", "#003e43"),
    ("Cobalt Citrus", "#1748a2", "#376dcc", "#ffcd3c", "#ffffff", "#0e347c"),
    ("Forest Sand", "#1f513a", "#467b59", "#dbc889", "#ffffff", "#143527"),
    ("Charcoal Cyan", "#20242b", "#333a45", "#26c5d9", "#ffffff", "#11151a"),
    ("Orange Navy", "#e8652d", "#ff8b4a", "#172448", "#ffffff", "#bd481d"),
    ("Magenta Plum", "#9f1e6a", "#d04793", "#41153d", "#ffffff", "#70144c"),
    ("Aqua Midnight", "#11aeb0", "#4ed2ce", "#102044", "#ffffff", "#08777a"),
    ("Red Graphite", "#b92732", "#e34b55", "#292d34", "#ffffff", "#851922"),
    ("Sage Cream", "#52755f", "#82a78d", "#f4e7c8", "#ffffff", "#385142"),
    ("Yellow Onyx", "#f2c52d", "#ffdd62", "#16191f", "#ffffff", "#bb9414"),
    ("Sky Indigo", "#278dcc", "#55b9e8", "#27286c", "#ffffff", "#176695"),
    ("Olive Ivory", "#697533", "#9ba559", "#fff7df", "#ffffff", "#485020"),
    ("Plum Champagne", "#4f244f", "#7b4779", "#d7b36c", "#ffffff", "#351735"),
    ("Petrol Mint", "#005660", "#0b7d84", "#90e2c7", "#ffffff", "#003d44"),
    ("Slate Orange", "#46505b", "#697684", "#f58b42", "#ffffff", "#2d343b"),
]

THEMES = [
    "diagonal", "corner_cut", "center_badge", "split", "ribbon",
    "stripe", "frame", "arc", "chevron", "wave",
    "blocks", "diamond", "sidebars", "spotlight", "monogram",
    "tech", "minimal", "festival", "sport", "luxury",
]

DESIGN_NAMES = [
    f"{theme.replace('_', ' ').title()} {variant}"
    for theme in THEMES
    for variant in ("Prime", "Edge", "Bold", "Studio", "Pro")
]


def canvas_size(width_in: float, height_in: float):
    w = 1200
    h = max(300, round(w * (height_in / width_in)))
    return w, h


def common(name, customer=True):
    return {
        "id": name,
        "name": name.replace("_", " ").title(),
        "customerEditable": customer,
        "selectable": customer,
        "evented": customer,
    }


def rect(name, x, y, w, h, fill, opacity=1, rx=0, angle=0, stroke=None, sw=0, customer=True):
    d = {
        **common(name, customer),
        "type": "rect",
        "left": round(x, 2), "top": round(y, 2),
        "width": round(w, 2), "height": round(h, 2),
        "fill": fill, "opacity": opacity,
        "rx": rx, "ry": rx, "angle": angle,
    }
    if stroke:
        d.update(stroke=stroke, strokeWidth=sw or 2)
    return d


def line(name, x1, y1, x2, y2, stroke, sw=2, opacity=1, customer=True):
    return {
        **common(name, customer),
        "type": "line",
        "left": 0, "top": 0,
        "points": [round(x1,2), round(y1,2), round(x2,2), round(y2,2)],
        "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "fill": None,
    }


def circle(name, cx, cy, r, fill, opacity=1, stroke=None, sw=0, customer=True):
    d = {
        **common(name, customer),
        "type": "circle",
        "left": round(cx-r,2), "top": round(cy-r,2),
        "radius": round(r,2), "fill": fill, "opacity": opacity,
    }
    if stroke:
        d.update(stroke=stroke, strokeWidth=sw or 2)
    return d


def polygon(name, pts, fill, opacity=1, stroke=None, sw=0, customer=True):
    d = {
        **common(name, customer),
        "type": "polygon",
        "left": 0, "top": 0,
        "points": [{"x":round(x,2),"y":round(y,2)} for x,y in pts],
        "fill": fill, "opacity": opacity,
    }
    if stroke:
        d.update(stroke=stroke, strokeWidth=sw or 2)
    return d


def textbox(name, x, y, w, text, fs, fill, weight=600, align="center", font="Montserrat",
            angle=0, customer=True):
    return {
        **common(name, customer),
        "type": "textbox",
        "left": round(x,2), "top": round(y,2),
        "width": round(w,2),
        "text": text,
        "fontSize": fs,
        "fontFamily": font,
        "font": font,
        "fontWeight": weight,
        "fill": fill,
        "textAlign": align,
        "lineHeight": 1.08,
        "angle": angle,
        "splitByGrapheme": False,
    }


def lock_helper(o):
    o["customerEditable"] = False
    o["selectable"] = False
    o["evented"] = False
    o["locked"] = True
    return o


def background_art(theme, variant, w, h, c1, c2, accent, light, dark):
    """Materially different structural artwork, not palette-only variation."""
    o = [lock_helper(rect("background", 0, 0, w, h, c1, customer=False))]
    v = variant

    if theme == "diagonal":
        o += [
            lock_helper(polygon("diag_1", [(0,0),(w*.68,0),(w*.22,h)], c2, .72, customer=False)),
            lock_helper(polygon("diag_2", [(w*.72,0),(w,0),(w,h*.34)], accent, .92, customer=False)),
            lock_helper(polygon("diag_3", [(0,h*.72),(w*.22,h),(0,h)], accent, .92, customer=False)),
        ]
    elif theme == "corner_cut":
        s = .15 + v*.018
        o += [
            lock_helper(polygon("corner_tr", [(w*(1-s),0),(w,0),(w,h*s)], accent, customer=False)),
            lock_helper(polygon("corner_bl", [(0,h*(1-s)),(0,h),(w*s,h)], accent, customer=False)),
            lock_helper(line("cut_top", w*.08,h*.08,w*.55,h*.08, light, 3, .6, False)),
        ]
    elif theme == "center_badge":
        r = min(w,h) * (.18 + v*.012)
        o += [
            lock_helper(circle("badge", w/2,h/2,r,c2,.85,accent,4,False)),
            lock_helper(circle("badge_inner", w/2,h/2,r*.82,"transparent",1,light,2,False)),
        ]
    elif theme == "split":
        split = .32 + v*.045
        o += [
            lock_helper(rect("split_left",0,0,w*split,h,dark,customer=False)),
            lock_helper(polygon("split_angle",[(w*split,0),(w*(split+.14),0),(w*(split-.02),h),(w*split,h)],accent,.9,customer=False)),
        ]
    elif theme == "ribbon":
        yy = h*(.18 + .035*v)
        o += [
            lock_helper(polygon("rib_top",[(0,yy),(w,yy-h*.10),(w,yy+h*.08),(0,yy+h*.18)],accent,.92,customer=False)),
            lock_helper(polygon("rib_bottom",[(0,h-yy),(w,h-yy-h*.08),(w,h-yy+h*.10),(0,h-yy+h*.18)],c2,.75,customer=False)),
        ]
    elif theme == "stripe":
        for n in range(5):
            x = w*(.04+n*.18)
            o.append(lock_helper(rect(f"stripe_{n}",x,0,w*.07,h,accent if n%2==0 else c2,.28,angle=7+v*2,customer=False)))
    elif theme == "frame":
        m = 28+v*7
        o += [
            lock_helper(rect("frame_outer",m,m,w-2*m,h-2*m,"transparent",1,18,0,accent,5,False)),
            lock_helper(rect("frame_inner",m+18,m+18,w-2*(m+18),h-2*(m+18),"transparent",1,14,0,light,2,False)),
        ]
    elif theme == "arc":
        for n in range(4):
            rr = min(w,h)*(.16+n*.07)
            o.append(lock_helper(circle(f"arc_{n}",w*(.12+.04*v),h*.18,rr,"transparent",1,accent,5-n,False)))
    elif theme == "chevron":
        band = h*(.20+.02*v)
        o += [
            lock_helper(polygon("chev_l",[(0,h*.5),(w*.22,h*.5-band),(w*.42,h*.5),(w*.22,h*.5+band)],accent,.72,customer=False)),
            lock_helper(polygon("chev_r",[(w,h*.5),(w*.78,h*.5-band),(w*.58,h*.5),(w*.78,h*.5+band)],c2,.72,customer=False)),
        ]
    elif theme == "wave":
        # Approximate waves with overlapping circles/ellipses supported by Fabric primitives.
        for n in range(5):
            o.append(lock_helper(circle(f"wave_{n}",w*(.12+n*.22),h*(.92-.03*(n%2)),min(w,h)*(.18+.01*v),accent,.16+.03*n,customer=False)))
    elif theme == "blocks":
        for n in range(6):
            bw=w*(.10+.02*((n+v)%3)); bh=h*(.13+.03*((n+v)%2))
            x=(n%3)*w*.34 + w*.03; y=(n//3)*h*.68+h*.06
            o.append(lock_helper(rect(f"block_{n}",x,y,bw,bh,accent if n%2 else c2,.35,12,customer=False)))
    elif theme == "diamond":
        size=min(w,h)*(.24+.015*v)
        o += [
            lock_helper(polygon("diamond_1",[(w/2,h*.08),(w/2+size,h*.32),(w/2,h*.56),(w/2-size,h*.32)],accent,.33,customer=False)),
            lock_helper(polygon("diamond_2",[(w/2,h*.44),(w/2+size*.75,h*.67),(w/2,h*.90),(w/2-size*.75,h*.67)],c2,.26,customer=False)),
        ]
    elif theme == "sidebars":
        sw=w*(.055+.012*v)
        o += [
            lock_helper(rect("bar_l",0,0,sw,h,accent,customer=False)),
            lock_helper(rect("bar_r",w-sw,0,sw,h,accent,customer=False)),
            lock_helper(rect("bar_l2",sw,0,8,h,light,.8,customer=False)),
            lock_helper(rect("bar_r2",w-sw-8,0,8,h,light,.8,customer=False)),
        ]
    elif theme == "spotlight":
        o += [
            lock_helper(polygon("spot_l",[(0,0),(w*.42,0),(w*.58,h),(w*.18,h)],light,.08,customer=False)),
            lock_helper(polygon("spot_r",[(w*.58,0),(w,0),(w*.82,h),(w*.42,h)],accent,.10,customer=False)),
        ]
    elif theme == "monogram":
        r=min(w,h)*(.20+.012*v)
        o += [
            lock_helper(circle("mono_ring",w/2,h*.32,r,"transparent",1,accent,4,False)),
            lock_helper(circle("mono_ring2",w/2,h*.32,r*.82,"transparent",1,light,2,False)),
        ]
    elif theme == "tech":
        for n in range(7):
            yy=h*(.08+n*.13)
            o.append(lock_helper(line(f"tech_{n}",w*.04,yy,w*(.28+.08*((n+v)%5)),yy,accent,2,.55,False)))
            o.append(lock_helper(circle(f"node_{n}",w*(.30+.08*((n+v)%5)),yy,4+v,accent,.85,customer=False)))
    elif theme == "minimal":
        o += [
            lock_helper(line("minimal_top",w*.08,h*.10,w*.92,h*.10,accent,3,.7,False)),
            lock_helper(line("minimal_bottom",w*.08,h*.90,w*.92,h*.90,accent,3,.7,False)),
            lock_helper(rect("minimal_chip",w*.08,h*.10,w*.12,8,accent,customer=False)),
        ]
    elif theme == "festival":
        for n in range(14):
            x=w*(.04+(n*0.071)%0.92); y=h*(.08+((n*7+v*3)%8)*.11)
            o.append(lock_helper(circle(f"dot_{n}",x,y,5+(n+v)%8,accent if n%2 else light,.45,customer=False)))
    elif theme == "sport":
        o += [
            lock_helper(polygon("sport_1",[(0,0),(w*.46,0),(w*.22,h)],c2,.82,customer=False)),
            lock_helper(polygon("sport_2",[(w*.62,0),(w*.78,0),(w*.54,h),(w*.38,h)],accent,.65,customer=False)),
            lock_helper(line("sport_rule",w*.08,h*.82,w*.92,h*.82,light,4,.55,False)),
        ]
    else:  # luxury
        m=34+v*5
        o += [
            lock_helper(rect("lux_frame",m,m,w-2*m,h-2*m,"transparent",1,20,0,accent,3,False)),
            lock_helper(line("lux_top",w*.28,h*.11,w*.72,h*.11,accent,2,.75,False)),
            lock_helper(line("lux_bottom",w*.28,h*.89,w*.72,h*.89,accent,2,.75,False)),
            lock_helper(circle("lux_dot",w/2,h*.11,5,accent,1,customer=False)),
        ]
    return o


def brand_copy(theme, variant, w, h, c1, c2, accent, light, dark, compact=False):
    """Editable brand fields placed differently by layout family."""
    v=variant
    o=[]

    if compact:
        fs1=max(38, round(h*.14))
        fs2=max(24, round(h*.085))
        fs3=max(18, round(h*.055))
        if theme in ("split","sidebars"):
            x=w*.20; box=w*.60
        else:
            x=w*.15; box=w*.70
        o += [
            textbox("logo_text",x,h*.17,box,"LOGO",fs2,light,800),
            textbox("company_name",x,h*.37,box,"COMPANY NAME",fs1,light,800),
            textbox("message",x,h*.62,box,"MESSAGE HERE",fs2,light,650),
        ]
        return o

    if theme in ("split","sidebars"):
        x=w*.30 if theme=="split" else w*.16
        box=w*.62 if theme=="split" else w*.68
        align="left" if theme=="split" else "center"
    elif theme in ("diagonal","sport"):
        x=w*.14; box=w*.72; align="center"
    elif theme in ("corner_cut","frame","minimal","luxury","arc","monogram"):
        x=w*.15; box=w*.70; align="center"
    else:
        x=w*.12; box=w*.76; align="center"

    fs_title=max(46, round(h*.075))
    fs_company=max(34, round(h*.055))
    fs_body=max(24, round(h*.036))

    if theme=="monogram":
        o.append(textbox("monogram",w*.40,h*.17,w*.20,"ZV",fs_title*1.1,accent,800))
        top=.40
    else:
        o.append(textbox("logo_text",x,h*.20,box,"LOGO",fs_company,accent if theme=="minimal" else light,800,align))
        top=.31

    o += [
        textbox("company_name",x,h*top,box,"COMPANY NAME",fs_title,light,800,align),
        textbox("message",x,h*(top+.18),box,"MESSAGE HERE",fs_company,light,650,align),
        textbox("website",x,h*(top+.36),box,"PHONE / WEBSITE",fs_body,accent if theme!="corner_cut" else light,600,align),
    ]
    return o


def build_top_page(theme, variant, palette, idx):
    """120 x 120 inch canopy top with four coordinated roof/valance faces."""
    width_in,height_in=SURFACES[0][1],SURFACES[0][2]
    w,h=canvas_size(width_in,height_in)
    _,c1,c2,accent,light,dark=palette
    o=background_art(theme,variant,w,h,c1,c2,accent,light,dark)

    # Four roof divisions meet at centre; decorative, not red production guides.
    guide=accent
    o += [
        lock_helper(line("roof_diag_1",0,0,w,h,guide,2,.28,False)),
        lock_helper(line("roof_diag_2",w,0,0,h,guide,2,.28,False)),
    ]

    # Editable logo/company on all four visible roof directions.
    box=w*.50
    center=w/2
    fs=42+variant*2
    o += [
        textbox("top_brand",w*.25,h*.11,box,"LOGO\nCOMPANY NAME",fs,light,800,"center"),
        textbox("bottom_brand",w*.25,h*.77,box,"LOGO\nCOMPANY NAME",fs,light,800,"center",180),
        textbox("left_brand",w*.02,h*.31,box,"LOGO\nCOMPANY NAME",fs,light,800,"center",90),
        textbox("right_brand",w*.48,h*.31,box,"LOGO\nCOMPANY NAME",fs,light,800,"center",-90),
        textbox("top_valance",w*.27,h*.02,w*.46,"PHONE / WEBSITE",26,light,600,"center"),
        textbox("bottom_valance",w*.27,h*.94,w*.46,"PHONE / WEBSITE",26,light,600,"center",180),
        textbox("left_valance",-w*.16,h*.47,w*.40,"PHONE / WEBSITE",26,light,600,"center",90),
        textbox("right_valance",w*.76,h*.47,w*.40,"PHONE / WEBSITE",26,light,600,"center",-90),
    ]

    return {
        "name":"Canopy Top",
        "surfaceKey":"canopy-top",
        "background":c1,
        "width":w,"height":h,
        "canvas":{"width":w,"height":h},
        "physical":{"widthIn":width_in,"heightIn":height_in,"unit":"in"},
        "safeMarginIn":2,
        "objects":o,
    }


def build_wall_page(surface_index, theme, variant, palette, idx):
    name,width_in,height_in=SURFACES[surface_index]
    w,h=canvas_size(width_in,height_in)
    _,c1,c2,accent,light,dark=palette

    # Mirror/shift alternate physical faces without flattening them.
    page_variant=(variant+surface_index)%5
    page_theme=THEMES[(THEMES.index(theme)+surface_index*3)%len(THEMES)]
    o=background_art(page_theme,page_variant,w,h,c1,c2,accent,light,dark)
    compact=height_in <= 40
    o += brand_copy(page_theme,page_variant,w,h,c1,c2,accent,light,dark,compact=compact)

    return {
        "name":name,
        "surfaceKey":name.lower().replace(" ","-").replace("/","-"),
        "background":c1,
        "width":w,"height":h,
        "canvas":{"width":w,"height":h},
        "physical":{"widthIn":width_in,"heightIn":height_in,"unit":"in"},
        "safeMarginIn":2,
        "objects":o,
    }


def structural_signature(pages):
    rows=[]
    for p in pages:
        row=[]
        for o in p["objects"]:
            row.append({
                "type":o.get("type"),
                "left":round(float(o.get("left",0)),1),
                "top":round(float(o.get("top",0)),1),
                "width":round(float(o.get("width",0) or 0),1),
                "height":round(float(o.get("height",0) or 0),1),
                "radius":round(float(o.get("radius",0) or 0),1),
                "angle":round(float(o.get("angle",0) or 0),1),
                "points":o.get("points") if o.get("type") in ("line","polygon") else None,
                "fontSize":o.get("fontSize"),
            })
        rows.append({"surface":p["name"],"objects":row})
    return hashlib.sha256(json.dumps(rows,sort_keys=True,default=str).encode()).hexdigest()


def object_to_svg(o):
    t=o.get("type")
    op=o.get("opacity",1)
    fill=o.get("fill","none")
    if fill in (None,"transparent"): fill="none"
    stroke=o.get("stroke","none")
    sw=o.get("strokeWidth",0)
    angle=o.get("angle",0)
    if t=="rect":
        x=o.get("left",0); y=o.get("top",0)
        return f'<rect x="{x}" y="{y}" width="{o.get("width",0)}" height="{o.get("height",0)}" rx="{o.get("rx",0)}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" transform="rotate({angle} {x} {y})"/>'
    if t=="circle":
        r=o.get("radius",0); cx=o.get("left",0)+r; cy=o.get("top",0)+r
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>'
    if t=="line":
        x1,y1,x2,y2=o.get("points",[0,0,0,0])
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" stroke-opacity="{op}"/>'
    if t=="polygon":
        pts=" ".join(f'{p["x"]},{p["y"]}' for p in o.get("points",[]))
        return f'<polygon points="{pts}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>'
    if t=="textbox":
        x=o.get("left",0); y=o.get("top",0); width=o.get("width",0)
        fs=o.get("fontSize",24); family=escape(str(o.get("fontFamily","Arial")))
        weight=o.get("fontWeight",400); align=o.get("textAlign","left")
        anchor={"center":"middle","right":"end"}.get(align,"start")
        tx=x+(width/2 if anchor=="middle" else width if anchor=="end" else 0)
        lines=str(o.get("text","")).split("\n")
        tspans=[]
        for n,s in enumerate(lines):
            dy=0 if n==0 else fs*1.10
            tspans.append(f'<tspan x="{tx}" dy="{dy}">{escape(s)}</tspan>')
        transform=f' transform="rotate({angle} {tx} {y+fs})"' if angle else ""
        return f'<text x="{tx}" y="{y+fs}" text-anchor="{anchor}" font-family="{family}" font-size="{fs}" font-weight="{weight}" fill="{fill}" fill-opacity="{op}"{transform}>{"".join(tspans)}</text>'
    return ""


def page_svg(page):
    w=page["width"]; h=page["height"]
    body="".join(object_to_svg(o) for o in page["objects"])
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


def build_template(product, idx):
    theme=THEMES[idx//5]
    variant=idx%5
    palette=PALETTES[(idx*7 + variant)%len(PALETTES)]

    pages=[build_top_page(theme,variant,palette,idx)]
    for surface_index in range(1,7):
        pages.append(build_wall_page(surface_index,theme,variant,palette,idx))

    design_name=DESIGN_NAMES[idx]
    data={
        "version":1,
        "templateType":"editable-master",
        "generator":GENERATOR_ID,
        "designFamily":"canopy-10x10-combo",
        "designName":design_name,
        "designCode":f"canopy7-{idx+1:03d}",
        "pageCount":7,
        "unit":"in",
        "document":{
            "profile":"canopy-10x10-combo",
            "unit":"in",
            "width":pages[0]["width"],
            "height":pages[0]["height"],
            "physical":{"widthIn":120.0,"heightIn":120.0},
        },
        "pages":copy.deepcopy(pages),
        "adminPages":copy.deepcopy(pages),
        "editable":True,
        "editorNative":True,
        "editorSchema":"fabric-primitives-v1",
        "surfaceDimensions":[
            {"name":p["name"],"widthIn":p["physical"]["widthIn"],"heightIn":p["physical"]["heightIn"]}
            for p in pages
        ],
        "source":{
            "type":"original-reference-informed-vector-composition",
            "note":"Seven-page editable canopy composition. Reference-informed geometry; no flattened customer artwork.",
        },
    }
    name=f"Canopy 7-Page {idx+1:03d} · {design_name}"
    return name,data,pages


class Command(BaseCommand):
    help="Rebuild 100 editable 7-page 10x10 canopy templates."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int)
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--replace", action="store_true",
                            help="Delete existing templates for this product before importing.")

    def _product(self, product_id):
        if product_id:
            try:
                return Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                raise CommandError(f"Product {product_id} not found")

        # Current project audit identified the 10x10 canopy product as ID 197.
        candidate=Product.objects.filter(pk=197).first()
        if candidate:
            return candidate

        candidate = (
            Product.objects
            .filter(name__icontains="10x10")
            .filter(name__icontains="canopy")
            .first()
        )
        if candidate:
            return candidate

        raise CommandError("Canopy product not found. Run with --product-id <ID>.")

    @transaction.atomic
    def handle(self,*args,**opts):
        count=max(1,min(100,int(opts["count"])))
        product=self._product(opts.get("product_id"))
        dry=opts["dry_run"]

        built=[]
        seen=set()
        for idx in range(count):
            name,data,pages=build_template(product,idx)
            sig=structural_signature(pages)
            if sig in seen:
                raise CommandError(f"Structural duplicate detected: {name}")
            seen.add(sig)
            built.append((name,data,pages))
            self.stdout.write(f"{'DRY RUN ' if dry else ''}{idx+1:03d}: {name} · 7 pages")

        if dry:
            self.stdout.write(self.style.SUCCESS(
                f"Validated {len(built)} structurally unique canopy templates; database unchanged."
            ))
            return

        if opts["replace"]:
            existing=DesignTemplate.objects.filter(product=product)
            n=existing.count()
            existing.delete()
            self.stdout.write(f"Deleted {n} existing templates for product {product.pk}.")

        media_root=Path(getattr(__import__("django.conf").conf.settings,"MEDIA_ROOT","media"))
        base=media_root/MEDIA_DIR/str(product.pk)
        base.mkdir(parents=True,exist_ok=True)

        for idx,(name,data,pages) in enumerate(built):
            svg_files=[]
            for pno,page in enumerate(pages,1):
                svg=page_svg(page)
                fn=f"canopy_{idx+1:03d}_page_{pno}.svg"
                (base/fn).write_text(svg,encoding="utf-8")
                svg_files.append(f"{MEDIA_DIR}/{product.pk}/{fn}")
            data["svgFiles"]=svg_files

            obj,_=DesignTemplate.objects.update_or_create(
                product=product,
                name=name,
                defaults={"json_data":data,"is_active":True},
            )

            preview_svg=page_svg(pages[0])
            preview_bytes=None
            if cairosvg is not None:
                try:
                    preview_bytes=cairosvg.svg2png(
                        bytestring=preview_svg.encode("utf-8"),
                        output_width=700,
                        output_height=700,
                    )
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(
                        f"PNG preview failed for {name}; using SVG: {exc}"
                    ))

            if preview_bytes:
                obj.preview.save(
                    f"canopy7_{idx+1:03d}.png",
                    ContentFile(preview_bytes),
                    save=True,
                )
            else:
                obj.preview.save(
                    f"canopy7_{idx+1:03d}.svg",
                    ContentFile(preview_svg.encode("utf-8")),
                    save=True,
                )

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(built)} editable 7-page canopy templates for "
            f"product {product.pk}: {product.name}"
        ))
