"""Build 100 complete, luxury, industry-specific and editable door-hanger designs.

Each design contains visible typography, thematic vector illustration, an offer,
contact information, and a separate usable back. Preview SVG is rendered from
the EXACT SAME Fabric primitive objects as the editor, never background-only.

20 industry concepts x 5 visibly distinct art directions = 100 compositions.
No remote requests, external stock images, dummy photo backgrounds or changes
to the storefront UI. Keeps all existing template primary keys and saved designs.
Backs up original JSON + preview locations before any changes.

    python manage.py rebuild_doorhanger_luxury_100 --dry-run
    python manage.py rebuild_doorhanger_luxury_100 --apply
    python manage.py rebuild_doorhanger_luxury_100 --product-id 426 --apply
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from datetime import datetime
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product

GENERATOR = "zenvibe-doorhanger-luxury-v6-native"
LEGACY_GENERATORS = {
    GENERATOR,
    "zenvibe-marketing-materials-v1-json-svg",
    "zenvibe-doorhanger-complete-preview-v2",
    "zenvibe-doorhanger-compositions-v3",
    "zenvibe-doorhanger-unique-v4",
    "zenvibe-doorhanger-unique-v5",
}

# brand, headline with intentional breaks, subhead, call-to-action,
# three distinct editable features, thematic icon, accent
THEMES = [
    ("NORTH & CO.", "MAKE ROOM\nFOR MORE", "Elevated business solutions", "LET'S CONNECT",
     ("Thoughtful strategy", "Trusted expertise", "Personal attention"), "business", "#BC8A4A"),
    ("ATELIER HOMES", "FIND YOUR\nPLACE", "Beautiful spaces, better living", "BOOK A VIEWING",
     ("Local property insight", "Tailored home search", "Exceptional service"), "home", "#A47B62"),
    ("TABLE & GRAIN", "GOOD FOOD.\nGREAT MOMENTS.", "Fresh flavours, made daily", "ORDER TODAY",
     ("Seasonal ingredients", "Made with heart", "Always welcoming"), "food", "#B5713D"),
    ("THE WANDER CO.", "THE WORLD\nIS WAITING", "Discover somewhere wonderful", "PLAN YOUR TRIP",
     ("Curated escapes", "Unforgettable stays", "Made for you"), "travel", "#5F8F91"),
    ("SOMA STUDIO", "YOUR MOMENT\nOF CALM", "Wellness with intention", "RESERVE A SESSION",
     ("Restorative rituals", "A gentle approach", "Every detail matters"), "wellness", "#82926A"),
    ("KINCARE", "CARE THAT\nCONNECTS", "Your health, our priority", "BOOK AN APPOINTMENT",
     ("Support you can trust", "Compassionate staff", "Care for every stage"), "health", "#568E95"),
    ("BRIGHTPATH", "LEARN.\nGROW. THRIVE.", "Education for every ambition", "EXPLORE COURSES",
     ("Practical learning", "Skilled educators", "A brighter future"), "education", "#6A81A7"),
    ("CIRCUIT LAB", "THINK\nDIFFERENTLY", "Modern technology, made simple", "START A PROJECT",
     ("Creative solutions", "Smart systems", "Secure by design"), "tech", "#6678A2"),
    ("FORM FITNESS", "MOVE WITH\nPURPOSE", "Your strongest chapter starts here", "JOIN THE STUDIO",
     ("Personal coaching", "A welcoming space", "Progress that lasts"), "fitness", "#BC846A"),
    ("LEDGER & CO.", "BUILD YOUR\nFUTURE", "Clarity for what comes next", "LET'S TALK",
     ("Forward thinking", "Plans built for you", "Clear next steps"), "finance", "#A98B5F"),
    ("GLOW ATELIER", "GLOW FROM\nWITHIN", "Beauty, beautifully considered", "BOOK YOUR VISIT",
     ("Expert treatments", "Modern techniques", "Time for yourself"), "beauty", "#BC788E"),
    ("STONE & STEEL", "BUILT TO\nINSPIRE", "Construction with purpose", "GET A QUOTE",
     ("Quality finishes", "Measured precision", "Trusted workmanship"), "construction", "#A98060"),
    ("SUNDAY INTERIORS", "LIVE MORE\nBEAUTIFULLY", "Interiors that feel like home", "EXPLORE DESIGNS",
     ("Curated materials", "Beautiful details", "Enduring style"), "interior", "#98856B"),
    ("MOTIVE AUTO", "DRIVE INTO\nTHE FUTURE", "Automotive care, refined", "BOOK A SERVICE",
     ("Specialist service", "Uncompromising care", "Made to move"), "automotive", "#608C9A"),
    ("CELEBRATE CO.", "MAKE IT\nMEMORABLE", "Gather, delight, celebrate", "SAVE YOUR DATE",
     ("Thoughtful planning", "Personal touches", "Unforgettable events"), "event", "#A9809D"),
    ("THREAD STUDIO", "STYLE IN\nEVERY DETAIL", "A fresh point of view", "SHOP THE EDIT",
     ("Curated pieces", "Beautiful fabrics", "Style that lasts"), "fashion", "#AB8079"),
    ("FRAME THEORY", "STORIES\nWORTH KEEPING", "Photography with soul", "BOOK YOUR SHOOT",
     ("Candid moments", "Timeless portraits", "Images to treasure"), "photo", "#8B819F"),
    ("CROWN LEGAL", "CONFIDENCE\nIN EVERY STEP", "A considered legal approach", "CONTACT OUR TEAM",
     ("Clear guidance", "Personal advocacy", "Trusted experience"), "legal", "#8C896A"),
    ("SIGNAL STUDIO", "IDEAS THAT\nSTAND OUT", "Design and marketing together", "LET'S CREATE",
     ("Distinctive branding", "Creative thinking", "Measurable impact"), "marketing", "#B07C5B"),
    ("COMMON GROUND", "GOOD THINGS\nGROW HERE", "Creating a stronger community", "GET INVOLVED",
     ("People first", "Local connection", "Shared possibilities"), "community", "#7B9881"),
]
EDITIONS = ("Gallery", "Editorial", "Botanical", "Architectural", "Contemporary")
# Explicitly paired colours; contrast is never guessed from a random palette.
STYLES = [
    {"bg": "#F5EFE6", "ink": "#20353C", "muted": "#52646A", "panel": "#E8DFD1", "light": False},
    {"bg": "#172C32", "ink": "#F7F0E5", "muted": "#DED1C0", "panel": "#24454B", "light": True},
    {"bg": "#F1E7E1", "ink": "#48363F", "muted": "#6C5360", "panel": "#EBD7D7", "light": False},
    {"bg": "#25344C", "ink": "#F9F0DE", "muted": "#DDD6C3", "panel": "#344B68", "light": True},
    {"bg": "#E8EFE9", "ink": "#28413B", "muted": "#50675F", "panel": "#D6E3D9", "light": False},
]


def limited(x):
    return round(float(x), 2)


class Art:
    """Fabric-friendly shapes only; every motif object is individually editable."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.objects = []
        self.serial = 0

    def add(self, kind, name, x, y, w, h, colour, *, editable=True, **extra):
        self.serial += 1
        item = {
            "id": "dh6-%03d" % self.serial,
            "name": name,
            "type": kind,
            "left": limited(x), "top": limited(y),
            "width": limited(w), "height": limited(h),
            "scaleX": 1, "scaleY": 1, "angle": 0,
            "originX": "left", "originY": "top",
            "fill": colour, "opacity": 1,
            "selectable": editable, "evented": editable,
            "customerEditable": editable, "locked": not editable,
        }
        item.update(extra)
        self.objects.append(item)
        return item

    def rect(self, x, y, w, h, fill, name="Editable vector accent", rx=0, editable=True):
        return self.add("rect", name, x, y, w, h, fill,
                        editable=editable, rx=rx, ry=rx)

    def circle(self, cx, cy, r, fill, name="Editable round motif", stroke=None, sw=0):
        return self.add("circle", name, cx-r, cy-r, r*2, r*2, fill,
                        radius=limited(r), stroke=stroke, strokeWidth=sw)

    def ellipse(self, cx, cy, rx, ry, fill, name="Editable organic motif"):
        return self.add("ellipse", name, cx-rx, cy-ry, rx*2, ry*2, fill,
                        rx=limited(rx), ry=limited(ry))

    def text(self, name, value, x, y, w, h, colour, size, *,
             font="Arial", bold=False, align="center", spacing=0):
        if not value.strip():
            raise CommandError("Empty editable text block")
        return self.add("textbox", name, x, y, w, h, colour,
                        text=value, fontFamily=font, font=font,
                        fontSize=limited(size),
                        fontWeight="700" if bold else "400",
                        textAlign=align, lineHeight=1.1,
                        charSpacing=spacing, manualReplacement=True,
                        fieldType="marketing-text")

    def art(self, motif, region, accent, ink, secondary, seed):
        x,y,w,h=region
        def R(ax,ay,aw,ah,fill=accent,tag="Illustrated vector"):
            return self.rect(x+w*ax,y+h*ay,w*aw,h*ah,fill,name=tag,rx=w*.008)
        def C(cx,cy,r,fill=accent,stroke=None,sw=0):
            return self.circle(x+w*cx,y+h*cy,min(w,h)*r,fill,
                               stroke=stroke,sw=sw)
        def E(cx,cy,rx,ry,fill=accent):
            return self.ellipse(x+w*cx,y+h*cy,w*rx,h*ry,fill)
        # No placeholder image frames. These are thematic, layered vector
        # illustrations with individually editable shapes.
        if motif=="business":
            for j,ht in enumerate((.44,.68,.54,.83,.60)):
                R(.12+j*.15,.88-ht,.115,ht,secondary if j%2 else accent)
                R(.145+j*.15,.90-ht,.04,.045,ink)
        elif motif=="home":
            R(.18,.43,.64,.47,secondary)
            R(.29,.56,.16,.23,ink)
            R(.60,.58,.12,.32,ink)
            R(.1,.25,.80,.12,accent)
            E(.5,.27,.36,.07,secondary)
        elif motif=="food":
            C(.52,.51,.29,secondary)
            C(.52,.51,.23,ink)
            C(.52,.51,.19,accent)
            for j in range(4):
                E(.40+.09*j,.49+.05*(j%2),.07,.055,secondary)
            R(.11,.24,.024,.56,accent); R(.84,.24,.024,.56,accent)
        elif motif=="travel":
            E(.50,.52,.40,.33,secondary)
            R(.16,.48,.68,.065,accent)
            R(.41,.15,.17,.67,ink)
            C(.48,.52,.13,accent)
            C(.2,.18,.065,ink); C(.8,.79,.045,ink)
        elif motif=="wellness":
            R(.49,.12,.025,.74,secondary)
            for j in range(5):
                E(.36 if j%2 else .65,.22+j*.125,.15,.075,
                  accent if j%2 else secondary)
            C(.50,.82,.07,ink)
        elif motif=="health":
            C(.5,.48,.32,secondary)
            R(.425,.16,.15,.64,ink)
            R(.22,.40,.56,.16,ink)
            C(.5,.48,.115,accent)
        elif motif=="education":
            R(.15,.27,.32,.51,secondary)
            R(.53,.27,.32,.51,accent)
            R(.485,.22,.028,.60,ink)
            for j in range(4):
                R(.22,.34+j*.10,.20,.012,ink)
                R(.59,.34+j*.10,.20,.012,ink)
        elif motif=="tech":
            C(.5,.51,.25,secondary)
            C(.5,.51,.12,accent)
            for j in range(5):
                R(.10+j*.17,.21,.032,.6,ink if j%2 else accent)
                C(.116+j*.17,.22 if j%2 else .80,.045,secondary)
        elif motif=="fitness":
            R(.12,.47,.76,.08,ink)
            for j in range(2):
                R(.14+j*.58,.33,.08,.36,accent)
                R(.22+j*.42,.39,.08,.24,secondary)
            C(.5,.51,.09,accent)
        elif motif=="finance":
            for j,ht in enumerate((.25,.48,.39,.71,.83)):
                R(.11+j*.17,.89-ht,.125,ht,secondary if j%2 else accent)
            R(.09,.10,.75,.028,ink)
            C(.82,.17,.065,accent)
        elif motif=="beauty":
            R(.25,.39,.52,.47,secondary)
            R(.33,.26,.35,.14,ink)
            R(.43,.15,.16,.10,accent)
            C(.52,.55,.12,accent)
            E(.50,.75,.22,.045,ink)
        elif motif=="construction":
            R(.21,.19,.60,.69,secondary)
            for j in range(3):
                R(.29+j*.18,.28,.11,.48,ink)
            R(.13,.82,.75,.075,accent)
            R(.12,.08,.76,.07,accent)
        elif motif=="interior":
            R(.20,.42,.60,.21,secondary)
            R(.25,.61,.075,.22,ink); R(.68,.61,.075,.22,ink)
            R(.21,.26,.58,.20,accent)
            E(.80,.25,.12,.12,secondary)
        elif motif=="automotive":
            R(.16,.50,.68,.22,secondary)
            R(.29,.36,.44,.18,accent)
            C(.32,.75,.12,ink)
            C(.70,.75,.12,ink)
            C(.32,.75,.055,accent)
            C(.70,.75,.055,accent)
        elif motif=="event":
            for j in range(9):
                ang=j*2.4
                C(.5+.36*math.cos(ang),.49+.34*math.sin(ang),
                  .045 if j%2 else .065,accent if j%3 else secondary)
            C(.5,.48,.22,secondary)
            C(.5,.48,.12,ink)
        elif motif=="fashion":
            R(.40,.20,.20,.12,ink)
            E(.5,.22,.17,.10,accent)
            R(.25,.36,.50,.12,secondary)
            R(.32,.48,.36,.37,accent)
            R(.39,.10,.22,.025,ink)
        elif motif=="photo":
            R(.14,.28,.72,.49,secondary)
            R(.34,.18,.25,.12,ink)
            C(.50,.51,.17,ink)
            C(.50,.51,.10,accent)
            C(.73,.37,.032,accent)
        elif motif=="legal":
            R(.49,.18,.025,.58,accent)
            R(.17,.27,.67,.035,accent)
            for offset in (-.24,.24):
                E(.5+offset,.58,.19,.035,secondary)
                R(.5+offset-.008,.29,.016,.25,ink)
            R(.31,.80,.40,.047,ink)
        elif motif=="marketing":
            R(.16,.28,.68,.47,secondary)
            for j,ht in enumerate((.20,.32,.48,.57)):
                R(.25+j*.14,.64-ht*.4,.085,ht*.4,accent)
            R(.23,.67,.50,.027,ink)
            C(.76,.31,.045,ink)
        else:  # community / people
            C(.50,.50,.17,secondary)
            for j in range(5):
                a=j*2*math.pi/5
                cx=.5+.33*math.cos(a);cy=.5+.29*math.sin(a)
                C(cx,cy,.075,accent)
                E(cx,cy+.09,.08,.10,ink)
            C(.5,.50,.075,ink)
        # Edition-specific typography+ornament signature, never merely a
        # colour swap. Repositioned for each artwork direction.
        for j in range((seed//20)+1):
            C(.16+j*.13,.09,.012,ink)

    def validate(self):
        text=[]
        for o in self.objects:
            x=float(o["left"]); y=float(o["top"])
            w=float(o["width"]); h=float(o["height"])
            if min(x,y,w,h)<0 or x+w>self.w+.2 or y+h>self.h+.2:
                raise CommandError("Artwork object outside door-hanger artboard: "+o["name"])
            if o["type"]=="textbox":
                text.append((x,y,w,h,o["name"]))
                if y<self.h*.255:
                    raise CommandError("Text intrudes into die-cut / knob hole safety region")
        for i,a in enumerate(text):
            for b in text[i+1:]:
                if min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])>1 and (
                    min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1])>1
                ):
                    raise CommandError("Overlapping text blocks: %s / %s"%(a[4],b[4]))
        if len(text)<5 or len(self.objects)<12:
            raise CommandError("Template incomplete: expected visible copy and rich illustration")


