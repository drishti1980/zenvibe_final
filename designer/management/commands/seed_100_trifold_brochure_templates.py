from __future__ import annotations

import base64
import copy
import hashlib
import json
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


GENERATOR_ID = "zenvibe-trifold-brochure-v1-json-svg"
VERSION = 1
MEDIA_DIR = "generated_trifold_brochures_v1"
DEFAULT_W, DEFAULT_H = 1100, 850

CATEGORIES = [
    ("Restaurant","FRESH FLAVOURS","Seasonal food made with care","Fresh ingredients, generous portions and memorable flavours.","BOOK A TABLE","123 ANYWHERE ST · (03) 9000 1234","zenvibe.example/menu"),
    ("Corporate","BUILD WHAT'S NEXT","Strategy · Design · Growth","We turn complex ideas into clear, practical and measurable outcomes.","LET'S TALK","MELBOURNE · SYDNEY · GEELONG","zenvibe.example/business"),
    ("Real Estate","YOUR NEXT HOME","Premium property presentation","Modern finishes, generous spaces and an exceptional location.","BOOK AN INSPECTION","PROPERTY GROUP · 0400 123 456","zenvibe.example/property"),
    ("Travel","EXPLORE MORE","Journeys designed around you","Curated escapes, local experiences and flexible itineraries.","START YOUR JOURNEY","TRAVEL STUDIO · AUSTRALIA","zenvibe.example/travel"),
    ("Spa","TIME TO RESET","Wellness for body and mind","Restorative treatments, thoughtful rituals and personalised care.","BOOK YOUR VISIT","WELLNESS STUDIO · 10AM–7PM","zenvibe.example/spa"),
    ("Healthcare","CARE YOU CAN TRUST","Modern healthcare, personal attention","Accessible, compassionate care focused on long-term wellbeing.","MAKE AN APPOINTMENT","HEALTH CLINIC · (03) 9000 2255","zenvibe.example/health"),
    ("Construction","BUILT WITH PURPOSE","Planning · Building · Delivery","Reliable delivery, quality workmanship and clear communication.","REQUEST A QUOTE","LICENSED & INSURED","zenvibe.example/build"),
    ("Education","LEARN. GROW. ACHIEVE.","Education that opens possibilities","Practical programs, supportive educators and flexible pathways.","ENROL TODAY","CAMPUS · 1300 000 111","zenvibe.example/learn"),
    ("Technology","SMARTER DIGITAL","Technology that moves business forward","Secure, scalable solutions that simplify operations and support growth.","DISCOVER SOLUTIONS","DIGITAL STUDIO · AUSTRALIA","zenvibe.example/tech"),
    ("Fitness","STRONGER EVERY DAY","Train with purpose","Expert coaching, progressive programs and a supportive community.","START TODAY","FITNESS CLUB · OPEN 7 DAYS","zenvibe.example/fitness"),
    ("Finance","PLAN WITH CONFIDENCE","Clear advice for your next move","Practical financial guidance designed around your goals.","BOOK A CONSULTATION","ADVISORY GROUP · 1300 222 111","zenvibe.example/finance"),
    ("Beauty","BEAUTY, REFINED","Treatments made personal","Modern technique, premium products and a relaxed client experience.","RESERVE YOUR TIME","BEAUTY STUDIO · GEELONG","zenvibe.example/beauty"),
    ("Nonprofit","MAKE AN IMPACT","Small actions. Lasting change.","Create practical support, stronger connections and better outcomes.","GET INVOLVED","COMMUNITY FOUNDATION","zenvibe.example/give"),
    ("Interior","SPACES WITH SOUL","Interiors shaped around living","Warm, functional spaces created through thoughtful planning and detail.","VIEW OUR WORK","INTERIOR STUDIO · MELBOURNE","zenvibe.example/interiors"),
    ("Automotive","DRIVE WITH CONFIDENCE","Service you can depend on","Professional automotive care, transparent advice and dependable workmanship.","BOOK A SERVICE","AUTO CARE · (03) 9000 7788","zenvibe.example/auto"),
    ("Events","MAKE IT MEMORABLE","Events designed to connect","Polished experiences with personality, from intimate to large-scale.","PLAN YOUR EVENT","EVENT STUDIO · AUSTRALIA","zenvibe.example/events"),
    ("Fashion","NEW SEASON","Designed for everyday confidence","Modern essentials, expressive details and versatile silhouettes.","SHOP THE COLLECTION","ONLINE + IN STORE","zenvibe.example/style"),
    ("Photography","STORIES IN FOCUS","Natural moments, beautifully captured","Relaxed photography for people, brands and celebrations.","BOOK A SESSION","PHOTO STUDIO · 0400 555 222","zenvibe.example/photo"),
    ("Legal","CLEAR. PRACTICAL. TRUSTED.","Advice when it matters","Straightforward legal guidance with attention to priorities and next steps.","SPEAK WITH US","LEGAL GROUP · (03) 9000 4411","zenvibe.example/legal"),
    ("Marketing","MAKE YOUR BRAND MOVE","Creative that earns attention","Brand, content and campaign thinking built for stronger connections.","START A PROJECT","CREATIVE AGENCY · MELBOURNE","zenvibe.example/agency"),
]