def safe_text_size(text, box_width, box_height, preferred):
    # Estimate a conservative text width so both SVG preview and Fabric have
    # room. Explicit newlines are intentional and have separate measuring.
    longest=max(len(line) for line in text.split("\n"))
    lines=len(text.split("\n"))
    return max(9, min(preferred, box_width/(max(1,longest)*.64),
                       box_height/(lines*1.18)))


def page_for(index, side, w, h):
    theme_idx=index%20; edition=index//20
    brand, headline, sub, cta, benefits, motif, accent=THEMES[theme_idx]
    style=STYLES[edition]
    ink=style["ink"]; muted=style["muted"]; paper=style["bg"]
    art=Art(w,h)
    # Locked substrate (not hidden as backgroundAsset, which the product's
    # restricted-print-area editor would drop during loading).
    art.rect(0,0,w,h,paper,"Locked door-hanger substrate",editable=False)
    accent_colour=accent
    foil="#D7B780" if style["light"] else accent
    if edition==0:  # Gallery: headline over illustrated feature
        art.rect(w*.06,h*.260,w*.88,h*.006,foil,"Foil editorial rule")
        hero=(w*.13,h*.46,w*.74,h*.25)
        title_box=(.10,.313,.80,.126)
        sub_y=.745
    elif edition==1:  # Editorial: framed illustration and typographic stack
        art.rect(w*.06,h*.285,w*.88,h*.008,foil)
        art.rect(w*.09,h*.50,w*.82,h*.25,style["panel"])
        hero=(w*.19,h*.505,w*.62,h*.238)
        title_box=(.085,.320,.83,.16)
        sub_y=.777
    elif edition==2:  # Botanical: illustration first; raised typography
        art.rect(w*.09,h*.290,w*.82,h*.005,foil)
        hero=(w*.15,h*.32,w*.70,h*.28)
        title_box=(.085,.625,.83,.133)
        sub_y=.777
    elif edition==3:  # Architectural: strong asymmetric decorative frame
        art.rect(w*.075,h*.33,w*.025,h*.51,foil)
        art.rect(w*.88,h*.33,w*.025,h*.51,foil)
        hero=(w*.16,h*.315,w*.68,h*.277)
        title_box=(.105,.625,.79,.138)
        sub_y=.777
    else:  # Contemporary: colourful layered decorative panels
        art.rect(w*.08,h*.30,w*.84,h*.29,style["panel"])
        art.rect(w*.09,h*.31,w*.05,h*.25,foil)
        hero=(w*.17,h*.335,w*.68,h*.232)
        title_box=(.10,.630,.80,.129)
        sub_y=.780

    if side==1:
        # A distinct complete back page with service detail, benefits,
        # booking CTA, and a smaller matching branded illustration.
        art.objects=art.objects[:1]   # same substrate, different composition
        art.rect(w*.10,h*.30,w*.8,h*.006,foil)
        art.art(motif,(w*.32,h*.334,w*.36,h*.16),
                foil,ink,style["panel"],index)
        art.text("Back eyebrow",brand,w*.1,h*.255,w*.8,h*.034,muted,
                 safe_text_size(brand,w*.8,h*.034,w*.04),bold=True,spacing=60)
        art.text("Back headline","MADE FOR YOU",w*.1,h*.505,w*.8,h*.074,ink,
                 safe_text_size("MADE FOR YOU",w*.8,h*.074,w*.079),
                 bold=True)
        for j,benefit in enumerate(benefits):
            yy=h*(.605+.068*j)
            art.circle(w*.17,yy+h*.014,w*.012,foil,"Editable service bullet")
            art.text("Service benefit %d"%(j+1),benefit,
                     w*.22,yy,w*.67,h*.049,ink,
                     safe_text_size(benefit,w*.67,h*.049,w*.044),
                     bold=j==0,align="left")
        art.rect(w*.105,h*.835,w*.79,h*.07,foil,"Editable call-to-action panel")
        art.text("Back call to action",cta,w*.14,h*.845,w*.72,h*.047,
                 "#172C32" if style["light"] else "#FFFFFF",
                 safe_text_size(cta,w*.72,h*.047,w*.048),bold=True)
        art.text("Contact website","YOURBRAND.COM",w*.10,h*.938,w*.80,h*.035,
                 ink,safe_text_size("YOURBRAND.COM",w*.8,h*.035,w*.032))
    else:
        # Hero motif and copy occupy separate bands. Both have genuinely
        # different placement and artwork for every industry and edition.
        art.art(motif,hero,foil,ink,style["panel"],index)
        art.text("Editable brand",brand,w*.12,h*.268,w*.76,h*.038,ink,
                 safe_text_size(brand,w*.76,h*.038,w*.048),
                 bold=True,spacing=45)
        xx,yy,ww,hh=title_box
        art.text("Editable headline",headline,w*xx,h*yy,w*ww,h*hh,ink,
                 safe_text_size(headline,w*ww,h*hh,w*.095),bold=True)
        art.text("Editable subtitle",sub,w*.10,h*sub_y,w*.80,h*.058,muted,
                 safe_text_size(sub,w*.80,h*.058,w*.042))
        art.rect(w*.105,h*.842,w*.79,h*.067,foil,"Editable offer panel",rx=w*.01)
        art.text("Editable call to action",cta,w*.14,h*.852,w*.72,h*.048,
                 "#172C32" if style["light"] else "#FFFFFF",
                 safe_text_size(cta,w*.72,h*.048,w*.047),bold=True)
        art.text("Editable website","YOURBRAND.COM",w*.12,h*.945,w*.76,h*.034,ink,
                 safe_text_size("YOURBRAND.COM",w*.76,h*.034,w*.030),
                 spacing=30)

    art.validate()
    page={
        "name":"Back" if side else "Front",
        "width":w,"height":h,
        "canvas":{"width":w,"height":h},
        "background":paper,
        "objects":art.objects,
    }
    return page


def svg_preview(page):
    """Raster-free gallery artwork from the exact same source objects."""
    w=page["width"];h=page["height"]
    # Visual preview only: the hole and side slit are illustrative die-cut
    # guides. They are not a production tool path or editable art.
    mask_id="doorhanger-previewer"
    cx=w*.5;cy=h*.132;r=w*.095
    parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'<defs><mask id="{mask_id}"><rect width="{w}" height="{h}" fill="white"/>'
        f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="black"/>'
        f'<rect x="{cx+r*.90:g}" y="{cy-r*.10:g}" '
        f'width="{w-(cx+r*.90):g}" height="{r*.2:g}" fill="black"/>'
        f'</mask></defs><g mask="url(#{mask_id})">'
    ]
    for o in page["objects"]:
        kind=o["type"];x=o["left"];y=o["top"]
        bw=o["width"];bh=o["height"]
        fill=escape(str(o.get("fill") or "none"),quote=True)
        opacity=o.get("opacity",1)
        if kind=="rect":
            parts.append(
                f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" '
                f'rx="{o.get("rx",0)}" fill="{fill}" opacity="{opacity}"/>'
            )
        elif kind=="circle":
            r=o["radius"]
            parts.append(
                f'<circle cx="{x+r:g}" cy="{y+r:g}" r="{r:g}" fill="{fill}" '
                f'opacity="{opacity}" stroke="{o.get("stroke") or "none"}" '
                f'stroke-width="{o.get("strokeWidth",0)}"/>'
            )
        elif kind=="ellipse":
            parts.append(
                f'<ellipse cx="{x+o["rx"]:g}" cy="{y+o["ry"]:g}" '
                f'rx="{o["rx"]}" ry="{o["ry"]}" fill="{fill}" opacity="{opacity}"/>'
            )
        elif kind=="textbox":
            size=o["fontSize"];font=escape(str(o.get("fontFamily","Arial")),quote=True)
            weight=escape(str(o.get("fontWeight","400")),quote=True)
            align=o.get("textAlign","center")
            anchor={"center":"middle","right":"end"}.get(align,"start")
            tx=x+bw/2 if align=="center" else x+bw if align=="right" else x
            line_list=str(o["text"]).split("\n")
            cap=size*1.1
            parts.append(
                f'<text x="{tx:g}" y="{y+size:g}" font-size="{size:g}" '
                f'font-family="{font}" font-weight="{weight}" '
                f'letter-spacing="{float(o.get("charSpacing",0))/1000*size:g}" '
                f'text-anchor="{anchor}" fill="{fill}">'
            )
            for j,line in enumerate(line_list):
                parts.append(
                    f'<tspan x="{tx:g}" dy="{0 if j==0 else cap:g}">'
                    f'{escape(line)}</tspan>'
                )
            parts.append("</text>")
    parts.append("</g></svg>")
    return "".join(parts)