PALETTES = [
    ("Forest Cream","#0d6b43","#f7f0d7","#17372c","#ffffff","#d8ad57"),
    ("Navy Coral","#16365f","#f3efe7","#ef6b61","#ffffff","#9fc4d8"),
    ("Terracotta","#a54e38","#fbf3e8","#27352e","#ffffff","#dfad72"),
    ("Cobalt","#1f4fa3","#f5f7f8","#10294f","#ffffff","#efb74c"),
    ("Plum Blush","#633c63","#f8e9e7","#35263c","#ffffff","#c997a6"),
    ("Teal Sand","#176b70","#f4ead7","#173c40","#ffffff","#d4a95f"),
    ("Charcoal Lime","#24282d","#f6f3e9","#a8c95f","#ffffff","#7d8d93"),
    ("Burgundy","#762c3b","#fbf4ec","#39242a","#ffffff","#caa05e"),
    ("Azure","#277da1","#f2f8fa","#183b52","#ffffff","#f2b35d"),
    ("Olive","#657348","#f7f0df","#303728","#ffffff","#c99954"),
    ("Black Gold","#171717","#f6f0e4","#b89452","#ffffff","#777777"),
    ("Rose Navy","#b85b6b","#fff3f1","#24334d","#ffffff","#e6b6a6"),
    ("Aqua Orange","#087f8c","#f7f7f0","#f28f3b","#ffffff","#174f56"),
    ("Indigo Mint","#3d3b8e","#f3f5ff","#77cbb9","#ffffff","#25244e"),
    ("Brick Blue","#9a3e32","#f7eee5","#305b78","#ffffff","#d5a85c"),
    ("Emerald Pink","#12664f","#fff1f3","#db6680","#ffffff","#e2b25f"),
    ("Slate Yellow","#425466","#f7f4e9","#f4c95d","#ffffff","#203040"),
    ("Violet","#68478d","#faf5ff","#dc9e82","#ffffff","#352447"),
    ("Ocean","#005f73","#eef8f7","#0a9396","#ffffff","#ee9b00"),
    ("Red Cream","#b62d2d","#fff7ec","#3a2924","#ffffff","#e2b96f"),
]

FONTS = [
    ("Montserrat","DM Sans"),("Playfair Display","Montserrat"),
    ("DM Serif Display","DM Sans"),("Libre Baskerville","Montserrat"),
    ("Georgia","Arial"),
]


def data_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def tb(i,x,y,w,text,size,fill,font="Montserrat",weight=400,align="left",lh=1.15,spacing=0):
    return {
        "id":i,"name":i.replace("_"," ").title(),"type":"textbox",
        "left":round(x,2),"top":round(y,2),"width":round(w,2),
        "text":text,"fontSize":size,"font":font,"fontFamily":font,
        "fontWeight":weight,"fill":fill,"textAlign":align,
        "lineHeight":lh,"charSpacing":spacing,
        "customerEditable":True,"locked":False,
        "fieldType":"brochure-text","manualReplacement":True,
    }


def image(i,x,y,w,h,src,editable=True,background=False):
    return {
        "id":i,"name":i.replace("_"," ").title(),"type":"image",
        "left":round(x,2),"top":round(y,2),"width":round(w,2),"height":round(h,2),
        "src":src,"baseSrc":src,"scaleX":1,"scaleY":1,
        "customerEditable":bool(editable),"backgroundAsset":bool(background),
        "locked":bool(background),
        "fieldType":"brochure-background" if background else "brochure-photo",
        "manualReplacement":not background,
    }


def photo_placeholder(w,h,label,primary,variant):
    x=(variant*37)%100
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<rect width="100%" height="100%" fill="#e3e8e7"/>
<circle cx="{w*(.20+x/300):.1f}" cy="{h*.30:.1f}" r="{min(w,h)*.15:.1f}" fill="{primary}" opacity=".18"/>
<path d="M0 {h*.82:.1f} L{w*.28:.1f} {h*.50:.1f} L{w*.52:.1f} {h*.70:.1f} L{w*.76:.1f} {h*.38:.1f} L{w} {h*.70:.1f} V{h} H0Z" fill="{primary}" opacity=".24"/>
<rect x="2" y="2" width="{max(1,w-4)}" height="{max(1,h-4)}" fill="none" stroke="#ffffff" stroke-width="4"/>
<text x="{w/2:.1f}" y="{h*.91:.1f}" text-anchor="middle" font-family="Arial" font-size="{max(12,min(w,h)*.055):.1f}" fill="{primary}">{escape(label)}</text>
</svg>'''


def background_svg(W,H,palette,family,side,idx):
    primary,paper,dark,white,accent=palette[1:]
    p=W/3
    m=family%20
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="{paper}"/>']

    # 20 macro compositions. The five variations of each family receive
    # different content/category/photo/text geometry, producing 100 templates.
    if m==0:
        s += [f'<rect width="{p}" height="{H}" fill="{primary}"/>',f'<rect x="{p}" width="{p}" height="{H*.22}" fill="{primary}"/>']
    elif m==1:
        s += [f'<rect width="{W}" height="{H*.18}" fill="{dark}"/>',f'<rect x="{2*p}" width="{p}" height="{H}" fill="{primary}"/>']
    elif m==2:
        s += [f'<path d="M0 0 H{W} V{H*.22} L0 {H*.52}Z" fill="{primary}"/>',f'<path d="M0 {H} V{H*.78} L{W} {H*.48} V{H}Z" fill="{dark}"/>']
    elif m==3:
        s += [f'<rect width="{W}" height="{H}" fill="{dark}"/>'] + [f'<rect x="{k*p+p*.1}" y="{H*.08}" width="{p*.8}" height="{H*.84}" rx="20" fill="{paper}"/>' for k in range(3)]
    elif m==4:
        s += [f'<rect width="{p*1.35}" height="{H}" fill="{primary}"/>',f'<path d="M{p*.95} 0 H{p*1.55} L{p*1.15} {H} H{p*.55}Z" fill="{accent}" opacity=".85"/>']
    elif m==5:
        s += [f'<rect x="{p}" width="{p}" height="{H}" fill="{primary}"/>',f'<circle cx="{p*2.55}" cy="{H*.22}" r="{H*.25}" fill="{accent}" opacity=".22"/>']
    elif m==6:
        s += [f'<path d="M0 0 H{W} V{H*.36} Q{W*.52} {H*.56} 0 {H*.40}Z" fill="{primary}"/>',f'<rect y="{H*.88}" width="{W}" height="{H*.12}" fill="{dark}"/>']
    elif m==7:
        for k in range(8):
            x=k*W/8
            s.append(f'<path d="M{x} 0 L{x+W/16} 0 L{x-W/8+W/16} {H} L{x-W/8} {H}Z" fill="{primary if k%2==0 else accent}" opacity=".10"/>')
        s.append(f'<rect x="{2*p}" width="{p}" height="{H}" fill="{primary}"/>')
    elif m==8:
        s += [f'<rect width="{W}" height="{H}" fill="{primary}"/>',f'<path d="M0 {H*.18} Q{W*.5} {H*.02} {W} {H*.18} V{H} H0Z" fill="{paper}"/>']
    elif m==9:
        s += [f'<rect width="{p}" height="{H*.32}" fill="{primary}"/>',f'<rect x="{p}" y="{H*.68}" width="{p}" height="{H*.32}" fill="{dark}"/>',f'<rect x="{2*p}" width="{p}" height="{H*.32}" fill="{accent}"/>']
    elif m==10:
        s += [f'<rect x="{W*.06}" y="{H*.07}" width="{W*.88}" height="{H*.86}" fill="none" stroke="{primary}" stroke-width="4"/>',f'<rect x="{W*.075}" y="{H*.085}" width="{W*.85}" height="{H*.83}" fill="none" stroke="{accent}"/>']
    elif m==11:
        s += [f'<path d="M0 0 H{p*1.4} L{p*.7} {H} H0Z" fill="{primary}"/>',f'<path d="M{W} 0 H{p*2.3} L{p*2.75} {H} H{W}Z" fill="{dark}"/>']
    elif m==12:
        s += [f'<circle cx="{W*.5}" cy="{H*.5}" r="{H*.62}" fill="{primary}" opacity=".08"/>',f'<circle cx="{W*.5}" cy="{H*.5}" r="{H*.43}" fill="none" stroke="{accent}" stroke-width="4" opacity=".45"/>']
    elif m==13:
        s += [f'<rect width="{W}" height="{H*.12}" fill="{primary}"/>',f'<rect y="{H*.88}" width="{W}" height="{H*.12}" fill="{primary}"/>',f'<rect x="{p*.92}" width="{p*.16}" height="{H}" fill="{accent}" opacity=".35"/>']
    elif m==14:
        s += [f'<path d="M0 0 H{W} V{H*.5} C{W*.72} {H*.30} {W*.35} {H*.72} 0 {H*.48}Z" fill="{primary}"/>']
    elif m==15:
        s += [f'<rect width="{W}" height="{H}" fill="{dark}"/>',f'<path d="M0 0 H{W*.72} L{W*.55} {H} H0Z" fill="{paper}"/>',f'<path d="M{W*.62} 0 H{W*.75} L{W*.58} {H} H{W*.45}Z" fill="{accent}"/>']
    elif m==16:
        for k in range(6):
            s.append(f'<circle cx="{W*(.08+k*.18):.1f}" cy="{H*(.12+(k%2)*.68):.1f}" r="{H*.12:.1f}" fill="{primary}" opacity=".08"/>')
        s.append(f'<rect x="{2*p}" width="{p}" height="{H}" fill="{primary}"/>')
    elif m==17:
        s += [f'<path d="M0 {H*.72} L{W*.32} {H*.38} L{W*.58} {H*.62} L{W} {H*.20} V{H} H0Z" fill="{primary}" opacity=".94"/>']
    elif m==18:
        s += [f'<rect width="{p*.18}" height="{H}" fill="{primary}"/>',f'<rect x="{p}" width="{p*.18}" height="{H}" fill="{accent}"/>',f'<rect x="{2*p}" width="{p*.18}" height="{H}" fill="{dark}"/>']
    else:
        s += [f'<rect width="{W}" height="{H}" fill="{primary}"/>',f'<rect x="{W*.04}" y="{H*.05}" width="{W*.92}" height="{H*.90}" rx="32" fill="{paper}"/>',f'<path d="M{W*.04} {H*.72} Q{W*.35} {H*.52} {W*.58} {H*.74} T{W*.96} {H*.68} V{H*.95} H{W*.04}Z" fill="{accent}" opacity=".38"/>']

    if (idx+side)%3==0:
        for q in range(5):
            s.append(f'<circle cx="{W*(.08+q*.205):.1f}" cy="{H*(.10+((q+idx)%3)*.055):.1f}" r="{6+q*2}" fill="{accent}" opacity=".45"/>')
    s.append("</svg>")
    return "".join(s)


PHOTO_PATTERNS = [
    [(.00,.00,.33,.34),(.33,.58,.33,.42),(.66,.30,.34,.38)],
    [(.00,.18,.33,.40),(.33,.18,.33,.28),(.66,.00,.34,.52)],
    [(.00,.52,.33,.48),(.33,.26,.33,.32),(.66,.52,.34,.48)],
    [(.03,.12,.27,.28),(.36,.52,.27,.32),(.69,.12,.27,.30)],
    [(.00,.00,.35,.56),(.43,.58,.20,.28),(.66,.10,.34,.30)],
    [(.00,.52,.33,.48),(.33,.00,.33,.44),(.66,.50,.34,.50)],
    [(.00,.00,.33,.46),(.33,.38,.33,.35),(.66,.00,.34,.46)],
    [(.00,.58,.33,.42),(.33,.08,.33,.34),(.66,.58,.34,.42)],
    [(.00,.15,.33,.44),(.33,.48,.33,.40),(.66,.15,.34,.44)],
    [(.00,.32,.33,.34),(.33,.00,.33,.32),(.66,.32,.34,.34)],
    [(.03,.16,.27,.34),(.36,.16,.27,.34),(.69,.16,.27,.34)],
    [(.00,.46,.33,.54),(.33,.18,.33,.34),(.66,.00,.34,.48)],
    [(.00,.12,.33,.34),(.33,.54,.33,.36),(.66,.12,.34,.34)],
    [(.00,.12,.33,.30),(.33,.58,.33,.30),(.66,.12,.34,.30)],
    [(.00,.52,.33,.48),(.33,.52,.33,.48),(.66,.52,.34,.48)],
    [(.00,.00,.33,.48),(.33,.44,.33,.42),(.66,.00,.34,.48)],
    [(.03,.54,.27,.30),(.36,.10,.27,.34),(.66,.54,.34,.46)],
    [(.00,.56,.33,.44),(.33,.22,.33,.34),(.66,.00,.34,.56)],
    [(.00,.18,.27,.36),(.33,.50,.27,.36),(.66,.18,.27,.36)],
    [(.03,.10,.27,.32),(.36,.48,.27,.34),(.69,.10,.27,.32)],
]


def add_text(objects,idx,side,panel,W,H,palette,content):
    primary,paper,dark,white,accent=palette[1:]
    head,bodyfont=FONTS[idx%len(FONTS)]
    p=W/3
    x=panel*p+p*.075
    width=p*.85
    cat,title,subtitle,body,cta,contact,website=content
    fam=idx%20
    variation=idx//20
    yshift=variation*7

    if side==0 and panel==2:
        top=H*(.10 if fam not in {2,6,14} else .48)+yshift
        objects += [
            tb(f"{idx}_cover_cat",x,top,width,cat.upper(),15,accent if fam in {3,8,15} else primary,bodyfont,700,spacing=80),
            tb(f"{idx}_cover_title",x,top+34,width,title,36 if len(title)<18 else 29,dark if fam not in {1,5,16} else white,head,700),
            tb(f"{idx}_cover_sub",x,top+126,width,subtitle,17,dark if fam not in {1,5,16} else white,bodyfont,500),
            tb(f"{idx}_cover_web",x,H*.89,width,website,12,dark if fam not in {1,5,16} else white,bodyfont,600),
        ]
    elif side==0 and panel==0:
        objects += [
            tb(f"{idx}_back_title",x,H*.55-yshift,width,"LET'S CONNECT",22,dark,head,700),
            tb(f"{idx}_back_contact",x,H*.64-yshift,width,contact+"\n"+website,13,dark,bodyfont,400,lh=1.45),
            tb(f"{idx}_back_note",x,H*.82-yshift,width,"Follow us for news, ideas and updates.",12,dark,bodyfont),
        ]
    elif side==0:
        objects += [
            tb(f"{idx}_flap_title",x,H*.15+yshift,width,"WHY CHOOSE US",22,dark,head,700),
            tb(f"{idx}_flap_body",x,H*.24+yshift,width,body,13,dark,bodyfont,400,lh=1.35),
            tb(f"{idx}_flap_cta",x,H*.79-yshift,width,cta,14,primary,bodyfont,700,spacing=30),
        ]
    else:
        titles=["OUR STORY","WHAT WE OFFER","YOUR NEXT STEP"]
        bodies=[
            body,
            "01  Personal service\n02  Clear communication\n03  Quality outcomes\n04  Flexible options",
            f"{cta}\n\n{contact}\n{website}",
        ]
        objects += [
            tb(f"{idx}_inside_{panel}_title",x,H*.11+yshift,width,titles[panel],24,dark,head,700),
            tb(f"{idx}_inside_{panel}_body",x,H*.22+yshift,width,bodies[panel],13,dark,bodyfont,400,lh=1.38),
        ]
        if panel==1:
            objects.append(tb(f"{idx}_inside_quote",x,H*.74-yshift,width,"“Thoughtful service. Better experiences. Stronger results.”",16,primary,head,600,lh=1.25))


def build_page(idx,side,W,H,palette,content):
    bg=background_svg(W,H,palette,idx%20,side,idx)
    objects=[image(f"{idx}_{side}_static_bg",0,0,W,H,data_uri(bg),False,True)]
    pattern=PHOTO_PATTERNS[idx%20]
    if side:
        pattern=list(reversed(pattern))
    for j,(rx,ry,rw,rh) in enumerate(pattern):
        # variation shifts each of the 5 versions in a family.
        v=idx//20
        x=max(0,min(.94,rx+(v-2)*.006))*W
        y=max(0,min(.90,ry+((v+j)%3-1)*.012))*H
        w=min(rw*W,W-x)
        h=min(rh*H,H-y)
        ph=photo_placeholder(max(100,int(w)),max(100,int(h)),f"REPLACE PHOTO {j+1}",palette[1],idx*7+j+side)
        objects.append(image(f"{idx}_{side}_photo_{j+1}",x,y,w,h,data_uri(ph),True,False))
    for panel in range(3):
        add_text(objects,idx,side,panel,W,H,palette,content)
    return {"name":"Outside" if side==0 else "Inside","background":palette[2],"objects":objects},bg


def build_template(idx,product):
    W=int(getattr(product,"width",0) or DEFAULT_W)
    H=int(getattr(product,"height",0) or DEFAULT_H)
    if H>W:
        W,H=H,W
    palette=PALETTES[idx%20]
    content=CATEGORIES[(idx*7+idx//20)%20]
    outside,svg1=build_page(idx,0,W,H,palette,content)
    inside,svg2=build_page(idx,1,W,H,palette,content)
    pages=[outside,inside]
    family=idx%20
    variation=idx//20
    name=f"ZV Tri-Fold {idx+1:03d} · {content[0]} · {palette[0]} · Layout {family+1:02d}-{variation+1}"
    data={
        "version":VERSION,"templateType":"editable-master","generator":GENERATOR_ID,
        "editorSchema":"fabric-primitives-v1","editorNative":True,"editable":True,
        "designCode":f"zv-trifold-{idx+1:03d}","designName":name,
        "category":content[0],"composition_key":f"family-{family:02d}-variation-{variation:02d}",
        "pageCount":2,
        "brochure":{"type":"tri-fold","panelsPerSide":3,
                    "outsideOrder":["Back Cover","Fold-In Flap","Front Cover"],
                    "insideOrder":["Inside Left","Inside Centre","Inside Right"],
                    "staticBackground":True,"editableText":True,"editablePhotos":True},
        "document":{"width":W,"height":H,"profile":"trifold-brochure",
                    "physical":{"widthIn":float(getattr(product,"print_width_in",0) or 11),
                                "heightIn":float(getattr(product,"print_height_in",0) or 8.5)}},
        "pages":copy.deepcopy(pages),"adminPages":copy.deepcopy(pages),
        "source":{"type":"original-json-svg-composition",
                  "note":"Locked SVG decorative background + editable Fabric textbox/photo JSON overlays."},
    }
    return name,data,pages,[svg1,svg2]


def validate(data):
    if len(data.get("pages") or [])!=2:
        raise ValueError("Tri-fold template must contain Outside + Inside.")
    for p in data["pages"]:
        objs=p["objects"]
        bg=[o for o in objs if o.get("type")=="image" and o.get("backgroundAsset")]
        photos=[o for o in objs if o.get("type")=="image" and not o.get("backgroundAsset") and o.get("customerEditable") is True]
        texts=[o for o in objs if o.get("type") in {"text","textbox","i-text"} and o.get("customerEditable") is True]
        if len(bg)!=1 or len(photos)<3 or len(texts)<6:
            raise ValueError(f"Invalid page: backgrounds={len(bg)}, photos={len(photos)}, text={len(texts)}")


def preview_svg(W,H,page,static_svg):
    # Preview uses static SVG plus simplified editable overlay rendering.
    inner=static_svg[static_svg.find(">")+1:]
    if inner.endswith("</svg>"):
        inner=inner[:-6]
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',inner]
    for o in page["objects"]:
        if o.get("backgroundAsset"):
            continue
        if o.get("type")=="image":
            x,y,w,h=o["left"],o["top"],o["width"],o["height"]
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#dce3e2" stroke="#fff" stroke-width="3"/>')
            out.append(f'<text x="{x+w/2}" y="{y+h/2}" text-anchor="middle" font-family="Arial" font-size="14" fill="#667">PHOTO</text>')
        elif o.get("type") in {"text","textbox","i-text"}:
            x=o["left"]; y=o["top"]+o.get("fontSize",16); fs=o.get("fontSize",16)
            if o.get("textAlign")=="center":
                x+=o.get("width",0)/2; anchor="middle"
            else:
                anchor="start"
            tsp=[]
            for n,line in enumerate(str(o.get("text","")).split("\n")[:6]):
                tsp.append(f'<tspan x="{x}" dy="{0 if n==0 else fs*o.get("lineHeight",1.2)}">{escape(line)}</tspan>')
            out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{escape(str(o.get("fontFamily","Arial")))}" font-size="{fs}" font-weight="{o.get("fontWeight",400)}" fill="{o.get("fill","#222")}">{"".join(tsp)}</text>')
    out.append("</svg>")
    return "".join(out)


class Command(BaseCommand):
    help="Seed 100 original 2-page tri-fold brochures: static SVG backgrounds + editable JSON text/photos."

    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,required=True)
        parser.add_argument("--count",type=int,default=100)
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--replace-generated",action="store_true")

    def handle(self,*args,**opts):
        count=max(1,min(100,opts["count"]))
        try:
            product=Product.objects.get(pk=opts["product_id"])
        except Product.DoesNotExist:
            raise CommandError(f"Product {opts['product_id']} not found")

        built=[]; keys=set()
        for idx in range(count):
            name,data,pages,svgs=build_template(idx,product)
            validate(data)
            if data["composition_key"] in keys:
                raise CommandError("Duplicate composition key: "+data["composition_key"])
            keys.add(data["composition_key"])
            built.append((name,data,pages,svgs))

        self.stdout.write(self.style.SUCCESS(f"Validated {len(built)} brochures / {len(built)*2} pages."))
        self.stdout.write("Master: JSON + SVG combination. Text/photos editable; background SVG locked.")

        if opts["dry_run"]:
            for i,(name,data,pages,svgs) in enumerate(built,1):
                if i<=10 or i>count-3:
                    texts=sum(1 for p in pages for o in p["objects"] if o.get("type")=="textbox")
                    photos=sum(1 for p in pages for o in p["objects"] if o.get("type")=="image" and not o.get("backgroundAsset"))
                    self.stdout.write(f"{i:03d}: {name} · text={texts} · photos={photos}")
            self.stdout.write(self.style.SUCCESS("Dry run complete; database unchanged."))
            return

        base=Path("media")/MEDIA_DIR/str(product.pk)
        base.mkdir(parents=True,exist_ok=True)

        with transaction.atomic():
            if opts["replace_generated"]:
                old=DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR_ID)
                self.stdout.write(f"Removing previous brochure batch: {old.count()}")
                old.delete()

            for idx,(name,data,pages,svgs) in enumerate(built):
                files=[]
                for side,svg in enumerate(svgs):
                    side_name="outside" if side==0 else "inside"
                    fn=f"trifold_{idx+1:03d}_{side_name}.svg"
                    (base/fn).write_text(svg,encoding="utf-8")
                    files.append(f"{MEDIA_DIR}/{product.pk}/{fn}")
                data["svgFiles"]=files
                data["svgUsage"]="locked-background-sidecar-plus-json-editable-overlay"

                W=data["document"]["width"]; H=data["document"]["height"]
                prev=preview_svg(W,H,pages[0],svgs[0])
                if cairosvg:
                    try:
                        preview_bytes=cairosvg.svg2png(bytestring=prev.encode("utf-8"),output_width=W,output_height=H)
                        preview_name=f"trifold_{idx+1:03d}.png"
                    except Exception:
                        preview_bytes=prev.encode("utf-8"); preview_name=f"trifold_{idx+1:03d}.svg"
                else:
                    preview_bytes=prev.encode("utf-8"); preview_name=f"trifold_{idx+1:03d}.svg"

                obj=DesignTemplate.objects.filter(product=product,name=name).first()
                if obj is None:
                    obj=DesignTemplate(product=product,name=name)
                obj.json_data=data
                obj.is_active=True
                obj.preview.save(preview_name,ContentFile(preview_bytes),save=False)
                obj.save()

        self.stdout.write(self.style.SUCCESS(
            f"Imported {len(built)} tri-fold templates for product {product.pk}: {product.name}"
        ))
        self.stdout.write("Every template: Outside + Inside, 3 panels/side, editable text/photos, locked SVG artwork.")