def source_dimensions(product, known):
    # Never guess physical inches. Product editor pixels may come from Admin
    # or the existing 100-template library.
    w=int(product.width or 0)
    h=int(product.height or 0)
    if (w<200 or h<400 or w/h>.75 or w/h<.28) and known:
        data=known[0].json_data
        if isinstance(data,str):
            try:data=json.loads(data)
            except (ValueError,TypeError):data={}
        if not isinstance(data,dict):data={}
        w=int(data.get("width") or 0);h=int(data.get("height") or 0)
    if not (200<=w<=1600 and 400<=h<=3200 and .28<=w/h<=.75):
        raise CommandError("Configure portrait door-hanger editor dimensions before installing")
    return w,h


class Command(BaseCommand):
    help="Rebuild 100 professionally composed, editable front/back door-hanger masters and matching previews."

    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int)
        mode=parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--apply",action="store_true")

    def handle(self,*args,**opts):
        selected=Product.objects.filter(is_active=True,name__icontains="door hanger").order_by("pk")
        if opts["product_id"]:
            selected=selected.filter(pk=opts["product_id"])
        products=list(selected)
        if not products:
            raise CommandError("No active door-hanger product found")
        for product in products:
            self.rebuild_product(product,opts["apply"])

    def rebuild_product(self,product,apply):
        existing=list(DesignTemplate.objects.filter(
            product=product,is_active=True).order_by("pk"))
        known={}
        for t in existing:
            m=re.match(r"^ZV Door Hanger\s+(\d{1,3})\b",t.name)
            if not m:
                continue
            idx=int(m.group(1))-1
            if not 0<=idx<100:
                continue
            data=t.json_data
            if isinstance(data,str):
                try:data=json.loads(data)
                except (ValueError,TypeError):
                    raise CommandError("Malformed existing door-hanger JSON on ID %s"%t.pk)
            if not isinstance(data,dict) or data.get("generator") not in LEGACY_GENERATORS:
                raise CommandError("Existing door-hanger %s is not an approved generated master"%t.pk)
            if idx in known:
                raise CommandError("Duplicate active door-hanger index %s"%idx)
            known[idx]=t
        if existing and len(known)!=len(existing):
            raise CommandError(
                "This product has non-generated templates. Preserve them and review "
                "the gallery before a full library rebuild."
            )
        w,h=source_dimensions(product,list(known.values()))
        surfaces=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
        if len(surfaces)>2:
            raise CommandError("Door hanger has more than two active Admin surfaces; confirm page setup first")
        side_count=len(surfaces) if surfaces else 2
        for surface in surfaces:
            if float(surface.print_width_in or 0)<=0 or float(surface.print_height_in or 0)<=0:
                raise CommandError("Admin door-hanger print surface has invalid inch dimensions")
        built=[]
        footprints=set()
        for idx in range(100):
            pages=[page_for(idx,side,w,h) for side in range(side_count)]
            for side,surface in enumerate(surfaces):
                pages[side]["name"]=surface.label
                pages[side]["physical"]={
                    "widthIn":float(surface.print_width_in),
                    "heightIn":float(surface.print_height_in),
                    "unit":"in",
                }
            signature=hashlib.sha256(json.dumps(
                [
                    (p["name"],[(o["type"],o["left"],o["top"],o["width"],o["height"],
                                  o.get("text"),o.get("radius")) for o in p["objects"]])
                    for p in pages
                ],sort_keys=True).encode("utf-8")).hexdigest()
            if signature in footprints:
                raise CommandError("Repeated design at %03d"%(idx+1))
            footprints.add(signature)
            preview=svg_preview(pages[0])
            theme=THEMES[idx%20][0]
            edition=EDITIONS[idx//20]
            name=f"ZV Door Hanger {idx+1:03d} · {theme} · {edition}"
            master={
                "generator":GENERATOR,"version":6,
                "templateType":"editable-master",
                "editorNative":True,"editable":True,
                "designFamily":theme,"composition":edition,
                "compositionSignature":signature,"pageCount":len(pages),
                "width":w,"height":h,
                "pages":pages,
                "previewComplete":True,
                "adminSurfacePageCount":side_count,
                "cutAreaNote":"Knob-hole and slit on preview are illustrative only; use actual manufacturer dieline for production.",
            }
            built.append((idx,name,master,preview))
        self.stdout.write(self.style.SUCCESS(
            f"Validated 100 distinct, fully illustrated door hangers ({side_count} page(s)) "
            f"for #{product.pk} {product.name}. Existing generated rows: {len(known)}"
        ))
        if not apply:
            self.stdout.write("Dry run finished: no database or media changes")
            return

        backup_dir=Path(settings.BASE_DIR)/"template_backups"
        backup_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup_path=backup_dir/f"doorhanger-{product.pk}-before-v6-{stamp}.jsonl.gz"
        with gzip.open(backup_path,"wt",encoding="utf-8") as archive:
            for item in existing:
                archive.write(json.dumps({
                    "pk":item.pk,"product_id":item.product_id,"name":item.name,
                    "json_data":item.json_data,"preview":item.preview.name if item.preview else "",
                    "is_active":item.is_active
                },ensure_ascii=False,default=str)+"\n")
        # Validate all pages before writes, then preserve every existing PK.
        with transaction.atomic():
            for idx,name,master,preview in built:
                template=known.get(idx) or DesignTemplate(product=product)
                template.name=name
                template.json_data=master
                template.is_active=True
                template.preview.save(
                    f"doorhanger-luxury-v6-{product.pk}-{idx+1:03d}.svg",
                    ContentFile(preview.encode("utf-8")),save=False
                )
                template.save()
        self.stdout.write(self.style.SUCCESS(
            f"Installed 100 complete designs ({side_count} page(s)); source IDs preserved. Backup: {backup_path}"
        ))
