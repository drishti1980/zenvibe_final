from __future__ import annotations
import copy
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Category, Product, ProductPrintArea, ProductColorVariant, DesignTemplate

GENERATOR="zenvibe-promotional-luxury-v44"
LEGACY_GENERATORS={"zenvibe-promotional-editable-v1","zenvibe-promotional-editable-v2","zenvibe-promotional-luxury-v3","zenvibe-promotional-luxury-v4","zenvibe-promotional-luxury-v5","zenvibe-promotional-luxury-v6","zenvibe-promotional-luxury-v7","zenvibe-promotional-luxury-v8","zenvibe-promotional-luxury-v9","zenvibe-promotional-luxury-v10","zenvibe-promotional-luxury-v11","zenvibe-promotional-luxury-v12","zenvibe-promotional-luxury-v13","zenvibe-promotional-luxury-v14","zenvibe-promotional-luxury-v15","zenvibe-promotional-luxury-v16","zenvibe-promotional-luxury-v17","zenvibe-promotional-luxury-v18","zenvibe-promotional-luxury-v19","zenvibe-promotional-luxury-v20","zenvibe-promotional-luxury-v21","zenvibe-promotional-luxury-v22","zenvibe-promotional-luxury-v23","zenvibe-promotional-luxury-v24","zenvibe-promotional-luxury-v25","zenvibe-promotional-luxury-v26","zenvibe-promotional-luxury-v27","zenvibe-promotional-luxury-v28","zenvibe-promotional-luxury-v29","zenvibe-promotional-luxury-v30","zenvibe-promotional-luxury-v31","zenvibe-promotional-luxury-v32","zenvibe-promotional-luxury-v33","zenvibe-promotional-luxury-v34","zenvibe-promotional-luxury-v35","zenvibe-promotional-luxury-v36","zenvibe-promotional-luxury-v37","zenvibe-promotional-luxury-v38","zenvibe-promotional-luxury-v39","zenvibe-promotional-luxury-v40","zenvibe-promotional-luxury-v41","zenvibe-promotional-luxury-v42","zenvibe-promotional-luxury-v43",GENERATOR}
LEGACY_PRODUCT_IDS={63,64,163,164,165,166,167,252}
CANONICAL_PRODUCT_NAMES={
    "Compact Lightweight Umbrella – 36 Inch",
    "Custom 3D Printed Coasters with Logo",
    "Custom Aluminum Bottle Opener | Promotional Logo Tool",
    "Custom Car Freshener with Logo",
    "Custom Car Keychain with Logo | Personalized Automotive Keyring",
    "Custom Full Color Lanyard with Logo | Personalized Event ID Holder",
    "Custom Lanyard",
    "Custom Logo Golf Balls",
    "Custom Mouse Pads",
    "Custom Name Badge",
    "Custom Office Door Name Plate with Logo | Personalized Name & Title Sign",
    "Custom Paper Wristbands – Personalized Event & Admission Wristbands",
    "Custom Round Lapel Pin",
    "Custom Shape Bottle Opener Keychain with Logo | Personalized Promotional Keyring",
    "Custom Shape Metal Keychain with Logo | Personalized Premium Keyring",
    "Custom Shopping Cart Coin Keychain with Logo | Trolley Token Keyring",
    "Custom Silicone Wristbands",
    "Custom Triangle Shape Promotional Fluorescent Highlighter Pen",
    "Personalized Logo Golf Towel",
    "Premium Heavy Duty Custom Keychain",
}
COUNT=100
W=1000

# Product-family classification only. Physical ruler values are NEVER guessed here:
# they remain admin/source configured on Product / ProductPrintArea.
def family(product):
    s=(product.name+" "+product.slug).lower()
    if "coaster" in s: return "coaster"
    if "lanyard" in s: return "lanyard"
    if "wristband" in s: return "wristband"
    if "golf ball" in s: return "golf-ball"
    if "golf towel" in s: return "golf-towel"
    if "mouse pad" in s: return "mouse-pad"
    if "badge" in s: return "badge"
    if "name plate" in s: return "name-plate"
    if "freshener" in s: return "freshener"
    if "keychain" in s or "keyring" in s or "bottle opener" in s: return "keychain"
    if "lapel" in s or "pin" in s: return "lapel-pin"
    if "umbrella" in s: return "umbrella"
    if "highlighter" in s: return "highlighter"
    return "promotional"

def physical(product):
    area=product.print_areas.filter(print_width_in__isnull=False,print_height_in__isnull=False).order_by("sort_order","id").first()
    if area and area.print_width_in and area.print_height_in:
        return float(area.print_width_in),float(area.print_height_in)
    if product.print_width_in and product.print_height_in:
        return float(product.print_width_in),float(product.print_height_in)
    return None

def canvas(product):
    p=physical(product)
    if not p: return (1000,700)
    w,h=p
    if w>=h: return (W,max(260,round(W*h/w)))
    return (max(260,round(W*w/h)),W)

def rect(i,x,y,w,h,fill,stroke=None,sw=0):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"rect","left":x,"top":y,"width":w,"height":h,"fill":fill,"stroke":stroke,"strokeWidth":sw,"scaleX":1,"scaleY":1,"angle":0,"opacity":1,"customerEditable":True,"selectable":True,"evented":True}
def circle(i,x,y,r,fill,stroke=None,sw=0):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"circle","left":x-r,"top":y-r,"radius":r,"fill":fill,"stroke":stroke,"strokeWidth":sw,"scaleX":1,"scaleY":1,"angle":0,"opacity":1,"customerEditable":True,"selectable":True,"evented":True}
def text(i,x,y,w,t,size,fill="#161616",weight="600",align="center",font="Poppins"):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"textbox","left":x,"top":y,"width":w,"text":t,"fontSize":size,"fontFamily":font,"fontWeight":weight,"fill":fill,"textAlign":align,"lineHeight":1.05,"scaleX":1,"scaleY":1,"angle":0,"opacity":1,"customerEditable":True,"selectable":True,"evented":True}
def line(i,x1,y1,x2,y2,c,sw=3):
    return {"id":i,"name":i.title(),"type":"line","x1":x1,"y1":y1,"x2":x2,"y2":y2,"left":min(x1,x2),"top":min(y1,y2),"stroke":c,"strokeWidth":sw,"fill":None,"scaleX":1,"scaleY":1,"angle":0,"customerEditable":True,"selectable":True,"evented":True}

PALETTES=[
("#111827","#FFFFFF","#F59E0B"),("#0F3D3E","#F4F1DE","#E07A5F"),("#172554","#EFF6FF","#2563EB"),
("#3F1D38","#FFF7ED","#D97706"),("#18181B","#FAFAFA","#A3E635"),("#0C4A6E","#F0F9FF","#06B6D4"),
("#4C1D95","#FAF5FF","#C084FC"),("#7F1D1D","#FFF7ED","#F97316"),("#064E3B","#ECFDF5","#10B981"),("#292524","#FAFAF9","#A8A29E")
]

def build_heavy_keychain(product,idx):
    """100 hand-authored-feel editable strap compositions.

    0-19: elegant restrained collection.
    20-99: colourful luxury vector clip-art collection.
    Each template has its own composition recipe; colour is styling, never identity.
    """
    w,h=1000,208
    # Deterministic per-template palette: all 100 receive a different colour
    # combination while composition identity remains independent of colour.
    import colorsys
    hue=((idx * 0.61803398875) % 1.0)
    sat=0.58 + (idx % 5)*0.06
    val=0.62 + (idx % 4)*0.07
    rgb=colorsys.hsv_to_rgb(hue,min(.88,sat),min(.90,val))
    unique_accent="#%02X%02X%02X" % tuple(int(v*255) for v in rgb)
    rgb2=colorsys.hsv_to_rgb((hue+.11)%1.0,min(.78,sat+.05),min(.82,val))
    unique_dark="#%02X%02X%02X" % tuple(int(v*255) for v in rgb2)
    elegant=[("#111827","#F8FAFC","#C6A15B"),("#172554","#F8FAFC","#94A3B8"),("#292524","#FFFBEB","#B7791F"),("#052E2B","#F0FDFA","#6EE7B7"),("#3B0764","#FAF5FF","#C4B5FD")]
    vivid=[("#312E81","#FFF7ED","#F97316"),("#164E63","#ECFEFF","#22D3EE"),("#831843","#FFF1F2","#FB7185"),("#166534","#F0FDF4","#4ADE80"),("#1E3A8A","#EFF6FF","#FACC15"),("#701A75","#FDF4FF","#E879F9"),("#7C2D12","#FFF7ED","#FDBA74"),("#3730A3","#EEF2FF","#818CF8"),("#155E75","#ECFEFF","#A3E635"),("#991B1B","#FFF1F2","#FBBF24")]

    # Full-bleed editable luxury backgrounds. These are artwork backgrounds
    # inside the printable strap, not the locked product-reference image.
    luxury_backgrounds=[
        ("#0B1020","#172554"),("#190B2C","#4C1D95"),("#2A0E17","#881337"),
        ("#06251E","#065F46"),("#251507","#92400E"),("#071D2B","#155E75"),
        ("#20110A","#9A3412"),("#17132B","#4338CA"),("#281024","#A21CAF"),
        ("#10200B","#3F6212"),("#24130B","#B45309"),("#081C24","#0E7490"),
        ("#260D13","#BE123C"),("#101B35","#1D4ED8"),("#1D102A","#7E22CE"),
        ("#082018","#047857"),("#2B1708","#CA8A04"),("#151515","#404040"),
        ("#18122B","#6D28D9"),("#071A27","#0369A1"),
    ]
    bg1,bg2=luxury_backgrounds[idx%len(luxury_backgrounds)]
    # A second editable panel gives depth instead of a flat white canvas.
    # Slightly different inset/stripe treatment by template prevents the
    # backgrounds themselves looking cloned.
    background=[rect("luxury_bg",0,0,w,h,bg1)]
    # Accent stays at the edge so it cannot cover text or clip-art.
    if idx%4==0: background += [rect("luxury_edge_l",0,0,28,h,bg2),rect("luxury_edge_r",972,0,28,h,bg2)]
    elif idx%4==1: background += [rect("luxury_edge_t",0,0,w,18,bg2),rect("luxury_edge_b",0,190,w,18,bg2)]
    elif idx%4==2: background += [rect("luxury_edge_l",0,0,18,h,bg2)]
    else: background += [rect("luxury_edge_r",982,0,18,h,bg2)]
    for _bg in background: _bg["selectable"]=True

    def brand(dark,accent,x=260,y=52,size=44,tag="PREMIUM COLLECTION"):
        return [text("brand",x,y,680,"YOUR BRAND",size,"#FFF8E7","800","left"),text("tag",x+3,119,520,tag,14,accent,"700","left")]
    def flower(x,y,dark,accent,s=1):
        return [circle("fl_c",x,y,10*s,dark),circle("fl_1",x,y-25*s,16*s,accent),circle("fl_2",x+24*s,y-7*s,16*s,accent),circle("fl_3",x+15*s,y+21*s,16*s,accent),circle("fl_4",x-15*s,y+21*s,16*s,accent),circle("fl_5",x-24*s,y-7*s,16*s,accent)]
    def sparkle(x,y,dark,accent):
        return [line("sp_v",x,y-30,x,y+30,accent,4),line("sp_h",x-30,y,x+30,y,dark,4),circle("sp_c",x,y,7,accent)]
    def leafsprig(x,y,dark,accent):
        return [line("stem",x-45,y+42,x+45,y-42,dark,3),circle("leaf1",x-25,y+23,16,accent),circle("leaf2",x+4,y-4,18,dark),circle("leaf3",x+31,y-29,14,accent)]

    if idx < 20:
        dark,light,accent=elegant[idx%5]
        recipes=[
          lambda: circle("seal",105,104,58,dark) and [circle("seal",105,104,58,dark),text("mono",57,74,96,"ZV",34,light,"800")]+brand(dark,accent,215,52,45,"EST. 2026"),
          lambda: [rect("double1",42,38,165,132,"transparent",accent,3),rect("double2",58,52,133,104,"transparent",dark,2),text("mono",76,75,96,"ZV",32,dark,"800")]+brand(dark,accent,245,52,43,"SIGNATURE SERIES"),
          lambda: leafsprig(115,104,dark,accent)+brand(dark,accent,225,50,45,"BOTANICAL ATELIER"),
          lambda: [line("deco1",45,104,95,52,accent,5),line("deco2",95,52,145,104,dark,5),line("deco3",145,104,195,52,accent,5)]+brand(dark,accent,235,52,44,"ART DECO"),
          lambda: [circle("pearl1",72,104,13,accent),circle("pearl2",110,104,21,dark),circle("pearl3",158,104,13,accent)]+brand(dark,accent,220,52,45,"FINE OBJECTS"),
          lambda: [rect("blacklabel",42,56,185,96,dark),text("label",62,82,145,"MAISON",20,light,"800")]+brand(dark,accent,265,52,43,"PARIS • 2026"),
          lambda: [text("number",42,35,180,"01",72,accent,"900"),line("numrule",180,45,180,165,dark,3)]+brand(dark,accent,220,52,45,"LIMITED EDITION"),
          lambda: [circle("ring1",108,104,62,"transparent",accent,4),circle("ring2",108,104,43,"transparent",dark,2),circle("gem",108,104,10,accent)]+brand(dark,accent,220,52,44,"JEWEL COLLECTION"),
          lambda: [rect("bar",45,35,11,138,accent),line("fine",80,35,80,173,dark,2),text("mono",105,72,85,"Z",34,dark,"800")]+brand(dark,accent,225,52,44,"MODERNIST"),
          lambda: sparkle(110,104,dark,accent)+brand(dark,accent,215,52,46,"CELESTIAL"),
          lambda: [line("arch1",48,150,110,50,accent,6),line("arch2",110,50,180,150,dark,6),circle("sun",110,92,18,accent)]+brand(dark,accent,225,52,44,"ARCHITECTURAL"),
          lambda: [rect("ticket",45,58,175,92,"transparent",dark,3),circle("cut1",45,104,18,light),circle("cut2",220,104,18,light),text("mono",78,84,110,"ZV",26,accent,"800")]+brand(dark,accent,255,52,43,"PRIVATE CLUB"),
          lambda: [circle("medal",110,88,42,accent),line("tail1",90,123,75,165,dark,5),line("tail2",130,123,145,165,dark,5),text("mono",78,70,64,"Z",26,dark,"800")]+brand(dark,accent,215,52,44,"AWARD SERIES"),
          lambda: [line("h1",45,68,195,68,accent,3),line("h2",45,140,195,140,dark,3),text("mono",78,80,85,"ZV",28,dark,"800")]+brand(dark,accent,235,52,45,"EDITORIAL"),
          lambda: [circle("orb1",80,104,34,accent),circle("orb2",130,104,34,dark),circle("orb3",180,104,34,light,accent,3)]+brand(dark,accent,235,52,43,"TRINITY"),
          lambda: [rect("cornerh",45,42,125,7,accent),rect("cornerv",45,42,7,105,accent),circle("cornerDot",170,42,9,dark)]+brand(dark,accent,205,52,45,"GALLERY"),
          lambda: [line("slash1",50,158,125,48,accent,8),line("slash2",100,158,175,48,dark,5),line("slash3",150,158,205,78,accent,3)]+brand(dark,accent,240,52,44,"COUTURE"),
          lambda: [circle("coin",110,104,57,dark),circle("coin2",110,104,43,"transparent",accent,3),text("mono",68,77,84,"ZV",31,light,"800")]+brand(dark,accent,225,52,44,"HERITAGE"),
          lambda: [rect("steps1",48,118,38,42,dark),rect("steps2",96,88,38,72,accent),rect("steps3",144,55,38,105,dark)]+brand(dark,accent,225,52,44,"BAUHAUS"),
          lambda: [circle("minidot",110,104,12,accent),line("minil",45,104,88,104,dark,2),line("minir",132,104,198,104,dark,2)]+brand(dark,accent,225,52,46,"ESSENTIAL"),
        ]
        return w,h,background+recipes[idx]()

    j=idx-20; theme=j%20; composition=j//20
    dark,light,accent=vivid[(j*3+theme)%10]
    # Colourful collection: every one of the 80 templates gets its own
    # primary/accent pairing, not a repeated 10-colour cycle.
    dark,accent=unique_dark,unique_accent
    arts=[
      lambda: flower(115,104,dark,accent,1.0),
      lambda: leafsprig(115,104,dark,accent),
      lambda: [circle("sun",112,104,43,accent),circle("sunCore",112,104,19,light)]+sparkle(178,62,dark,accent),
      lambda: [line("c1",55,138,78,65,accent,8),line("c2",78,65,112,120,dark,8),line("c3",112,120,148,65,accent,8),line("base",50,143,175,143,dark,5)],
      lambda: [circle("b1",82,84,30,accent),circle("b2",142,84,30,accent),circle("b3",88,132,22,dark),circle("b4",136,132,22,dark),circle("body",112,108,8,light,dark,2)],
      lambda: [line("m1",42,150,105,55,accent,9),line("m2",105,55,178,150,dark,9),circle("sun",183,58,18,accent)],
      lambda: sparkle(110,104,dark,accent)+[circle("star2",175,65,12,accent),circle("star3",62,148,9,dark)],
      lambda: [circle("w1",70,110,35,accent),circle("w2",120,110,35,dark),circle("w3",170,110,35,light,accent,4)],
      lambda: [circle("compass",112,104,58,"transparent",dark,4),line("needle",112,48,148,138,accent,8),circle("hub",112,104,9,dark)],
      lambda: [circle("disc",95,108,45,dark),circle("hole",95,108,12,accent),line("note",158,50,158,130,accent,6),circle("notehead",143,140,17,accent)],
      lambda: [circle("cup",105,110,42,"transparent",dark,5),circle("handle",150,110,18,"transparent",accent,5),line("steam1",85,42,95,72,accent,3),line("steam2",120,42,126,72,dark,3)],
      lambda: [circle("globe",110,104,52,"transparent",accent,4),line("eq",60,104,160,104,dark,3),line("route",72,70,150,138,accent,4)],
      lambda: [circle("conf1",62,62,10,accent),circle("conf2",160,65,12,dark),circle("conf3",112,148,9,accent),line("burst1",110,105,60,145,dark,4),line("burst2",110,105,180,118,accent,4)],
      lambda: [circle("heart1",90,88,28,accent),circle("heart2",130,88,28,accent),line("heartl",67,103,110,158,accent,12),line("heartr",153,103,110,158,accent,12)],
      lambda: [line("bolt1",125,38,74,112,accent,15),line("bolt2",74,112,126,104,dark,15),line("bolt3",126,104,92,170,accent,15)],
      lambda: [rect("sq",50,58,72,72,accent),circle("orb",158,118,40,dark),circle("cut",158,118,18,light)],
      lambda: [line("circuit1",48,68,145,68,accent,4),line("circuit2",145,68,145,142,dark,4),circle("node1",48,68,11,dark),circle("node2",145,142,13,accent)],
      lambda: [circle("planet",110,104,43,dark),circle("orbit",110,104,68,"transparent",accent,3),circle("moon",174,82,10,accent)],
      lambda: [rect("gift",65,82,95,76,accent),line("ribbonv",112,82,112,158,dark,6),line("ribbonh",65,112,160,112,dark,6),circle("bow1",90,72,20,"transparent",accent,5),circle("bow2",134,72,20,"transparent",accent,5)],
      lambda: [circle("camera",110,108,50,"transparent",dark,5),circle("lens",110,108,23,accent),rect("flash",82,48,56,24,dark)],
    ]
    art=background+arts[theme]()
    # Large editable ornament layer makes the clip-art visible at real strap scale.
    ornaments=[
      flower(190,55,"#FFF8E7",accent,.45)+flower(205,150,"#FFF8E7",accent,.32),
      leafsprig(190,104,"#FFF8E7",accent),
      sparkle(190,55,"#FFF8E7",accent)+sparkle(205,150,"#FFF8E7",accent),
      [circle("lux_dot1",185,60,9,accent),circle("lux_dot2",205,82,5,"#FFF8E7"),circle("lux_dot3",188,145,7,accent)],
    ]
    art += ornaments[composition%4]
    # Four composition systems; clip-art position, type hierarchy and framing all change.
    if composition==0:
      art += brand(dark,accent,235,52,44,["BLOOM","SIGNATURE","SUNSET","ROYAL","FLUTTER","SUMMIT","STARDUST","TIDAL","NORTH","RHYTHM","ROAST","WANDER","FÊTE","AMOUR","VOLT","FORM","DIGITAL","ORBIT","GIFTED","FOCUS"][theme])
    elif composition==1:
      art += [text("brand",235,42,680,"YOUR",29,"#FFF8E7","600","left"),text("brand2",235,78,680,"BRAND",55,accent,"900","left"),line("rule",238,151,780,151,dark,3)]
    elif composition==2:
      art += [rect("brandFrame",225,43,545,122,"transparent",accent,3),text("brand",250,65,495,"YOUR BRAND",39,"#FFF8E7","800","left"),text("tag",253,120,420,"LUXURY EDITION",14,accent,"700","left")]
    else:
      art += [text("brand",235,52,500,"YOUR BRAND",42,"#FFF8E7","800","left"),text("tag",238,117,400,"COLOUR COLLECTION",14,accent,"700","left"),circle("endBadge",875,104,48,accent),text("endText",842,87,66,"ZV",22,light,"900")]
    return w,h,art

def build_umbrella(product, idx):
    """Safe, theme-specific editable umbrella compositions (100 designs)."""
    from .umbrella_artwork_v2 import build_umbrella_v2
    return build_umbrella_v2(product, idx, rect, circle, text, line)


def build_coaster(product,idx):
    """100 genuinely different editable coaster compositions.

    There are no colour-only/decoration-only variants: idx 0..99 selects a
    unique composition recipe (10 layout systems x 10 independently arranged
    art directions). Shape remains external to the artwork so the SAME design
    adapts to Square/Circle.
    """
    import math
    w=h=1000
    palettes=[
      ("#0B1020","#FFF8E7","#D4AF37","#7C3AED"),("#FFF7ED","#111827","#C2410C","#F59E0B"),
      ("#062A2A","#F8FAFC","#2DD4BF","#FBBF24"),("#2B1020","#FFF1F2","#FB7185","#D4AF37"),
      ("#0F2344","#F8FAFC","#60A5FA","#F59E0B"),("#1F1510","#FFF7ED","#D97706","#14B8A6"),
      ("#F5F0E8","#17324D","#0F766E","#C2410C"),("#20112F","#FAF5FF","#C084FC","#FACC15"),
      ("#FFF1F5","#4A102A","#E11D48","#15803D"),("#111827","#F8FAFC","#6366F1","#F97316"),
    ]
    # Interleave structure, art direction and palette.  The previous v25 grouped
    # ten neighbouring cards under the same dominant structure, which made the
    # gallery visibly repetitive even though their ornaments differed.
    # v26 uses a bijective 0..99 pairing: every (layout,direction) combination
    # occurs exactly once, but consecutive cards never share either one.
    layout=idx%10
    direction=(idx//10 + (idx%10)*3)%10
    palette_index=((idx%10)*7 + (idx//10)*3)%10
    paper,ink,accent,accent2=palettes[palette_index]
    o=[rect("background",0,0,w,h,paper)]

    def ring(i,cx,cy,r,c,sw=8): return [circle(i,cx,cy,r,"transparent",c,sw)]
    def petal(i,cx,cy,rx,ry,c,ang=0):
        return {"id":i,"name":i.title(),"type":"ellipse","left":cx-rx,"top":cy-ry,"rx":rx,"ry":ry,
                "fill":c,"stroke":None,"strokeWidth":0,"scaleX":1,"scaleY":1,"angle":ang,
                "opacity":1,"customerEditable":True,"selectable":True,"evented":True}
    def flower(prefix,cx,cy,s=1):
        z=[circle(prefix+"c",cx,cy,16*s,ink)]
        for q in range(6):
            ang=q*60; z.append(petal(prefix+str(q),cx+math.cos(math.radians(ang))*48*s,
                cy+math.sin(math.radians(ang))*48*s,18*s,34*s,accent if q%2 else accent2,ang))
        return z
    def sprig(prefix,x,y,s=1,flip=1):
        z=[line(prefix+"stem",x-110*s*flip,y+95*s,x+110*s*flip,y-95*s,ink,5*s)]
        for q in range(5):
            px=x+(-80+q*40)*s*flip; py=y+(70-q*35)*s
            z.append(petal(prefix+"l"+str(q),px,py,16*s,38*s,accent if q%2 else accent2,-40*flip))
        return z
    def title(x,y,width,label="YOUR BRAND",size=58,align="center"):
        return [text("brand",x,y,width,label,size,ink,"700",align,font="Georgia")]
    def sub(x,y,width,label):
        return [text("tag",x,y,width,label,18,accent,"700","center")]

    # Ten wholly different page structures. None is a recolour of another.
    if layout==0: # central medallion
        o += ring("med1",500,500,365,accent,10)+ring("med2",500,500,275,ink,4)
        o += title(220,420,560)+sub(300,505,400,"SIGNATURE COLLECTION")
    elif layout==1: # editorial split
        o += [rect("leftPanel",0,0,365,1000,ink),rect("accentBar",365,0,34,1000,accent)]
        o += [text("mono",70,280,230,"ZV",150,paper,"700","center")]+title(455,360,430,"YOUR\nBRAND",62,"left")+sub(455,565,390,"MODERN EDITION")
    elif layout==2: # framed label
        o += [rect("frame",105,105,790,790,"transparent",ink,8),rect("label",205,345,590,310,paper,accent,5)]
        o += title(245,410,510)+sub(300,505,400,"PRIVATE LABEL")
    elif layout==3: # diagonal couture
        o += [rect("diagA",-160,90,1320,245,accent),rect("diagB",-160,665,1320,245,accent2)]
        o[-2]["angle"]=-18; o[-1]["angle"]=-18
        o += [rect("centerCard",190,300,620,400,paper,ink,4)]+title(245,410,510)+sub(300,510,400,"COUTURE SERIES")
    elif layout==4: # asymmetric gallery
        o += [circle("orb",235,250,185,accent2),circle("orb2",790,765,125,accent)]
        o += [rect("rule",130,170,18,660,ink)]+title(210,330,600,"YOUR BRAND",64,"left")+sub(210,445,430,"GALLERY OBJECTS")
    elif layout==5: # arch
        o += ring("arch",500,540,365,accent,16)+ring("arch2",500,540,305,ink,5)
        o += [rect("mask",100,0,800,310,paper)]+title(220,385,560)+sub(300,480,400,"HERITAGE HOUSE")
    elif layout==6: # four-corner composition
        o += [rect("center",225,225,550,550,paper,ink,5)]
        o += title(270,405,460)+sub(310,500,380,"ATELIER EDITION")
        for n,(x,y) in enumerate([(120,120),(880,120),(120,880),(880,880)]):
            o += flower("corner"+str(n),x,y,.85)
    elif layout==7: # horizontal bands
        o += [rect("band1",0,0,1000,260,ink),rect("band2",0,740,1000,260,accent)]
        o += [text("topMark",70,72,860,"EST. 2026",28,paper,"700","center")]
        o += title(180,390,640, "YOUR BRAND",72)+sub(290,505,420,"CRAFTED FOR YOU")
    elif layout==8: # offset seal
        o += [circle("seal",300,500,255,ink),circle("sealIn",300,500,205,paper,accent,8)]
        o += [text("sealMark",180,420,240,"ZV",95,accent,"700","center")]
        o += title(585,365,320,"YOUR\nBRAND",50,"left")+sub(585,535,300,"PREMIUM SERIES")
    else: # minimalist typographic
        o += [line("topRule",140,240,860,240,accent,6),line("bottomRule",140,760,860,760,accent2,6)]
        o += [text("number",150,285,700,f"{idx+1:02d}",155,accent2,"400","center")]
        o += title(220,520,560)+sub(300,615,400,"LIMITED COLLECTION")

    # Ten art directions change motif, balance and focal points within each
    # structure, making every layout+direction pair a distinct composition.
    if direction==0:
        o += flower("hero",180,790,1.35)+sprig("spr",790,190,.8,-1)
    elif direction==1:
        o += sprig("botL",220,760,1.15,1)+sprig("botR",780,240,.8,-1)
    elif direction==2:
        for q in range(8):
            ang=q*45; o += [circle("jewel"+str(q),500+math.cos(math.radians(ang))*410,500+math.sin(math.radians(ang))*410,18+(q%2)*8,accent if q%2 else accent2)]
    elif direction==3:
        o += ring("orbitA",500,500,425,accent2,4)+ring("orbitB",500,500,390,accent,3)
        o += [circle("gemA",160,255,24,accent),circle("gemB",835,735,34,accent2)]
    elif direction==4:
        for q,(x,y) in enumerate([(130,180),(260,110),(850,180),(900,330),(120,690),(180,860),(760,880),(900,760)]):
            o += flower("wild"+str(q),x,y,.42+(q%3)*.12)
    elif direction==5:
        for q in range(16):
            x=90+(q%4)*270; y=90+(q//4)*270
            o += [rect("tile"+str(q),x,y,75,75,accent if q%2 else accent2)]
            o[-1]["angle"]=45
    elif direction==6:
        for q in range(28):
            ang=q*12.857; rr=370 if q%2 else 315
            o += [circle("bead"+str(q),500+math.cos(math.radians(ang))*rr,500+math.sin(math.radians(ang))*rr,9+(q%4)*4,accent if q%2 else ink)]
    elif direction==7:
        o += [line("ray1",80,850,430,540,accent,18),line("ray2",920,150,570,460,accent2,12),
              circle("sun",835,165,70,accent),circle("moon",165,835,48,ink)]
    elif direction==8:
        o += [rect("cornerTL",45,45,210,18,accent),rect("cornerTL2",45,45,18,210,accent),
              rect("cornerBR",745,937,210,18,accent2),rect("cornerBR2",937,745,18,210,accent2)]
        o += flower("fineFlower",820,200,.65)
    else:
        o += sprig("wreathL",245,500,.9,1)+sprig("wreathR",755,500,.9,-1)
        o += flower("crestTop",500,155,.55)+flower("crestBottom",500,845,.55)

    return w,h,o

def build_freshener(product,idx):
    """100 unique luxury freshener masters.

    Identity is driven by a unique composition signature for every index, not by
    recolouring or cycling the same foreground. Gloss is constructed from
    editable translucent-looking highlight primitives so it remains editable.
    """
    w,h=canvas(product); s=min(w,h)
    palettes=(
        ("#08090D","#F8F5EC","#D4AF37","#242832"),
        ("#0B1F18","#FFF8E7","#C6A15B","#24483B"),
        ("#0B1830","#FAF6EA","#D6B76B","#244B78"),
        ("#2A111C","#FFF5F2","#D8A0A8","#653047"),
        ("#21142D","#FCF7FF","#C7A6DF","#513868"),
        ("#2B160F","#FFF4E6","#D89A52","#70402A"),
        ("#102224","#F5F1E7","#BFA06A","#345256"),
        ("#151515","#FAF7EF","#D6BE78","#3B3B3B"),
        ("#0D3027","#FBF3E2","#D8B15E","#28614F"),
        ("#241D42","#FBF8FF","#B9A5E8","#54477A"),
        ("#3A0E18","#FFF7F4","#E2B27A","#7D2736"),
        ("#082A3A","#F5FBFC","#7FC8C9","#18566C"),
        ("#17365D","#FFF9EE","#E5C07B","#315A86"),
        ("#3B1F2B","#FFF7FA","#E8B4C5","#704154"),
        ("#183A32","#F9F4E8","#E0BD76","#3F6B5E"),
        ("#332713","#FFF9E9","#E0B84D","#6D5729"),
        ("#172033","#F7F9FC","#9FB7D9","#354967"),
        ("#361A4A","#FFF8FF","#D6A7E6","#704C84"),
        ("#4A1717","#FFF4EC","#E5A15D","#8B3C32"),
        ("#12333D","#F5FCFA","#72C4B8","#2B6670"),
        ("#071A2B","#F8F4E8","#C8A55A","#163A5B"),
        ("#29142A","#FFF7F1","#DDA47A","#62385B"),
        ("#1C3525","#FCF6E9","#CDB26B","#47664C"),
        ("#292929","#FFFFFF","#C9A34F","#575757"),
        ("#38261A","#FFF7EA","#D7B17A","#76523B"),
        ("#172B4D","#F6F2E9","#D1A95B","#395780"),
        ("#401D2A","#FFF4F6","#E0A2B2","#7D4254"),
        ("#113A3A","#FFF9ED","#D9B568","#33706A"),
        ("#312455","#FAF8FF","#C2ADE8","#66568A"),
        ("#4B2417","#FFF5E9","#DFA05F","#8A5133"),
        ("#091F35","#F9FBFF","#91B8DF","#22496E"),
        ("#1A3C2B","#FFF8E9","#D7AD5E","#426C51"),
        ("#3E1727","#FFF5F8","#E6A7BD","#80425C"),
        ("#26313A","#F8F5EE","#BDA67B","#52616B"),
        ("#4B3510","#FFF9E8","#E5BE56","#876A24"),
        ("#18254A","#FFF7EE","#E0AA76","#40568A"),
        ("#3B233F","#FFF8F9","#D9A7B5","#74527A"),
        ("#0D3830","#F7FAF2","#AFCB78","#2F695C"),
        ("#4A2020","#FFF5EA","#E1A060","#86514A"),
        ("#143C50","#F8FCFF","#8BC9E0","#36718A"),
        ("#24203A","#FFF9EF","#D3B36E","#56506D"),
        ("#50202D","#FFF7F4","#E7B082","#91475B"),
        ("#163B2A","#F8F1DF","#CBAA62","#397052"),
        ("#101820","#FAFAF7","#C4B27A","#344451"),
        ("#533718","#FFF8E8","#E2B458","#91652F"),
        ("#1E2D59","#FAF7F0","#D0B16B","#465D91"),
        ("#51213A","#FFF5F9","#DCA5C0","#92516E"),
        ("#124A43","#F8F6E9","#D4B86A","#3B7A70"),
        ("#36254C","#FBF8FF","#C5A7D9","#6B5681"),
        ("#5A291C","#FFF5E7","#E3A66A","#9B5941"),
        ("#071E3D","#FFF8E7","#E6BE65","#244D7A"),
        ("#203F2D","#FAF4E4","#D8B875","#4E7558"),
        ("#551C2E","#FFF6F8","#EAB1C2","#964C66"),
        ("#263238","#FAF7F0","#D0AA69","#59676B"),
        ("#594515","#FFFAE9","#E8C75B","#967C32"),
        ("#1C315E","#F7F4EC","#C8A45E","#4D6794"),
        ("#472443","#FFF7FB","#D8A6C9","#83577C"),
        ("#07534B","#FFF8EA","#E0BA63","#3D8177"),
        ("#44315D","#FBF7FF","#CDB4E8","#79688D"),
        ("#653020","#FFF5E8","#E4A46A","#A86247"),
        ("#102A56","#F9F7F0","#D8B86A","#385C8D"),
        ("#294A32","#FFF8E9","#D7B36D","#5B7B61"),
        ("#65213B","#FFF5F8","#E7ABC2","#A95874"),
        ("#303A42","#FAF5E9","#CDB178","#657078"),
        ("#6A4A13","#FFF9E6","#EAC45A","#A9822C"),
        ("#25366A","#FBF7ED","#D4AE65","#58699A"),
        ("#57264D","#FFF7FA","#DDA9C7","#956083"),
        ("#0A6157","#FFF9EC","#E1BB68","#459087"),
        ("#50386A","#FCF8FF","#CAB0E3","#856F98"),
        ("#713524","#FFF6E9","#E6A56D","#B06D4F"),
        ("#12346B","#FFF8EA","#E1B75D","#45699A"),
        ("#31583A","#FCF5E4","#D9B36A","#668568"),
        ("#742744","#FFF6F8","#E9ADC1","#B6637D"),
        ("#39454E","#FBF6EA","#CFB17A","#6F7B82"),
        ("#755416","#FFFAE8","#ECC85D","#B28D32"),
        ("#2A4077","#FCF8EF","#D6B16B","#6075A3"),
        ("#642B56","#FFF7FB","#E0ABC8","#A0698F"),
        ("#0C6C60","#FFFAEE","#E2BC6B","#4D9B91"),
        ("#5B4074","#FDF9FF","#CEB4E7","#9079A1"),
        ("#7D3A27","#FFF7EA","#E8A76D","#BB7353"),
        ("#173E78","#FFF9EC","#E4BB61","#4D71A4"),
        ("#38633F","#FDF6E7","#DBB66C","#6E906F"),
        ("#812A4A","#FFF7F9","#EBB0C4","#C06B84"),
        ("#424F58","#FCF7EC","#D2B47D","#79858B"),
        ("#80601A","#FFFAEA","#EDCA61","#BC9736"),
        ("#304985","#FDF9F0","#D9B46F","#687BAA"),
        ("#71305F","#FFF8FC","#E2AEC9","#AA7198"),
        ("#0E7769","#FFFBF0","#E4BF6F","#56A69B"),
        ("#66477F","#FEFAFF","#D1B8E9","#9981A9"),
        ("#88402B","#FFF8EC","#EAAB71","#C27A58"),
        ("#1B4785","#FFFAEF","#E6BE66","#5578AA"),
        ("#3F6E46","#FEF8E9","#DDB96F","#769878"),
        ("#8D2D50","#FFF8FA","#EDB3C7","#C8738B"),
        ("#4B5962","#FDF8ED","#D5B780","#818D93"),
        ("#8C6A1D","#FFFBEC","#EFCD65","#C4A03A"),
    )
    bg,fg,gold,panel=palettes[idx % len(palettes)]
    # Display order:
    # 001-040 = dark/solid/glossy luxury
    # 041-100 = light/normal premium
    if idx < 40:
        surface=bg
        ink=fg
        soft=panel
    else:
        surface=fg
        ink=bg
        soft=panel
    o=[rect("bg",0,0,w,h,surface)]
    o[0]["freshenerSurface"]=True
    # Decorative geometry lives only in perimeter zones. The protected text
    # area is x=18%-82%, y=27%-70%, preventing rails/panels from crossing copy.
    mode=idx%25
    q=idx//25
    glossy=(idx<40 and (idx%2==0 or idx%5==0))
    if mode%5==0:
        o += [rect("frame",w*.085,h*.085,w*.83,h*.83,"rgba(0,0,0,0)",gold,max(2,s*.005))]
    elif mode%5==1:
        o += [rect("top_key",w*.10,h*.10,w*.28,h*.020,gold),rect("bottom_key",w*.62,h*.88,w*.28,h*.020,gold)]
    elif mode%5==2:
        o += [circle("corner_a",w*.13,h*.14,s*(.030+.004*q),soft),circle("corner_b",w*.87,h*.86,s*(.025+.004*q),gold)]
    elif mode%5==3:
        o += [rect("left_tick",w*.09,h*.10,w*.020,h*.18,gold),rect("right_tick",w*.89,h*.72,w*.020,h*.18,gold)]
    else:
        o += [line("top_slash",w*.12,h*.17,w*.25,h*.09,gold,max(2,s*.005)),line("bottom_slash",w*.75,h*.91,w*.88,h*.83,gold,max(2,s*.005))]

    if glossy:
        # Gloss is confined above/below the protected copy zone.
        o += [rect("gloss_top",w*.14,h*.145,w*.72,h*.045,soft),
              rect("gloss_shine",w*.22,h*.205,w*.42,h*.012,gold),
              rect("gloss_bottom",w*.20,h*.80,w*.60,h*.035,soft)]
    elif idx >= 40:
        # Light/normal templates: subtle accents instead of large solid panels.
        style=idx%4
        if style==0:
            o += [rect("soft_top",w*.12,h*.16,w*.76,h*.030,soft)]
        elif style==1:
            o += [rect("soft_bottom",w*.18,h*.82,w*.64,h*.028,soft)]
        elif style==2:
            o += [circle("soft_dot",w*.84,h*.16,s*.028,soft)]
        else:
            o += [line("soft_rule",w*.16,h*.18,w*.42,h*.18,soft,max(2,s*.005))]
    else:
        # Dark non-gloss designs use restrained perimeter accents only.
        o += [rect("lux_key",w*.12,h*.84,w*(.18+.02*(idx%4)),h*.018,gold)]

    brands=["YOUR BRAND","MAISON","NORTH & CO.","LUXE DRIVE","ATELIER","SIGNATURE","MONOGRAM","STUDIO NO.8","PREMIUM CO.","THE JOURNEY"]
    tags=["SIGNATURE SCENT","DRIVE IN STYLE","PREMIUM EDITION","EST. 2026","FRESH EVERY MILE","CRAFTED FOR YOU","LIMITED SERIES","MODERN ESSENTIALS","DISTINCTLY YOURS","THE SCENT EDIT"]
    brand=brands[(idx*3+idx//10)%10]; tag=tags[(idx*7+idx//6)%10]
    q=idx//25; typ=idx%10
    left=.15+.025*q; right=.85-.018*q; width=right-left
    top=.30+.012*(idx%4)
    if typ==0:
        o += [text("brand",w*left,h*top,w*width,brand,s*(.060+.004*q),ink,"800"),line("rule",w*.34,h*(top+.17),w*.66,h*(top+.17),gold,3),text("tag",w*.23,h*(top+.23),w*.54,tag,s*.020,ink,"600")]
    elif typ==1:
        o += [text("eyebrow",w*left,h*(top-.08),w*.40,"LUXE / 0"+str(q+1),s*.018,gold,"700","left"),text("brand",w*left,h*top,w*width,brand,s*.058,ink,"800","left"),text("tag",w*left,h*(top+.19),w*.50,tag,s*.020,ink,"600","left")]
    elif typ==2:
        o += [circle("seal",w*.50,h*(top+.02),s*(.070+.008*q),gold),text("mono",w*.43,h*(top-.015),w*.14,"ZV",s*.032,surface,"800"),text("brand",w*.18,h*(top+.20),w*.64,brand,s*.052,ink,"800"),text("tag",w*.24,h*(top+.34),w*.52,tag,s*.019,ink,"600")]
    elif typ==3:
        o += [text("mono",w*left,h*(top-.10),w*.24,"Z",s*(.115+.01*q),gold,"800","left"),text("brand",w*(left+.25),h*(top+.03),w*(width-.25),brand,s*.047,ink,"800","left"),text("tag",w*(left+.25),h*(top+.18),w*.40,tag,s*.018,ink,"600","left")]
    elif typ==4:
        o += [text("num",w*left,h*(top-.07),w*.18,str(idx+1).zfill(2),s*.072,gold,"800","left"),line("v",w*(left+.22),h*(top-.04),w*(left+.22),h*(top+.31),gold,3),text("brand",w*(left+.28),h*top,w*(width-.28),brand,s*.045,ink,"800","left"),text("tag",w*(left+.28),h*(top+.17),w*.38,tag,s*.018,ink,"600","left")]
    elif typ==5:
        o += [rect("label",w*.19,h*top,w*.62,h*.28,"rgba(0,0,0,0)",gold,3),text("brand",w*.24,h*(top+.06),w*.52,brand,s*.048,ink,"800"),text("tag",w*.27,h*(top+.18),w*.46,tag,s*.018,gold,"700")]
    elif typ==6:
        o += [text("brand",w*.15,h*top,w*.70,brand,s*.058,ink,"800"),rect("brandbar",w*(.20+.015*q),h*(top+.16),w*(.60-.03*q),h*.045,gold),text("tag",w*.20,h*(top+.24),w*.60,tag,s*.020,ink,"600")]
    elif typ==7:
        o += [line("cornerV",w*left,h*(top-.08),w*left,h*(top+.30),gold,4),line("cornerH",w*left,h*(top-.08),w*(left+.30),h*(top-.08),gold,4),text("brand",w*(left+.07),h*(top+.02),w*(width-.07),brand,s*.049,ink,"800","left"),text("tag",w*(left+.07),h*(top+.19),w*.45,tag,s*.018,ink,"600","left")]
    elif typ==8:
        o += [text("edition",w*.60,h*(top-.09),w*.22,"EDITION "+str(q+1),s*.017,gold,"700","right"),text("brand",w*.18,h*top,w*.64,brand,s*.055,ink,"800","right"),line("r",w*.48,h*(top+.16),w*.82,h*(top+.16),gold,3),text("tag",w*.40,h*(top+.22),w*.42,tag,s*.018,ink,"600","right")]
    else:
        o += [circle("d1",w*.40,h*(top-.02),s*.016,gold),circle("d2",w*.50,h*(top-.02),s*.016,gold),circle("d3",w*.60,h*(top-.02),s*.016,gold),text("brand",w*.17,h*(top+.09),w*.66,brand,s*.054,ink,"800"),text("tag",w*.23,h*(top+.25),w*.54,tag,s*.018,ink,"600")]

    return w,h,o


def build_full_color_lanyard(product,idx):
    """100 editable 6 x 1.25 in full-colour lanyard layouts.

    The lanyard editor is intentionally a short horizontal design face matching
    the source configurator, not a 36-inch manufacturing-length strip.
    25 composition systems x 4 structural treatments = 100 materially distinct
    editable Fabric layouts.
    """
    w,h=1200,250
    palettes=[
        ("#E21D2B","#FFFFFF","#7F1D1D"),("#111111","#FFFFFF","#D4AF37"),
        ("#1268C4","#FFFFFF","#082F6B"),("#ED16C5","#FFFFFF","#86198F"),
        ("#E33632","#FFF7ED","#7F1D1D"),("#0F766E","#FFFFFF","#F59E0B"),
        ("#4C1D95","#FFFFFF","#C4B5FD"),("#172554","#FFFFFF","#60A5FA"),
        ("#166534","#FFFFFF","#FACC15"),("#9F1239","#FFFFFF","#FDA4AF"),
        ("#0E7490","#FFFFFF","#67E8F9"),("#7C2D12","#FFF7ED","#FDBA74"),
        ("#312E81","#FFFFFF","#A5B4FC"),("#3F6212","#FFFFFF","#BEF264"),
        ("#701A75","#FFFFFF","#F0ABFC"),("#334155","#FFFFFF","#CBD5E1"),
        ("#B45309","#FFFFFF","#FDE68A"),("#1E3A8A","#FFFFFF","#93C5FD"),
        ("#065F46","#FFFFFF","#6EE7B7"),("#881337","#FFFFFF","#F9A8D4"),
    ]
    bg,ink,accent=palettes[(idx*7 + idx//5)%len(palettes)]
    system=idx%25
    variant=idx//25
    o=[rect("background",0,0,w,h,bg)]
    # Four structural treatments materially alter the composition, not just colour.
    if variant==0:
        o += [rect("edge_top",0,0,w,16,accent),rect("edge_bottom",0,h-16,w,16,accent)]
    elif variant==1:
        o += [rect("rail_left",0,0,90,h,accent),rect("rail_right",w-90,0,90,h,accent)]
    elif variant==2:
        o += [line("diag_a",0,h*.86,w*.22,0,accent,18),line("diag_b",w*.78,h,w, h*.14,accent,18)]
    else:
        o += [rect("frame",24,24,w-48,h-48,"transparent",accent,5),
              circle("jewel_l",70,h/2,22,accent),circle("jewel_r",w-70,h/2,22,accent)]

    brands=["YOUR BRAND","EVENT CREW","ZEN VIBE","STAFF ACCESS","VIP PASS",
            "YOUR LOGO","TEAM ONE","CONFERENCE","EXHIBITOR","WELCOME"]
    tags=["ADD YOUR LOGO AND MESSAGE","FULL COLOUR • CUSTOM PRINT","EVENT • STAFF • ID",
          "MAKE YOUR BRAND VISIBLE","PREMIUM EVENT LANYARD","SCAN • CONNECT • REMEMBER",
          "YOUR EVENT. YOUR STYLE.","CREW • ACCESS • 2026","CUSTOM MADE FOR YOU","BRAND EVERY MOMENT"]
    brand=brands[(idx*3)%len(brands)]; tag=tags[(idx*7+variant)%len(tags)]
    # 25 different content systems; all stay inside the safe horizontal face.
    mode=system
    if mode==0:
        o += [text("brand",150,64,900,brand,54,ink,"800"),text("tag",220,145,760,tag,20,ink,"600")]
    elif mode==1:
        o += [text("mono",75,54,170,"ZV",78,ink,"900"),line("v",275,45,275,205,accent,5),text("brand",330,64,760,brand,50,ink,"800","left"),text("tag",330,142,650,tag,18,ink,"600","left")]
    elif mode==2:
        o += [circle("seal",155,125,72,accent),text("mono",95,91,120,"ZV",42,bg,"900"),text("brand",280,60,800,brand,54,ink,"800","left"),text("tag",282,145,720,tag,18,ink,"600","left")]
    elif mode==3:
        o += [rect("label",185,46,830,158,"transparent",ink,4),text("brand",235,72,730,brand,48,ink,"800"),text("tag",300,145,600,tag,18,accent,"700")]
    elif mode==4:
        o += [text("brand",95,52,1010,brand,62,ink,"900","left"),line("rule",95,132,620,132,accent,6),text("tag",95,153,850,tag,19,ink,"600","left")]
    elif mode==5:
        o += [text("num",85,38,190,f"{idx+1:02d}",88,accent,"900"),text("brand",300,62,800,brand,50,ink,"800","left"),text("tag",302,143,690,tag,18,ink,"600","left")]
    elif mode==6:
        o += [rect("block",70,48,280,154,accent),text("mono",105,85,210,"YOUR",32,bg,"900"),text("brand",400,65,700,brand,52,ink,"800","left"),text("tag",402,146,650,tag,18,ink,"600","left")]
    elif mode==7:
        o += [circle("dot1",95,70,22,accent),circle("dot2",95,125,14,ink),circle("dot3",95,178,22,accent),text("brand",160,60,900,brand,55,ink,"800","left"),text("tag",162,145,800,tag,19,ink,"600","left")]
    elif mode==8:
        o += [line("toprule",160,58,1040,58,accent,5),text("brand",180,76,840,brand,48,ink,"800"),text("tag",250,145,700,tag,18,ink,"600"),line("bottomrule",160,194,1040,194,accent,5)]
    elif mode==9:
        o += [text("brand",130,45,940,brand,72,ink,"900"),text("tag",330,151,540,tag,17,accent,"700")]
    elif mode==10:
        o += [rect("badge",70,65,220,120,"transparent",accent,5),text("mono",105,91,150,"ID",42,ink,"900"),text("brand",340,65,760,brand,48,ink,"800","left"),text("tag",342,145,690,tag,18,ink,"600","left")]
    elif mode==11:
        o += [line("slash1",70,200,180,50,accent,12),line("slash2",115,200,225,50,ink,5),text("brand",280,66,820,brand,52,ink,"800","left"),text("tag",282,146,720,tag,18,ink,"600","left")]
    elif mode==12:
        o += [circle("orb1",125,125,64,"transparent",ink,5),circle("orb2",125,125,42,"transparent",accent,5),text("brand",245,62,850,brand,52,ink,"800","left"),text("tag",247,145,760,tag,18,ink,"600","left")]
    elif mode==13:
        o += [text("eyebrow",130,45,940,"FULL COLOUR LANYARD",17,accent,"700"),text("brand",130,78,940,brand,54,ink,"900"),text("tag",130,157,940,tag,18,ink,"600")]
    elif mode==14:
        o += [rect("bar",80,52,18,146,accent),text("brand",135,62,930,brand,55,ink,"800","left"),text("tag",137,146,820,tag,18,ink,"600","left")]
    elif mode==15:
        o += [text("brand",100,70,650,brand,52,ink,"800","left"),circle("mark",930,125,70,accent),text("mono",875,96,110,"ZV",38,bg,"900"),text("tag",102,150,680,tag,18,ink,"600","left")]
    elif mode==16:
        o += [text("brand",180,60,840,brand,52,ink,"800"),circle("p1",430,164,8,accent),circle("p2",600,164,8,accent),circle("p3",770,164,8,accent),text("tag",260,183,680,tag,16,ink,"600")]
    elif mode==17:
        o += [rect("topbox",90,40,1020,62,accent),text("brand",130,53,940,brand,35,bg,"900"),text("tag",180,137,840,tag,23,ink,"700")]
    elif mode==18:
        o += [text("mono",90,52,240,brand[:1],90,accent,"900"),text("brand",310,68,790,brand,48,ink,"800","left"),line("r",310,132,950,132,accent,5),text("tag",312,151,700,tag,17,ink,"600","left")]
    elif mode==19:
        o += [circle("c1",120,125,36,accent),circle("c2",190,125,24,ink),circle("c3",245,125,15,accent),text("brand",320,64,760,brand,50,ink,"800","left"),text("tag",322,145,700,tag,18,ink,"600","left")]
    elif mode==20:
        o += [text("brand",150,55,900,brand,50,ink,"800"),rect("key",420,132,360,12,accent),text("tag",250,160,700,tag,18,ink,"600")]
    elif mode==21:
        o += [rect("corner1",70,42,160,10,accent),rect("corner2",70,42,10,85,accent),text("brand",180,70,850,brand,52,ink,"800"),text("tag",260,151,680,tag,18,ink,"600")]
    elif mode==22:
        o += [text("edition",865,45,200,"EDITION "+str(variant+1),16,accent,"700","right"),text("brand",130,72,940,brand,54,ink,"800"),text("tag",230,154,740,tag,18,ink,"600")]
    elif mode==23:
        o += [line("l1",120,70,300,70,accent,5),line("l2",900,180,1080,180,accent,5),text("brand",170,82,860,brand,50,ink,"800"),text("tag",260,155,680,tag,18,ink,"600")]
    else:
        o += [circle("gem",600,50,14,accent),text("brand",150,76,900,brand,52,ink,"800"),text("tag",250,156,700,tag,18,ink,"600"),circle("gem2",600,205,9,accent)]
    return w,h,o

def build_mouse_pad(product,idx):
    """100 premium editable mouse-pad designs; one library shared by Rectangle/Round."""
    w,h=850,700
    # Curated premium palettes: dark ink, warm/light surface, restrained accent.
    palettes=[
        ("#111827","#F8FAFC","#D6A756"),("#102A43","#F7F3EA","#2CB1BC"),
        ("#1F2937","#FFF7ED","#E76F51"),("#3B1D2A","#FFF8F5","#D4A373"),
        ("#0F3D35","#FAF7EE","#C9A227"),("#231942","#F8F5FF","#9F86C0"),
        ("#172554","#EFF6FF","#38BDF8"),("#292524","#FAFAF9","#B08968"),
        ("#3F1D38","#FFF7FB","#E879A9"),("#12263A","#F4F1DE","#E9C46A"),
    ]
    dark,light,accent=palettes[idx%len(palettes)]
    k=idx%25
    edition=idx//25
    # Every design has a full editable surface so the thumbnail and editor read
    # as a finished mouse-pad design rather than sparse business-card artwork.
    o=[rect("surface",0,0,w,h,light)]
    brand=["YOUR BRAND","STUDIO","NORTH & CO.","CREATE","WORKSPACE","SIGNATURE","MADE FOR YOU","YOUR LOGO"][idx%8]
    tag=["MAKE YOUR DESK YOURS","DESIGN • WORK • CREATE","PREMIUM DESK SERIES","CREATE EVERY DAY","YOUR MESSAGE HERE","WORK • PLAY • CREATE"][idx%6]
    mx=55+edition*8
    if k==0:
        o += [rect("left_panel",0,0,210,h,dark),rect("gold_key",210,0,8,h,accent),text("brand",285,245,500,brand,58,dark,"800","left"),text("tag",288,340,450,tag,19,accent,"600","left")]
    elif k==1:
        o += [rect("top_band",0,0,w,155,dark),text("brand",mx,235,w-2*mx,brand,62,dark,"800"),line("rule",300,345,550,345,accent,5),text("tag",mx,390,w-2*mx,tag,19,dark)]
    elif k==2:
        o += [circle("hero",425,270,128,accent),circle("inner",425,270,84,dark),text("mark",330,228,190,brand[:2],54,light,"800"),text("brand",mx,470,w-2*mx,brand,48,dark,"800"),text("tag",mx,540,w-2*mx,tag,17,dark)]
    elif k==3:
        o += [rect("frame",45,45,760,610,"rgba(0,0,0,0)",dark,5),rect("frame2",66,66,718,568,"rgba(0,0,0,0)",accent,2),text("brand",mx,260,w-2*mx,brand,60,dark,"800"),text("tag",mx,365,w-2*mx,tag,18,accent)]
    elif k==4:
        o += [rect("bottom",0,500,w,200,dark),rect("accent_bar",0,480,w,20,accent),text("brand",mx,190,w-2*mx,brand,64,dark,"800","left"),text("tag",mx,310,w-2*mx,tag,20,dark,"600","left")]
    elif k==5:
        o += [rect("rail",70,0,92,h,dark),circle("seal",520,240,92,accent),text("mark",458,210,125,brand[:2],38,dark,"800"),text("brand",235,410,520,brand,55,dark,"800","left"),text("tag",237,500,470,tag,18,accent,"600","left")]
    elif k==6:
        o += [rect("dark_surface",0,0,w,h,dark),circle("halo",425,285,155,accent),circle("logo",425,285,102,light),text("mark",345,245,160,brand[:2],50,dark,"900"),text("brand",mx,500,w-2*mx,brand,48,light,"800")]
    elif k==7:
        o += [rect("band",0,205,w,290,dark),line("top",0,190,w,190,accent,10),line("bottom",0,505,w,505,accent,10),text("brand",mx,280,w-2*mx,brand,62,light,"800"),text("tag",mx,390,w-2*mx,tag,18,accent)]
    elif k==8:
        o += [rect("corner1",0,0,250,135,dark),rect("corner2",600,565,250,135,accent),text("brand",mx,270,w-2*mx,brand,62,dark,"800"),text("tag",mx,380,w-2*mx,tag,18,dark)]
    elif k==9:
        o += [circle("dot1",120,120,62,accent),circle("dot2",735,575,95,dark),text("brand",mx,265,w-2*mx,brand,60,dark,"800"),text("tag",mx,380,w-2*mx,tag,18,accent)]
    elif k==10:
        o += [rect("right_panel",610,0,240,h,dark),rect("right_key",590,0,20,h,accent),text("brand",mx,235,500,brand,60,dark,"800","left"),text("tag",mx,350,470,tag,19,accent,"600","left")]
    elif k==11:
        o += [line("r1",90,180,760,180,accent,7),line("r2",90,520,760,520,dark,7),text("brand",mx,275,w-2*mx,brand,64,dark,"800"),text("tag",mx,395,w-2*mx,tag,18,dark)]
    elif k==12:
        o += [rect("dark_surface",0,0,w,h,dark),circle("seal",425,285,145,accent),circle("seal2",425,285,118,dark),text("mark",330,240,190,brand[:2],58,light,"900"),text("brand",mx,505,w-2*mx,brand,45,light,"800")]
    elif k==13:
        o += [rect("panel",85,80,680,540,dark),rect("inner",105,100,640,500,"rgba(0,0,0,0)",accent,3),text("brand",150,250,550,brand,58,light,"800"),text("tag",150,365,550,tag,18,accent)]
    elif k==14:
        o += [rect("top_key",0,0,w,48,accent),rect("bottom_key",0,652,w,48,dark),text("brand",mx,270,w-2*mx,brand,64,dark,"800"),text("tag",mx,390,w-2*mx,tag,18,accent)]
    elif k==15:
        o += [circle("orb1",170,200,115,accent),circle("orb2",690,520,155,dark),text("brand",mx,295,w-2*mx,brand,60,dark,"800"),text("tag",mx,405,w-2*mx,tag,18,dark)]
    elif k==16:
        o += [rect("tile1",65,75,210,165,dark),rect("tile2",575,460,210,165,accent),text("brand",mx,285,w-2*mx,brand,60,dark,"800"),text("tag",mx,395,w-2*mx,tag,18,dark)]
    elif k==17:
        o += [line("slash1",80,610,300,75,accent,28),line("slash2",155,625,375,90,dark,14),text("brand",360,245,420,brand,54,dark,"800","left"),text("tag",362,355,380,tag,17,accent,"600","left")]
    elif k==18:
        o += [rect("label",105,160,640,380,accent),rect("label_inner",125,180,600,340,light),text("brand",165,270,520,brand,56,dark,"800"),text("tag",165,380,520,tag,18,dark)]
    elif k==19:
        o += [circle("c1",135,350,90,dark),circle("c2",280,350,58,accent),text("brand",385,275,400,brand,52,dark,"800","left"),text("tag",387,385,365,tag,17,accent,"600","left")]
    elif k==20:
        o += [rect("dark_surface",0,0,w,h,dark),rect("gold_frame",55,55,740,590,"rgba(0,0,0,0)",accent,4),text("brand",mx,260,w-2*mx,brand,62,light,"800"),text("tag",mx,380,w-2*mx,tag,18,accent)]
    elif k==21:
        o += [rect("header",0,0,w,105,dark),circle("logo",425,275,95,accent),text("mark",365,242,120,brand[:2],42,dark,"900"),text("brand",mx,430,w-2*mx,brand,52,dark,"800"),text("tag",mx,515,w-2*mx,tag,17,dark)]
    elif k==22:
        o += [rect("side_a",0,0,115,h,dark),rect("side_b",735,0,115,h,accent),text("brand",mx,270,w-2*mx,brand,62,dark,"800"),text("tag",mx,385,w-2*mx,tag,18,dark)]
    elif k==23:
        o += [line("diag1",0,620,330,0,accent,42),line("diag2",65,700,395,80,dark,18),text("brand",380,245,400,brand,55,dark,"800","left"),text("tag",382,360,370,tag,17,accent,"600","left")]
    else:
        o += [rect("dark_surface",0,0,w,h,dark),circle("ring",425,300,170,"rgba(0,0,0,0)",accent,8),circle("dot",425,300,25,accent),text("brand",mx,475,w-2*mx,brand,48,light,"800"),text("tag",mx,555,w-2*mx,tag,16,accent)]
    # Four editions are structural, not recolours: each changes the composition.
    if edition==1:
        o += [rect("edition_top",110,92,300,10,accent),circle("edition_dot",735,110,20,accent)]
    elif edition==2:
        o += [rect("edition_side",760,120,9,420,accent),line("edition_rule",120,585,470,585,dark,5)]
    elif edition==3:
        o += [circle("edition_a",105,585,28,accent),circle("edition_b",745,105,18,dark),line("edition_key",585,600,745,600,accent,7)]
    return w,h,o

def build_name_badge(product,idx):
    """100 editable round name-badge compositions for the 10 x 10 editor workspace."""
    w=h=1000
    # Artwork occupies the front badge only; the physical badge colour is a
    # locked editor mockup controlled independently by the customer colour choice.
    cx,cy,r=585,525,205
    darks=["#111827","#172554","#3B0764","#052E16","#4C0519","#1F2937","#312E81","#134E4A","#7C2D12","#701A75"]
    accents=["#F59E0B","#2563EB","#65A30D","#DB2777","#7C3AED","#0284C7","#EA580C","#059669","#9333EA","#CA8A04"]
    ink,accent=darks[idx%len(darks)],accents[idx%len(accents)]
    k=idx%20; q=idx//20
    # Decorative clipart primitives stay editable and are clipped to the front badge by editor.js.
    clipx=cx + (-1 if idx%2==0 else 1) * (112 + (idx%3)*8)
    clipy=cy + [-108,-72,72,108,0][q]
    brand=["YOUR DESIGN","YOUR NAME","YOUR BRAND","HELLO","TEAM","STAFF","EVENT","CREW","WELCOME","YOUR LOGO"][idx%10]
    sub=["NAME BADGE","YOUR TITLE HERE","COMPANY NAME","EST. 2026","EVENT TEAM","YOUR MESSAGE","MEMBER","STAFF ACCESS"][idx%8]
    # Transparent template: the selected red/blue/green/pink/purple badge body
    # remains visible underneath every design.
    o=[]
    if k==0:o=[text("brand",cx-r*.72,cy-42,r*1.44,brand,64,ink,"900"),text("sub",cx-r*.62,cy+34,r*1.24,sub,25,accent,"800")]
    elif k==1:o=[circle("mark",cx,cy-55,42,accent),text("initial",cx-40,cy-77,80,brand[:2],28,"#222","900"),text("brand",cx-r*.68,cy+15,r*1.36,brand,54,ink,"900")]
    elif k==2:o=[line("rule",cx-r*.62,cy-18,cx+r*.62,cy-18,accent,7),text("brand",cx-r*.68,cy-90,r*1.36,brand,54,ink,"900"),text("sub",cx-r*.58,cy+18,r*1.16,sub,25,ink,"700")]
    elif k==3:o=[text("hello",cx-r*.65,cy-112,r*1.3,"HELLO",22,accent,"800"),text("brand",cx-r*.72,cy-48,r*1.44,brand,64,ink,"900"),line("rule",cx-r*.40,cy+32,cx+r*.40,cy+32,accent,4),text("sub",cx-r*.55,cy+55,r*1.1,sub,23,ink,"700")]
    elif k==4:o=[circle("ring",cx,cy,145,"rgba(0,0,0,0)",accent,5),text("brand",cx-130,cy-45,260,brand,54,ink,"900"),text("sub",cx-115,cy+24,230,sub,23,accent,"800")]
    elif k==5:o=[text("mono",cx-r*.62,cy-112,r*.55,brand[:2],78,accent,"900","left"),text("brand",cx-r*.18,cy-70,r*.78,brand,47,ink,"900","left"),text("sub",cx-r*.18,cy-10,r*.75,sub,22,ink,"700","left")]
    elif k==6:o=[line("v",cx-72,cy-100,cx-72,cy+105,accent,6),text("brand",cx-42,cy-70,190,brand,50,ink,"900","left"),text("sub",cx-42,cy+5,180,sub,23,accent,"800","left")]
    elif k==7:o=[circle("dot1",cx-85,cy-85,13,accent),circle("dot2",cx+85,cy+85,13,accent),text("brand",cx-135,cy-45,270,brand,56,ink,"900"),text("sub",cx-120,cy+30,240,sub,23,ink,"700")]
    elif k==8:o=[text("brand",cx-140,cy-92,280,brand,60,ink,"900"),rect("label",cx-115,cy-15,230,48,accent),text("sub",cx-105,cy-5,210,sub,17,"#252525","800")]
    elif k==9:o=[line("top",cx-100,cy-80,cx+100,cy-80,accent,4),text("brand",cx-145,cy-42,290,brand,58,ink,"900"),line("bottom",cx-100,cy+45,cx+100,cy+45,accent,4),text("sub",cx-110,cy+62,220,sub,22,ink,"700")]
    elif k==10:o=[text("num",cx-145,cy-105,100,str(idx+1).zfill(2),55,accent,"900","left"),text("brand",cx-35,cy-72,170,brand,48,ink,"900","left"),text("sub",cx-35,cy-5,165,sub,21,ink,"700","left")]
    elif k==11:o=[circle("seal",cx,cy-30,72,accent),text("mono",cx-60,cy-58,120,brand[:2],38,"#222","900"),text("sub",cx-115,cy+65,230,sub,18,ink,"700")]
    elif k==12:o=[text("brand",cx-145,cy-78,290,brand,55,ink,"900"),circle("d1",cx-45,cy+15,8,accent),circle("d2",cx,cy+15,8,accent),circle("d3",cx+45,cy+15,8,accent),text("sub",cx-115,cy+52,230,sub,22,ink,"700")]
    elif k==13:o=[rect("frame",cx-145,cy-120,290,240,"rgba(0,0,0,0)",accent,4),text("brand",cx-125,cy-55,250,brand,52,ink,"900"),text("sub",cx-110,cy+25,220,sub,22,ink,"700")]
    elif k==14:o=[text("small",cx-120,cy-100,240,"OFFICIAL",22,accent,"900"),text("brand",cx-145,cy-48,290,brand,60,ink,"900"),text("sub",cx-115,cy+40,230,sub,22,ink,"700")]
    elif k==15:o=[line("slash",cx-125,cy+95,cx-35,cy-105,accent,16),text("brand",cx-5,cy-60,145,brand,46,ink,"900","left"),text("sub",cx-5,cy+10,140,sub,15,ink,"600","left")]
    elif k==16:o=[circle("a",cx-105,cy-70,24,accent),circle("b",cx+112,cy+78,16,accent),text("brand",cx-140,cy-35,280,brand,56,ink,"900"),text("sub",cx-110,cy+40,220,sub,22,ink,"700")]
    elif k==17:o=[text("brand",cx-140,cy-90,280,brand,41,ink,"800"),line("r1",cx-120,cy-20,cx+120,cy-20,accent,8),line("r2",cx-80,cy+5,cx+80,cy+5,ink,3),text("sub",cx-110,cy+42,220,sub,21,ink,"700")]
    elif k==18:o=[circle("logo",cx,cy-58,48,"rgba(0,0,0,0)",accent,5),text("mono",cx-40,cy-78,80,brand[:2],27,ink,"900"),text("brand",cx-135,cy+15,270,brand,38,ink,"800"),text("sub",cx-105,cy+70,210,sub,15,accent,"700")]
    else:o=[text("brand",cx-145,cy-70,290,brand,46,ink,"900"),text("amp",cx-35,cy-5,70,"•",35,accent,"900"),text("sub",cx-115,cy+50,230,sub,23,ink,"700")]
    # Add editable vector-style clipart to every design: stars, petals, sparkles,
    # geometric marks and mini emblems. These are Fabric primitives, not flattened images.
    motif=idx%5
    if motif==0:
        o += [circle("clip_dot",clipx,clipy,12,accent),line("clip_ray1",clipx-22,clipy,clipx+22,clipy,accent,4),line("clip_ray2",clipx,clipy-22,clipx,clipy+22,accent,4)]
    elif motif==1:
        o += [circle("clip_petal1",clipx-10,clipy,13,accent),circle("clip_petal2",clipx+10,clipy,13,accent),circle("clip_core",clipx,clipy,7,ink)]
    elif motif==2:
        o += [rect("clip_tile",clipx-18,clipy-18,36,36,"rgba(0,0,0,0)",accent,4),circle("clip_core",clipx,clipy,7,accent)]
    elif motif==3:
        o += [line("clip_x1",clipx-17,clipy-17,clipx+17,clipy+17,accent,5),line("clip_x2",clipx+17,clipy-17,clipx-17,clipy+17,accent,5),circle("clip_core",clipx,clipy,5,ink)]
    else:
        o += [circle("clip_ring",clipx,clipy,19,"rgba(0,0,0,0)",accent,5),circle("clip_dot",clipx,clipy,6,accent)]
    # Five structural editions add different peripheral details, not recolours.
    if q==1:o += [circle("edition",cx-135,cy+110,10,accent)]
    elif q==2:o += [line("edition",cx-120,cy+112,cx+10,cy+112,accent,5)]
    elif q==3:o += [circle("edition1",cx-125,cy+108,7,accent),circle("edition2",cx-95,cy+108,7,accent),circle("edition3",cx-65,cy+108,7,accent)]
    elif q==4:o += [line("edition1",cx+35,cy-112,cx+130,cy-112,accent,5),circle("edition2",cx+140,cy-112,7,accent)]
    return w,h,o



def build_aluminum_bottle_opener(product, idx):
    """Editable logo artwork, kept strictly inside the opener's flat top face.

    The photo is a locked reference asset. No raster artwork is included here.
    All 100 template entries contain selectable Fabric vector/text objects.
    """
    w, h = 1200, 789
    ink, light, accent = PALETTES[(idx * 7) % len(PALETTES)]
    # Same geometry as the product's 27.5/39.9/41.7/15.8% print area.
    # Leave 12% inset on each side so no object touches the curved edges.
    x, y, aw, ah = 390, 347, 375, 60
    layout, edition = idx % 20, idx // 20
    title = "YOUR BRAND"
    o = []
    def t(key, dx, dy, width, value, size=36, color=None, weight="900"):
        o.append(text(key, x + dx, y + dy, width, value, size,
                      color or ink, weight))
    def rule(key, x1, y1, x2, y2, color=None, thickness=3):
        o.append(line(key, x+x1, y+y1, x+x2, y+y2,
                      color or accent, thickness))
    def disk(key, cx, cy, radius, fill=None):
        o.append(circle(key, x+cx, y+cy, radius, fill or accent))
    if layout == 0:
        t("brand", 0, 36, aw, title, 36)
    elif layout == 1:
        disk("symbol", 35, 36, 36); t("brand", 75, 36, 290, title, 36)
    elif layout == 2:
        t("monogram", 8, 25, 70, "ZV", 34, accent); rule("divider", 88, 7, 88, 66); t("brand", 105, 36, 265, title, 36)
    elif layout == 3:
        rule("upper", 10, 7, 365, 7); t("brand", 0, 36, aw, title, 36); rule("lower", 10, 66, 365, 66)
    elif layout == 4:
        o.append(rect("outline", x+5, y+5, 365, 62, "rgba(0,0,0,0)", accent, 3)); t("brand", 36, 36, 335, "YOUR LOGO", 36)
    elif layout == 5:
        t("first", 0, 4, aw, "YOUR", 25); t("second", 0, 36, aw, "BRAND", 30, accent)
    elif layout == 6:
        disk("seal", 185, 36, 30); t("initial", 155, 36, 60, "ZV", 36, light)
    elif layout == 7:
        o.append(rect("rail", x+6, y+7, 8, 57, accent)); t("brand", 36, 10, 340, title, 36); t("subtitle", 36, 45, 340, "PROMOTIONAL", 25, accent)
    elif layout == 8:
        rule("slash1", 25, 64, 48, 8, accent, 6); rule("slash2", 45, 64, 78, 8, ink, 4); t("brand", 90, 36, 275, title, 36)
    elif layout == 9:
        disk("dot_left", 25, 36, 9); disk("dot_right", 357, 36, 9); t("brand", 42, 36, 290, title, 36)
    elif layout == 10:
        o.append(rect("badge", x+5, y+7, 65, 58, accent)); t("badge_text", 9, 36, 58, "VIP", 25, light); t("brand", 80, 36, 285, title, 36)
    elif layout == 11:
        t("brand", 0, 9, aw, title, 36); t("website", 0, 48, aw, "YOURCOMPANY.CA", 25, accent)
    elif layout == 12:
        disk("mark", 40, 36, 36); t("letter", 36, 25, 38, "Z", 36, light); t("brand", 85, 36, 280, title, 36)
    elif layout == 13:
        rule("upper", 0, 6, 375, 6, ink, 2); t("brand", 0, 36, aw, title, 36, accent); rule("lower", 0, 67, 375, 67, ink, 2)
    elif layout == 14:
        o.append(rect("monogram_panel", x+5, y+6, 60, 60, accent)); t("mono", 8, 36, 55, "ZV", 25, light); t("brand", 80, 36, 285, title, 36)
    elif layout == 15:
        t("overline", 0, 6, aw, "PREMIUM • CUSTOM", 25, accent); t("brand", 0, 36, aw, title, 36)
    elif layout == 16:
        disk("bubble1", 36, 36, 25); disk("bubble2", 54, 49, 25, ink); t("brand", 85, 36, 280, title, 36)
    elif layout == 17:
        o.append(rect("border", x+5, y+5, 365, 62, "rgba(0,0,0,0)", ink, 2)); t("brand", 25, 36, 343, title, 36)
    elif layout == 18:
        t("serial", 5, 25, 85, f"{idx+1:02d}", 30, accent); rule("divider", 90, 8, 90, 65, ink); t("brand", 104, 36, 260, title, 36)
    else:
        t("brand", 0, 10, aw, title, 36); o.append(rect("underline", x+80, y+53, 215, 6, accent))
    # Keep every editable element within the same printable rectangle.
    # Five full composition treatments rather than tiny decorative variants.
    if edition == 1:
        o.append(rect("edition_left_panel", x, y, 58, ah, "rgba(255,255,255,0.20)", accent, 2))
        o.append(text("edition_label", x+5, y+26, 48, "01", 25, ink, "900"))
    elif edition == 2:
        o.append(rect("edition_top_band", x, y, aw, 10, accent))
        o.append(rect("edition_bottom_band", x, y+ah-10, aw, 10, accent))
    elif edition == 3:
        o.append(line("edition_diagonal_1", x+aw-55, y+4, x+aw-15, y+ah-4, accent, 4))
        o.append(line("edition_diagonal_2", x+aw-75, y+4, x+aw-35, y+ah-4, accent, 3))
    elif edition == 4:
        o.append(rect("edition_right_panel", x+aw-65, y+4, 61, ah-8, "rgba(0,0,0,0)", accent, 3))
        o.append(text("edition_label", x+aw-61, y+27, 53, "EST.", 25, ink, "900"))
    return w, h, o


def build_paper_wristband(product, idx):
    """100 editable, full-face 10 x .75 inch event wristband layouts.

    Ten fundamentally different horizontal architectures combined with ten
    substantial emblem systems. No photo/mockup is embedded in the artwork.
    """
    w,h=1200,90
    darks=["#1235C8","#111827","#6D28D9","#065F46","#9F1239",
           "#0E7490","#7C2D12","#312E81","#334155","#14532D"]
    accents=["#FDE047","#FB7185","#67E8F9","#FBBF24","#A7F3D0",
             "#C4B5FD","#FDBA74","#86EFAC","#F9A8D4","#93C5FD"]
    bg=darks[idx%10]
    accent=accents[(idx//10+idx)%10]
    white="#FFFFFF"
    k=idx%10
    art=idx//10
    o=[rect("print_background",0,0,w,h,bg)]
    title=["ADD YOUR LOGO","EVENT ACCESS","VIP ADMISSION","YOUR BRAND",
           "ALL ACCESS","FESTIVAL PASS","EXCLUSIVE ENTRY","EVENT CREW",
           "WELCOME","CUSTOM WRISTBAND"][idx%10]
    small=["SCAN TO ENTER","EVENT 2026","YOUR MESSAGE","ADMIT ONE",
           "OFFICIAL PASS","PREMIUM ACCESS","STAFF & GUEST","YOUR COMPANY",
           "ENTRY BAND","CUSTOM PRINT"][idx%10]
    # Structural architecture controls where typography and graphics live.
    if k==0:
        o += [text("title",330,20,690,title,44,white,"900")]
    elif k==1:
        o += [rect("left_plate",0,0,260,h,accent),
              text("title",300,17,800,title,42,white,"900","left")]
    elif k==2:
        o += [rect("right_plate",950,0,250,h,accent),
              text("title",100,15,760,title,44,white,"900","left")]
    elif k==3:
        o += [line("top_rule",100,9,1100,9,accent,5),
              text("title",250,19,700,title,41,white,"900"),
              line("bottom_rule",100,82,1100,82,accent,5)]
    elif k==4:
        o += [rect("central_label",270,8,660,74,white),
              text("title",310,22,580,title,37,bg,"900")]
    elif k==5:
        o += [rect("diagonal_panel",0,0,150,h,accent),
              line("slash",165,0,230,90,accent,18),
              text("title",280,19,800,title,43,white,"900","left")]
    elif k==6:
        o += [rect("edge_top",0,0,w,14,accent),
              text("title",250,27,700,title,38,white,"900")]
    elif k==7:
        o += [rect("edge_bottom",0,76,w,14,accent),
              text("title",310,16,630,title,39,white,"900","left")]
    elif k==8:
        o += [rect("double_left",0,0,115,h,accent),
              rect("double_right",1085,0,115,h,accent),
              text("title",230,17,740,title,42,white,"900")]
    else:
        o += [rect("outlined_label",280,11,640,68,"rgba(0,0,0,0)",accent,4),
              text("title",315,23,570,title,36,white,"900")]

    # The art is an actual editable illustration / badge, not a tiny cosmetic dot.
    # Each family changes the overall reading of the band.
    if art==0: # ticket / serial
        o += [rect("ticket",60,14,145,62,"rgba(0,0,0,0)",white,3),
              text("ticket_number",72,28,120,"12345",25,white,"900")]
    elif art==1: # checkerboard
        for j in range(12):
            o += [rect("checker_"+str(j),45+(j%6)*25,17+(j//6)*26,24,25,
                       white if (j+j//6)%2 else accent)]
    elif art==2: # circular seal
        o += [circle("seal",125,45,37,accent),
              circle("seal_ring",125,45,30,"rgba(0,0,0,0)",bg,3),
              text("seal_text",95,34,60,"VIP",25,bg,"900")]
    elif art==3: # lightning zigzag
        for j in range(4):
            x=38+j*45
            o += [line("bolt_a_"+str(j),x,65,x+22,20,accent,6),
                  line("bolt_b_"+str(j),x+22,20,x+45,65,white,5)]
    elif art==4: # star medal
        o += [circle("medal",115,45,35,accent),
              text("medal_text",85,30,60,"★",29,bg,"900"),
              line("medal_l",65,18,85,8,white,4),
              line("medal_r",145,8,165,18,white,4)]
    elif art==5: # barcode-style admission
        for j in range(14):
            o += [rect("barcode_"+str(j),40+j*11,19,3+(j%3)*2,46,white)]
        o += [text("serial",43,69,155,"ENTRY 2026",10,accent,"700")]
    elif art==6: # crown and heraldry
        o += [line("crown_a",55,59,72,20,accent,7),
              line("crown_b",72,20,105,48,white,7),
              line("crown_c",105,48,137,20,accent,7),
              line("crown_d",137,20,158,59,white,7),
              line("crown_base",55,64,158,64,accent,7)]
    elif art==7: # concentric tech circles
        for j in range(3):
            o += [circle("orbit_"+str(j),115,45,16+j*12,"rgba(0,0,0,0)",
                         accent if j%2 else white,3)]
        o += [circle("orbit_core",115,45,8,accent)]
    elif art==8: # chevron stripe
        for j in range(4):
            x=32+j*40
            o += [line("chev_a_"+str(j),x,18,x+25,45,accent,7),
                  line("chev_b_"+str(j),x+25,45,x,72,white,7)]
    else: # rosette / floral emblem
        for j in range(8):
            import math
            angle=math.pi*j/4
            o += [circle("petal_"+str(j),115+24*math.cos(angle),
                         45+24*math.sin(angle),12,accent if j%2 else white)]
        o += [circle("rosette_core",115,45,14,bg),
              text("rosette_mark",105,38,20,"Z",15,white,"900")]

    # A visible secondary content lockup in a location separate from the hero.
    if k in (0,3,6,8):
        o += [text("sub",1020,37,160,small,12,white,"700")]
    elif k in (1,5,7):
        o += [text("sub",920,66,220,small,12,accent,"700")]
    else:
        o += [text("sub",1010,63,165,small,12,white,"700")]
    return w,h,o

def build_golf_ball(product,idx):
    """100 materially different editable golf-ball compositions.

    A template is identified by a unique structure + motif pairing (10 x 10).
    Colour is decoration only and is never used to manufacture extra designs.
    All artwork stays inside the configured logo region over the locked ball mockup.
    """
    import math
    w,h=canvas(product)
    cx,cy=w*.50,h*.50
    pw,ph=w*.42,h*.36
    left,top=cx-pw/2,cy-ph/2
    dark,light,accent=PALETTES[(idx*7 + idx//10*3)%len(PALETTES)]
    ink=dark
    fs=max(18,min(w,h)*.052)
    layout=idx%10
    motif=(idx//10 + (idx%10)*3)%10
    o=[]

    # Ten genuinely different information architectures.
    if layout==0: # centred wordmark
        o += [text("brand",left,top+ph*.28,pw,"YOUR BRAND",fs,ink,"900"),
              line("rule",left+pw*.24,top+ph*.67,left+pw*.76,top+ph*.67,accent,5),
              text("tag",left,top+ph*.73,pw,"GOLF CLUB",fs*.28,ink,"700")]
    elif layout==1: # left monogram / right wordmark
        o += [circle("seal",left+pw*.20,cy,ph*.20,accent),
              text("mono",left+pw*.09,cy-fs*.42,pw*.22,"ZV",fs*.72,light,"900"),
              text("brand",left+pw*.44,top+ph*.30,pw*.52,"YOUR\nBRAND",fs*.58,ink,"900","left")]
    elif layout==2: # crest
        o += [circle("crest_outer",cx,cy,ph*.30,"rgba(0,0,0,0)",accent,5),
              circle("crest_inner",cx,cy,ph*.22,"rgba(0,0,0,0)",ink,3),
              text("crest_mark",left+pw*.30,top+ph*.28,pw*.40,"ZV",fs*.78,ink,"900"),
              text("crest_tag",left+pw*.20,top+ph*.69,pw*.60,"EST. 2026",fs*.24,accent,"800")]
    elif layout==3: # editorial stacked
        o += [text("eyebrow",left,top+ph*.14,pw,"PREMIUM GOLF",fs*.22,accent,"800"),
              text("brand",left,top+ph*.31,pw,"YOUR",fs*.66,ink,"700"),
              text("brand2",left,top+ph*.52,pw,"BRAND",fs*.86,ink,"900")]
    elif layout==4: # vertical rail
        o += [rect("rail",left+pw*.08,top+ph*.12,pw*.045,ph*.76,accent),
              text("brand",left+pw*.23,top+ph*.25,pw*.70,"YOUR BRAND",fs*.62,ink,"900","left"),
              text("tag",left+pw*.23,top+ph*.58,pw*.62,"PLAY • DRIVE • WIN",fs*.24,accent,"800","left")]
    elif layout==5: # framed label
        o += [rect("frame",left+pw*.08,top+ph*.14,pw*.84,ph*.72,"rgba(0,0,0,0)",accent,5),
              text("brand",left+pw*.14,top+ph*.31,pw*.72,"YOUR LOGO",fs*.68,ink,"900"),
              text("tag",left+pw*.18,top+ph*.62,pw*.64,"SIGNATURE SERIES",fs*.22,accent,"800")]
    elif layout==6: # oversized initials
        o += [text("initial",left+pw*.03,top+ph*.18,pw*.48,"YB",fs*1.10,accent,"900","left"),
              line("divider",cx,top+ph*.18,cx,top+ph*.82,ink,4),
              text("brand",cx+pw*.08,top+ph*.31,pw*.38,"YOUR\nBRAND",fs*.45,ink,"900","left")]
    elif layout==7: # top/bottom rules
        o += [line("top_rule",left+pw*.10,top+ph*.18,left+pw*.90,top+ph*.18,accent,5),
              text("brand",left,top+ph*.31,pw,"YOUR BRAND",fs*.72,ink,"900"),
              line("bottom_rule",left+pw*.10,top+ph*.70,left+pw*.90,top+ph*.70,ink,3)]
    elif layout==8: # asymmetric badge
        o += [circle("badge",left+pw*.22,top+ph*.34,ph*.16,accent),
              text("badge_mark",left+pw*.12,top+ph*.27,pw*.20,"19",fs*.46,light,"900"),
              text("brand",left+pw*.43,top+ph*.27,pw*.52,"YOUR CLUB",fs*.58,ink,"900","left"),
              text("tag",left+pw*.43,top+ph*.58,pw*.45,"GOLF",fs*.24,accent,"800","left")]
    else: # diagonal sport lockup
        o += [line("slash_a",left+pw*.13,top+ph*.80,left+pw*.35,top+ph*.18,accent,8),
              line("slash_b",left+pw*.24,top+ph*.80,left+pw*.46,top+ph*.18,ink,4),
              text("brand",left+pw*.43,top+ph*.28,pw*.52,"DRIVE",fs*.70,ink,"900","left"),
              text("tag",left+pw*.43,top+ph*.61,pw*.48,"YOUR BRAND",fs*.23,accent,"800","left")]

    # Ten distinct editable vector-art directions. Combined bijectively with the
    # structures above, every one of the 100 templates has a unique composition.
    if motif==0: # four-point sparkle
        x,y=left+pw*.84,top+ph*.24
        o += [line("spark_v",x,y-ph*.09,x,y+ph*.09,accent,4),
              line("spark_h",x-pw*.07,y,x+pw*.07,y,accent,4),circle("spark",x,y,ph*.025,ink)]
    elif motif==1: # golf flag
        x=left+pw*.15
        o += [line("flag_pole",x,top+ph*.22,x,top+ph*.72,ink,4),
              line("flag_top",x,top+ph*.22,x+pw*.16,top+ph*.31,accent,5),
              line("flag_bottom",x+pw*.16,top+ph*.31,x,top+ph*.38,accent,5)]
    elif motif==2: # laurel
        for q in range(4):
            yy=top+ph*(.30+q*.13)
            o += [circle("leaf_l_"+str(q),left+pw*(.12+q*.025),yy,ph*.035,accent),
                  circle("leaf_r_"+str(q),left+pw*(.88-q*.025),yy,ph*.035,accent)]
    elif motif==3: # crown
        y=top+ph*.17
        o += [line("crown1",cx-pw*.13,y+ph*.12,cx-pw*.07,y,accent,5),
              line("crown2",cx-pw*.07,y,cx,y+ph*.10,accent,5),
              line("crown3",cx,y+ph*.10,cx+pw*.07,y,accent,5),
              line("crown4",cx+pw*.07,y,cx+pw*.13,y+ph*.12,accent,5)]
    elif motif==4: # orbit
        o += [circle("orbit",left+pw*.84,top+ph*.70,ph*.10,"rgba(0,0,0,0)",accent,4),
              circle("orbit_dot",left+pw*.91,top+ph*.63,ph*.025,ink)]
    elif motif==5: # diamond
        x,y=left+pw*.16,top+ph*.72
        o += [line("dia1",x,y-ph*.09,x+pw*.07,y,accent,5),
              line("dia2",x+pw*.07,y,x,y+ph*.09,accent,5),
              line("dia3",x,y+ph*.09,x-pw*.07,y,accent,5),
              line("dia4",x-pw*.07,y,x,y-ph*.09,accent,5)]
    elif motif==6: # triple speed marks
        for q in range(3):
            y=top+ph*(.72+q*.055)
            o += [line("speed_"+str(q),left+pw*(.67+q*.03),y,left+pw*(.91-q*.02),y,accent,3+q)]
    elif motif==7: # mini target
        x,y=left+pw*.15,top+ph*.24
        o += [circle("target1",x,y,ph*.085,"rgba(0,0,0,0)",accent,4),
              circle("target2",x,y,ph*.045,"rgba(0,0,0,0)",ink,3),circle("target3",x,y,ph*.015,accent)]
    elif motif==8: # corner brackets
        o += [line("br_t",left+pw*.07,top+ph*.10,left+pw*.25,top+ph*.10,accent,4),
              line("br_l",left+pw*.07,top+ph*.10,left+pw*.07,top+ph*.28,accent,4),
              line("br_b",left+pw*.75,top+ph*.90,left+pw*.93,top+ph*.90,accent,4),
              line("br_r",left+pw*.93,top+ph*.72,left+pw*.93,top+ph*.90,accent,4)]
    else: # championship stars
        for q,(dx,dy) in enumerate([(-.09,0),(0,-.035),(.09,0)]):
            x=cx+pw*dx; y=top+ph*(.16+dy)
            o += [circle("star_"+str(q),x,y,ph*(.022+.006*q),accent if q!=1 else ink)]

    # Unique signature mark per template. This is deliberately small and does
    # not create identity by itself; it prevents accidental JSON-equivalent rows.
    o += [text("design_id",left+pw*.78,top+ph*.82,pw*.18,f"{idx+1:02d}",max(10,fs*.16),accent,"700","right")]
    return w,h,o

def build_name_plate(product,idx):
    """100 editable 10 x 2 in office door name-plate designs.

    Artwork is authored across the actual horizontal plate face, matching the
    source configurator instead of the generic promotional-product layout.
    """
    w,h=1200,240
    palettes=[
        ("#111827","#FFFFFF","#06B6D4","#F59E0B"),("#172554","#FFFFFF","#38BDF8","#FACC15"),
        ("#18181B","#FFFFFF","#E11D48","#F59E0B"),("#0F3D3E","#FFFFFF","#2DD4BF","#FB7185"),
        ("#3B0764","#FFFFFF","#C084FC","#22D3EE"),("#7F1D1D","#FFFFFF","#F97316","#FACC15"),
        ("#0C4A6E","#FFFFFF","#06B6D4","#A3E635"),("#312E81","#FFFFFF","#818CF8","#EC4899"),
        ("#064E3B","#FFFFFF","#10B981","#FBBF24"),("#292524","#FFFFFF","#A8A29E","#F97316"),
    ]
    bg,ink,a1,a2=palettes[(idx*3)%len(palettes)]
    layout=idx%20; edition=idx//20
    o=[rect("plate_bg",0,0,w,h,bg)]
    # Five structural editions make the 100 designs materially different.
    if edition==0:
        o += [rect("edge_top",0,0,w,12,a1),rect("edge_bottom",0,h-12,w,12,a2)]
    elif edition==1:
        o += [rect("edge_left",0,0,28,h,a1),rect("edge_right",w-28,0,28,h,a2)]
    elif edition==2:
        o += [line("diag_l",0,h*.88,w*.18,0,a1,22),line("diag_r",w*.82,h,w,h*.12,a2,22)]
    elif edition==3:
        o += [rect("frame",20,20,w-40,h-40,"rgba(0,0,0,0)",a1,5)]
    else:
        o += [rect("rail",0,h*.72,w,h*.28,a1),rect("rail2",0,h*.88,w,h*.12,a2)]

    name=["NAME & TITLE HERE","ALEX MORGAN","DR. TAYLOR REED","JORDAN LEE","SAM PATEL",
          "OFFICE MANAGER","CREATIVE DIRECTOR","GENERAL MANAGER","YOUR NAME HERE","WELCOME"][idx%10]
    title=["YOUR COMPANY","EXECUTIVE OFFICE","MEETING ROOM","STUDIO 01","EST. 2026",
           "CLIENT SERVICES","DESIGN TEAM","ADMINISTRATION","YOUR TITLE","PRIVATE OFFICE"][(idx*7)%10]
    if layout==0:
        o += [text("name",185,65,830,name,52,ink,"900"),text("title",300,137,600,title,18,a1,"800")]
    elif layout==1:
        o += [rect("monogram",55,42,130,156,a1),text("initial",70,72,100,name[:2],52,bg,"900"),text("name",225,62,850,name,50,ink,"900","left"),text("title",225,132,720,title,19,a2,"800","left")]
    elif layout==2:
        o += [text("name",90,55,1020,name,56,ink,"900"),line("rule",220,135,980,135,a1,6),text("title",300,155,600,title,18,ink,"700")]
    elif layout==3:
        o += [rect("label",90,48,1020,144,"rgba(0,0,0,0)",a1,5),text("name",135,70,930,name,48,ink,"900"),text("title",260,140,680,title,18,a2,"800")]
    elif layout==4:
        o += [text("num",55,45,180,f"{idx+1:02d}",76,a1,"900"),line("v",240,38,240,202,a2,5),text("name",285,66,825,name,47,ink,"900","left"),text("title",285,135,700,title,18,ink,"700","left")]
    elif layout==5:
        o += [circle("seal",125,120,68,a1),text("initial",70,88,110,name[:2],42,bg,"900"),text("name",235,62,850,name,49,ink,"900","left"),text("title",235,136,720,title,18,a2,"800","left")]
    elif layout==6:
        o += [text("small",90,43,1020,"OFFICE • DIRECTORY",17,a1,"800"),text("name",90,78,1020,name,54,ink,"900"),text("title",90,155,1020,title,18,ink,"700")]
    elif layout==7:
        o += [line("slash1",55,205,170,35,a1,18),line("slash2",100,205,215,35,a2,9),text("name",245,65,865,name,50,ink,"900","left"),text("title",245,138,700,title,18,ink,"700","left")]
    elif layout==8:
        o += [circle("dot1",85,120,18,a1),circle("dot2",1115,120,18,a2),text("name",170,66,860,name,52,ink,"900"),text("title",280,140,640,title,18,ink,"700")]
    elif layout==9:
        o += [text("name",90,53,1020,name,58,ink,"900"),text("title",90,132,1020,title,20,a1,"800"),line("bottom",350,181,850,181,a2,5)]
    elif layout==10:
        o += [rect("left_block",0,0,255,h,a1),text("initial",48,72,160,name[:2],58,bg,"900"),text("name",300,60,810,name,49,ink,"900","left"),text("title",300,135,720,title,18,ink,"700","left")]
    elif layout==11:
        o += [text("name",110,65,980,name,48,ink,"900"),circle("gem",600,145,11,a1),text("title",300,164,600,title,17,a2,"800")]
    elif layout==12:
        o += [rect("bar",85,50,16,140,a1),text("name",135,62,970,name,52,ink,"900","left"),text("title",135,139,760,title,18,a2,"800","left")]
    elif layout==13:
        o += [text("name",80,58,1040,name,50,ink,"900"),line("l",80,142,410,142,a1,5),line("r",790,142,1120,142,a2,5),text("title",420,130,360,title,17,ink,"700")]
    elif layout==14:
        o += [circle("ring",130,120,72,"rgba(0,0,0,0)",a1,7),text("initial",78,89,104,name[:2],40,ink,"900"),text("name",250,60,850,name,50,ink,"900","left"),text("title",250,138,700,title,18,a2,"800","left")]
    elif layout==15:
        o += [text("name",80,50,1040,name,57,ink,"900"),rect("tag_bg",365,139,470,42,a1),text("title",385,147,430,title,17,bg,"900")]
    elif layout==16:
        o += [line("top_l",70,45,330,45,a1,6),line("top_r",870,45,1130,45,a2,6),text("name",110,75,980,name,50,ink,"900"),text("title",300,148,600,title,18,ink,"700")]
    elif layout==17:
        o += [text("initial",60,55,190,name[:1],90,a1,"900"),text("name",245,64,850,name,48,ink,"900","left"),text("title",245,137,700,title,18,a2,"800","left")]
    elif layout==18:
        o += [rect("corner1",45,42,90,12,a1),rect("corner2",45,42,12,75,a1),rect("corner3",1065,186,90,12,a2),rect("corner4",1143,123,12,75,a2),text("name",125,67,950,name,50,ink,"900"),text("title",300,143,600,title,18,ink,"700")]
    else:
        o += [text("name",80,57,1040,name,52,ink,"900"),text("bullet",540,133,120,"•  •  •",24,a1,"900"),text("title",300,166,600,title,17,ink,"700")]
    return w,h,o


def build_round_lapel_pin(product, idx):
    """Editable full-colour circular pin artwork: 100 combinations of layouts."""
    w=h=1000
    cx=cy=500
    palettes=[
        ("#f05b2a","#ffffff","#17365d"),("#0f2747","#fff4d6","#f7c66b"),
        ("#116466","#ffffff","#ffcb9a"),("#6b21a8","#fff7ed","#f9a8d4"),
        ("#111827","#f8fafc","#f59e0b"),("#be123c","#fff1f2","#fecdd3"),
        ("#1d4ed8","#ffffff","#facc15"),("#166534","#f0fdf4","#bbf7d0"),
        ("#f8fafc","#172554","#2563eb"),("#f97316","#172554","#ffffff"),
    ]
    bg,ink,accent=palettes[(idx//10+idx%10)%len(palettes)]
    k=idx%20
    family=idx//20
    titles=["YOUR LOGO","YOUR BRAND","TEAM SPIRIT","EXCELLENCE","EVENT CREW",
            "STAFF","MEMBER","VOLUNTEER","AWARD","EST. 2026",
            "CHAMPION","WELCOME","VIP","THANK YOU","OUR TEAM",
            "TOGETHER","PROUD","CELEBRATE","QUALITY","YOUR DESIGN"]
    title=titles[k]
    o=[circle("editable_colour_background",cx,cy,430,bg,"#c99c3e",10)]
    def heading(y,size=68):
        o.append(text("editable_title",205,y,590,title,size,ink,"900"))
    def subtitle(y,words="CUSTOM LAPEL PIN"):
        o.append(text("editable_subtitle",245,y,510,words,29,accent,"800"))
    # All artwork is vector/text and remains independently selectable.
    if k==0:
        heading(420,80);subtitle(530)
    elif k==1:
        o.append(circle("editable_emblem",cx,395,84,accent))
        heading(525,62)
    elif k==2:
        o.append(rect("editable_band",150,405,700,190,accent))
        o.append(text("editable_title",200,452,600,title,67,bg,"900"))
    elif k==3:
        o.append(text("editable_initials",340,275,320,title[:2],185,accent,"900"))
        heading(570,57)
    elif k==4:
        o.append(circle("editable_ring",cx,cy,330,"rgba(255,255,255,0)",accent,17))
        heading(435,65);subtitle(525,"SIGNATURE EDITION")
    elif k==5:
        o.append(line("editable_diagonal",240,735,750,255,accent,27))
        heading(435,66)
    elif k==6:
        o.append(circle("editable_badge",cx,cy,210,accent))
        o.append(text("editable_title",320,450,360,title,54,bg,"900"))
    elif k==7:
        o.append(rect("editable_top_bar",260,265,480,70,accent))
        heading(420,74);subtitle(555,"YOUR MESSAGE")
    elif k==8:
        for n in range(5):
            o.append(circle("editable_dot_"+str(n),300+n*100,350,19,accent))
        heading(455,69)
    elif k==9:
        o.append(line("editable_divider",500,250,500,750,accent,14))
        o.append(text("editable_left",250,445,220,title[:2],100,ink,"900"))
        o.append(text("editable_right",525,460,245,"YOUR LOGO",47,ink,"900"))
    elif k==10:
        o.append(circle("editable_halo",cx,cy,350,"rgba(255,255,255,0)",accent,8))
        o.append(circle("editable_halo_inner",cx,cy,280,"rgba(255,255,255,0)",ink,5))
        heading(440,68)
    elif k==11:
        o.append(rect("editable_block",245,310,510,370,accent))
        o.append(text("editable_title",270,445,460,title,69,bg,"900"))
    elif k==12:
        o.append(circle("editable_top_disc",cx,345,115,accent))
        heading(545,58);subtitle(625,"PROUDLY CUSTOM")
    elif k==13:
        o.append(line("editable_rule_top",220,370,780,370,accent,14))
        heading(450,75)
        o.append(line("editable_rule_bottom",220,580,780,580,accent,14))
    elif k==14:
        o.append(text("editable_monogram",315,310,370,title[:2],165,accent,"900"))
        subtitle(585,title)
    elif k==15:
        for n in range(3):
            o.append(rect("editable_stripe_"+str(n),230,290+n*42,540,20,accent))
        heading(490,66)
    elif k==16:
        o.append(circle("editable_offset_disc",355,380,140,accent))
        heading(515,62)
    elif k==17:
        o.append(rect("editable_left_panel",190,305,180,390,accent))
        o.append(text("editable_initials",215,460,140,title[:2],70,bg,"900"))
        o.append(text("editable_title",390,445,370,title,58,ink,"900"))
    elif k==18:
        o.append(circle("editable_outer_border",cx,cy,370,"rgba(255,255,255,0)",accent,23))
        o.append(circle("editable_inner_border",cx,cy,305,"rgba(255,255,255,0)",ink,5))
        heading(445,63)
    else:
        o.append(text("editable_topline",245,330,510,"PREMIUM EDITION",37,accent,"900"))
        heading(450,75)
        subtitle(560,"EST. 2026")
    # Five materially different finishing systems, each with editable geometry.
    if family==1:
        o.append(line("editable_finish_rule",260,700,740,700,accent,9))
    elif family==2:
        o.append(circle("editable_finish_orbit",cx,cy,385,"rgba(255,255,255,0)",accent,6))
    elif family==3:
        o.append(circle("editable_finish_dot_left",245,500,15,accent))
        o.append(circle("editable_finish_dot_right",755,500,15,accent))
    elif family==4:
        o.append(text("editable_finish_signature",345,700,310,"CUSTOM MADE",22,ink,"800"))
    return w,h,o

def build(product,idx):
    if product.id == 234 or 'round lapel pin' in product.name.lower():
        return build_round_lapel_pin(product,idx)
    if product.name == "Custom Aluminum Bottle Opener | Promotional Logo Tool":
        return build_aluminum_bottle_opener(product,idx)
    if product.id == 231 or "paper wristband" in product.name.lower():
        return build_paper_wristband(product,idx)
    if family(product) == "golf-ball":
        return build_golf_ball(product,idx)
    if product.id == 427 or product.name == "Custom Name Badge":
        return build_name_badge(product,idx)
    # Product 428 is the 10 x 2 in office door name plate. It must use the
    # dedicated horizontal editable library, never the generic promo templates.
    if product.id == 428 or "office door name plate" in product.name.lower():
        return build_name_plate(product,idx)
    if family(product) == "mouse-pad":
        return build_mouse_pad(product,idx)
    if family(product) == "freshener":
        return build_freshener(product,idx)
    if product.name == "Custom Full Color Lanyard with Logo | Personalized Event ID Holder":
        return build_full_color_lanyard(product,idx)
    if family(product) == "coaster":
        return build_coaster(product,idx)
    if product.name == "Compact Lightweight Umbrella – 36 Inch":
        return build_umbrella(product,idx)
    # Product 420 is the two-sided Custom Car Keychain. Use the dedicated
    # 100-design strap library instead of the generic promotional layouts.
    # Every layer returned by build_heavy_keychain is an editable Fabric
    # primitive; payload() duplicates the composition into editable Front/Back
    # pages with unique object IDs.
    if product.id == 420 or product.name == "Premium Heavy Duty Custom Keychain":
        return build_heavy_keychain(product,idx)
    w,h=canvas(product); dark,light,accent=PALETTES[idx%len(PALETTES)]
    k=idx%20; m=max(20,w*.06); fs=max(18,min(w,h)*.085)
    o=[]
    # Artwork templates are transparent overlays. Never add a full-canvas background sheet over the locked product mockup.
    # 100 materially different compositions: 20 master systems x 5 structural variants.
    # Every variant changes geometry/motif; recolouring never creates a new template.
    system=idx//20
    variant=system % 5
    if variant==1:
        m=max(20,w*.10); fs*=.88
    elif variant==2:
        m=max(20,w*.035); fs*=1.08
    elif variant==3:
        m=max(20,w*.075); fs*=.94
    elif variant==4:
        m=max(20,w*.05); fs*=1.02
    if k==0:o=[rect("left",0,0,w*.28,h,dark),text("brand",w*.34,h*.25,w*.58,"YOUR BRAND",fs,dark,"800","left"),text("tag",w*.34,h*.52,w*.58,"MAKE IT YOURS",fs*.38,accent,"600","left")]
    elif k==1:o=[circle("mark",w*.5,h*.34,min(w,h)*.16,accent),text("brand",m,h*.58,w-2*m,"YOUR BRAND",fs,light,"800"),text("url",m,h*.78,w-2*m,"YOURCOMPANY.CA",fs*.3,light)]
    elif k==2:o=[rect("bg",0,0,w,h,light),rect("top",0,0,w,h*.24,accent),text("brand",m,h*.36,w-2*m,"YOUR BRAND",fs,dark,"800"),line("rule",w*.25,h*.62,w*.75,h*.62,accent,4),text("tag",m,h*.69,w-2*m,"PROMOTE • CONNECT • GROW",fs*.3,dark)]
    elif k==3:o=[rect("bg",0,0,w,h,dark),rect("card",m,h*.14,w-2*m,h*.72,light),text("brand",w*.14,h*.3,w*.72,"YOUR BRAND",fs,dark,"800"),text("tag",w*.14,h*.55,w*.72,"PREMIUM PROMOTIONAL",fs*.34,accent)]
    elif k==4:o=[rect("bg",0,0,w,h,light),rect("diag",0,h*.68,w,h*.32,accent),text("brand",m,h*.22,w-2*m,"YOUR BRAND",fs,dark,"800","left"),text("url",m,h*.48,w-2*m,"yourcompany.ca",fs*.32,dark,"500","left")]
    elif k==5:o=[rect("bg",0,0,w,h,dark),rect("rail",w*.08,0,w*.08,h,accent),text("brand",w*.24,h*.25,w*.65,"YOUR\\nBRAND",fs,light,"800","left"),text("tag",w*.24,h*.66,w*.65,"EST. 2026",fs*.32,accent,"600","left")]
    elif k==6:o=[rect("bg",0,0,w,h,light),circle("halo",w*.5,h*.42,min(w,h)*.27,accent),circle("logo",w*.5,h*.42,min(w,h)*.16,dark),text("brand",m,h*.76,w-2*m,"YOUR BRAND",fs*.52,dark,"800")]
    elif k==7:o=[rect("band",0,h*.25,w,h*.5,light),text("brand",m,h*.36,w-2*m,"YOUR BRAND",fs,dark,"800"),text("tag",m,h*.61,w-2*m,"CUSTOM • LOCAL • BOLD",fs*.3,dark)]
    elif k==8:o=[rect("bg",0,0,w,h,light),rect("frame",m,h*.1,w-2*m,h*.8,"rgba(0,0,0,0)",dark,3),text("brand",w*.15,h*.3,w*.7,"YOUR BRAND",fs,dark,"800"),text("tag",w*.15,h*.57,w*.7,"SINCE 2026",fs*.34,accent)]
    elif k==9:o=[rect("bg",0,0,w,h,dark),circle("dot1",w*.16,h*.2,min(w,h)*.05,accent),circle("dot2",w*.84,h*.8,min(w,h)*.08,accent),text("brand",m,h*.36,w-2*m,"YOUR BRAND",fs,light,"800"),text("url",m,h*.62,w-2*m,"YOURCOMPANY.CA",fs*.3,light)]
    elif k==10:o=[rect("bg",0,0,w,h,light),rect("right",w*.7,0,w*.3,h,dark),text("brand",m,h*.28,w*.56,"YOUR BRAND",fs,dark,"800","left"),text("tag",m,h*.54,w*.56,"BRAND EVERY MOMENT",fs*.34,accent,"600","left")]
    elif k==11:o=[rect("bg",0,0,w,h,dark),line("a",m,h*.25,w-m,h*.25,accent,5),text("brand",m,h*.36,w-2*m,"YOUR BRAND",fs,light,"800"),line("b",m,h*.67,w-m,h*.67,accent,5)]
    elif k==12:o=[rect("bg",0,0,w,h,light),circle("seal",w*.5,h*.42,min(w,h)*.23,dark),text("initial",w*.35,h*.31,w*.3,"ZV",fs,light,"800"),text("brand",m,h*.74,w-2*m,"YOUR BRAND",fs*.46,dark,"700")]
    elif k==13:o=[rect("bg",0,0,w,h,accent),rect("block",w*.1,h*.14,w*.8,h*.72,dark),text("brand",w*.17,h*.3,w*.66,"YOUR BRAND",fs,light,"800"),text("tag",w*.17,h*.58,w*.66,"CUSTOM PROMOTIONAL",fs*.31,accent)]
    elif k==14:o=[rect("bg",0,0,w,h,light),rect("bar1",0,0,w*.18,h,accent),rect("bar2",w*.18,0,w*.05,h,dark),text("brand",w*.31,h*.3,w*.6,"YOUR BRAND",fs,dark,"800","left"),text("url",w*.31,h*.58,w*.6,"yourcompany.ca",fs*.31,accent,"600","left")]
    elif k==15:o=[rect("bg",0,0,w,h,dark),rect("top",0,0,w,h*.12,accent),rect("bottom",0,h*.88,w,h*.12,accent),text("brand",m,h*.34,w-2*m,"YOUR BRAND",fs,light,"800"),text("tag",m,h*.61,w-2*m,"DESIGNED TO BE REMEMBERED",fs*.3,light)]
    elif k==16:o=[rect("bg",0,0,w,h,light),circle("c1",w*.12,h*.18,min(w,h)*.11,accent),circle("c2",w*.88,h*.82,min(w,h)*.16,dark),text("brand",m,h*.38,w-2*m,"YOUR BRAND",fs,dark,"800"),text("tag",m,h*.64,w-2*m,"MAKE AN IMPRESSION",fs*.32,accent)]
    elif k==17:o=[rect("bg",0,0,w,h,dark),rect("panel",w*.12,h*.12,w*.76,h*.76,accent),rect("inner",w*.15,h*.17,w*.7,h*.66,light),text("brand",w*.2,h*.34,w*.6,"YOUR BRAND",fs,dark,"800"),text("tag",w*.2,h*.59,w*.6,"PREMIUM CUSTOM",fs*.31,dark)]
    elif k==18:o=[rect("bg",0,0,w,h,light),text("brand",m,h*.2,w-2*m,"YOUR",fs*.72,dark,"800"),text("brand2",m,h*.42,w-2*m,"BRAND",fs*1.15,accent,"800"),text("url",m,h*.72,w-2*m,"YOURCOMPANY.CA",fs*.3,dark)]
    else:o=[rect("bg",0,0,w,h,dark),rect("stripe",0,h*.43,w,h*.14,accent),text("brand",m,h*.2,w-2*m,"YOUR BRAND",fs,light,"800"),text("tag",m,h*.66,w-2*m,"PROMOTIONAL PRODUCTS",fs*.32,light)]
    # Remove filled panels that can look like part of the physical product.
    # Product body/mockup is editor-only and locked; template JSON is artwork only.
    # Most promotional products place artwork over a separate product mockup, so
    # their large filled panels are removed. Product 420 is different: its two
    # editor pages ARE the printable keychain faces, therefore those filled
    # rectangles are real editable design layers and must be preserved.
    if product.id != 420:
        cleaned=[]
        for obj in o:
            if obj.get("type")=="rect":
                ow=float(obj.get("width") or 0); oh=float(obj.get("height") or 0)
                fill=str(obj.get("fill") or "").lower()
                transparent=fill in ("", "transparent", "rgba(0,0,0,0)")
                if not transparent and (ow*oh) >= (w*h*.12):
                    continue
            cleaned.append(obj)
        o=cleaned
    # Five structural luxury treatments make each 20-layout family materially different.
    # All added objects remain editable Fabric primitives.
    if variant==1:
        o += [
            line(f"lux_top_{idx}",w*.08,h*.09,w*.68,h*.09,accent,max(2,min(w,h)*.008)),
            line(f"lux_right_{idx}",w*.91,h*.18,w*.91,h*.78,dark,max(2,min(w,h)*.006)),
            text(f"edition_{idx}",w*.70,h*.08,w*.20,"SIGNATURE",max(12,fs*.18),dark,"600","right"),
        ]
    elif variant==2:
        rr=max(8,min(w,h)*.035)
        o += [
            circle(f"gem_a_{idx}",w*.10,h*.12,rr,accent),
            circle(f"gem_b_{idx}",w*.90,h*.88,rr,dark),
            line(f"lux_rule_{idx}",w*.12,h*.90,w*.62,h*.90,accent,max(2,min(w,h)*.008)),
        ]
    elif variant==3:
        o += [
            rect(f"lux_outer_{idx}",w*.035,h*.045,w*.93,h*.91,"rgba(0,0,0,0)",accent,max(2,min(w,h)*.006)),
            rect(f"lux_inner_{idx}",w*.065,h*.075,w*.87,h*.85,"rgba(0,0,0,0)",dark,max(1,min(w,h)*.003)),
        ]
    elif variant==4:
        rr=max(7,min(w,h)*.025)
        o += [
            line(f"deco_l_{idx}",w*.05,h*.12,w*.05,h*.88,accent,max(2,min(w,h)*.007)),
            line(f"deco_r_{idx}",w*.95,h*.12,w*.95,h*.88,accent,max(2,min(w,h)*.007)),
            circle(f"deco_jewel_{idx}",w*.50,h*.08,rr,accent,dark,max(1,min(w,h)*.003)),
        ]
    return w,h,o

def payload(product,idx):
    w,h,objects=build(product,idx); p=physical(product)
    page={"name":"Print Area","background":"#FFFFFF","objects":objects}
    if p: page["physical"]={"widthIn":p[0],"heightIn":p[1]}
    doc={"width":w,"height":h,"profile":"promotional-"+family(product),"unit":"in"}
    if p: doc["physical"]={"widthIn":p[0],"heightIn":p[1]}
    names=[
        "Gilded Botanical","Midnight Monogram","Emerald Atelier","Blush Maison","Azure Heritage",
        "Terracotta Social","Sage Gallery","Amethyst Deco","Rose Garden","Indigo Modern",
        "Verdant Luxe","Ruby Celebration","Ocean Mosaic","Violet Society","Amber Classic",
        "Noir Pop","Olive Artisan","Copper Studio","Orchid Signature","Royal Medallion",
    ]
    editions=["Signature","Editorial","Grand","Contemporary","Collector"]
    design_name=(f"{names[idx%20]} — {editions[(idx//20)%5]}" if family(product)=="coaster"
                 else (f"Bottle Opener {idx+1:03d}" if product.name == "Custom Aluminum Bottle Opener | Promotional Logo Tool"
                       else f"{family(product).replace('-',' ').title()} {idx+1:03d}"))
    # Product 420 is a two-sided car keychain. Keep one DesignTemplate row per
    # design, but store both editable faces inside it (Front + Back).
    if product.id == 420 or (family(product)=="keychain" and "car keychain" in product.name.lower()):
        front=copy.deepcopy(page)
        front["name"]="Front"
        back=copy.deepcopy(page)
        back["name"]="Back"
        # IDs must be unique between pages so edits/history never cross-link faces.
        for obj in back.get("objects",[]):
            oid=str(obj.get("id") or "object")
            obj["id"]=oid+"_back"
            obj["name"]=(obj.get("name") or oid)+" Back"
        pages=[front,back]
    else:
        pages=[copy.deepcopy(page)]
    show_mockup = False if product.id == 420 else True
    return {"version":2,"templateType":"editable-master","generator":GENERATOR,"showProductMockup":show_mockup,"lockProductMockup":show_mockup,"constrainToPrintArea":True,"designName":design_name,"document":doc,"pageCount":len(pages),"pages":copy.deepcopy(pages),"adminPages":copy.deepcopy(pages),"editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1","source":{"type":"zenvibe-promotional-transparent-artwork-v24","note":"Editable artwork only; product reference is editor-only when enabled."}}

class Command(BaseCommand):
    help="Create 100 editable promotional templates per product while preserving admin/source ruler geometry."
    def add_arguments(self,p):
        p.add_argument("--count",type=int,default=COUNT); p.add_argument("--replace",action="store_true"); p.add_argument("--product-id",type=int)
    @transaction.atomic
    def handle(self,*args,**opts):
        q=Product.objects.filter(category__slug="promotional-products",is_active=True,name__in=CANONICAL_PRODUCT_NAMES).exclude(pk__in=LEGACY_PRODUCT_IDS)
        if opts["product_id"]: q=q.filter(pk=opts["product_id"])
        products=list(q)
        if not products: raise CommandError("No active Promotional Products found.")
        total=0
        for product in products:
            # Dedicated aluminum bottle-opener workspace matching the source configurator.
            if product.name == "Custom Aluminum Bottle Opener | Promotional Logo Tool":
                # Source configurator ruler is the product workspace (21 x 13.8 in).
                # The editable logo face is a separate percentage area inside it.
                product.print_width_in=21
                product.print_height_in=13.8
                product.workspace_width_in=21
                product.workspace_height_in=13.8
                area=product.print_areas.order_by("sort_order","id").first()
                if area:
                    area.left=31.5; area.top=43.8; area.width=36; area.height=8.5
                    area.print_width_in=21; area.print_height_in=13.8
                    area.save(update_fields=["left","top","width","height","print_width_in","print_height_in"])
                else:
                    ProductPrintArea.objects.create(product=product,name="Logo Area",
                        left=31.5,top=43.8,width=36,height=8.5,
                        print_width_in=21,print_height_in=13.8,sort_order=0)
                source_colours=[
                    ("Blue","blue","#2563EB"),("Red","red","#EF4444"),
                    ("White","white","#F3F4F6"),("Green","green","#2F9E44"),
                    ("Black","black","#333333"),
                ]
                keep=[]
                for order,(name,key,hex_value) in enumerate(source_colours):
                    keep.append(key)
                    ProductColorVariant.objects.update_or_create(
                        product=product,color_key=key,
                        defaults={"name":name,"hex_value":hex_value,"slug_suffix":key,
                                  "sort_order":order,"is_active":True},
                    )
                product.color_variants.exclude(color_key__in=keep).update(is_active=False)
            # Source-style paper wristband: full 10 x .75 inch printable face.
            # Apply only to paper wristbands; silicone wristbands are unchanged.
            if product.id == 231 or "paper wristband" in product.name.lower():
                product.print_width_in=10
                product.print_height_in=.75
                product.workspace_width_in=10
                product.workspace_height_in=.75
                area=product.print_areas.order_by("sort_order","id").first()
                if area:
                    area.left=0; area.top=0; area.width=100; area.height=100
                    area.print_width_in=10; area.print_height_in=.75
                    area.save(update_fields=["left","top","width","height","print_width_in","print_height_in"])
                else:
                    ProductPrintArea.objects.create(product=product,name="Print Area",
                        left=0,top=0,width=100,height=100,
                        print_width_in=10,print_height_in=.75,sort_order=0)
            # Mouse pad source configuration: one editable 8.5 x 7 in face.
            # Rectangle/Round are customer shape options over the SAME 100 designs.
            if family(product) == "mouse-pad":
                product.print_width_in=8.5
                product.print_height_in=7
                product.workspace_width_in=8.5
                product.workspace_height_in=7
                attrs=dict(product.source_attributes or {})
                attrs["Shape"]=["Rectangle","Round"]
                product.source_attributes=attrs
                area=product.print_areas.order_by("sort_order","id").first()
                if area:
                    area.left=0; area.top=0; area.width=100; area.height=100
                    area.print_width_in=8.5; area.print_height_in=7
                    area.save(update_fields=["left","top","width","height","print_width_in","print_height_in"])
                else:
                    ProductPrintArea.objects.create(product=product,name="Print Area",left=0,top=0,width=100,height=100,print_width_in=8.5,print_height_in=7,sort_order=0)
            # Source-matched Full Color Lanyard configuration: the customer
            # designs a 6 x 1.25 inch horizontal face. 36 x .75 is the physical
            # strap/manufacturing dimension and must not drive this editor ruler.
            if product.name == "Custom Full Color Lanyard with Logo | Personalized Event ID Holder":
                product.print_width_in=6
                product.print_height_in=1.25
                product.workspace_width_in=6
                product.workspace_height_in=1.25
                area=product.print_areas.order_by("sort_order","id").first()
                if area:
                    area.left=0; area.top=0; area.width=100; area.height=100
                    area.print_width_in=6; area.print_height_in=1.25
                    area.save(update_fields=["left","top","width","height","print_width_in","print_height_in"])
                else:
                    ProductPrintArea.objects.create(product=product,name="Print Area",left=0,top=0,width=100,height=100,print_width_in=6,print_height_in=1.25,sort_order=0)
                source_colours=[
                    ("Red","red","#E31B23"),("Black","black","#111111"),
                    ("Blue","blue","#1268C4"),("Pink","pink","#ED16C5"),
                    ("Coral Red","coral-red","#E33632"),
                ]
                keep=[]
                for order,(name,key,hex_value) in enumerate(source_colours):
                    keep.append(key)
                    ProductColorVariant.objects.update_or_create(
                        product=product,color_key=key,
                        defaults={"name":name,"hex_value":hex_value,"slug_suffix":key,"sort_order":order,"is_active":True},
                    )
                product.color_variants.exclude(color_key__in=keep).update(is_active=False)
            product.customizer_mode="editor"
            if product.editor_layout_mode=="legacy": product.editor_layout_mode="print_area"
            product.constrain_to_print_area=True
            # Product 420 uses two clean printable faces. Its lifestyle/gallery
            # photograph must never be injected into the editable template canvas.
            product.show_product_reference = False if product.id == 420 else True
            update_fields=["customizer_mode","editor_layout_mode","constrain_to_print_area","show_product_reference"]
            if product.name == "Custom Full Color Lanyard with Logo | Personalized Event ID Holder":
                update_fields += ["print_width_in","print_height_in","workspace_width_in","workspace_height_in"]
            if family(product) == "mouse-pad":
                update_fields += ["print_width_in","print_height_in","workspace_width_in","workspace_height_in","source_attributes"]
            if product.id == 231 or "paper wristband" in product.name.lower():
                update_fields += ["print_width_in","print_height_in","workspace_width_in","workspace_height_in"]
            if product.name == "Custom Aluminum Bottle Opener | Promotional Logo Tool":
                update_fields += ["print_width_in","print_height_in","workspace_width_in","workspace_height_in"]
            product.save(update_fields=update_fields)
            if opts["replace"]:
                # Do not delete the currently visible library first. Build the
                # replacement set, verify it, then retire older generated rows.
                # This prevents a failed/partial seed from leaving the product
                # with zero templates.
                old_generated=DesignTemplate.objects.filter(
                    product=product, json_data__generator__in=LEGACY_GENERATORS
                ).exclude(json_data__generator=GENERATOR)
            else:
                old_generated=DesignTemplate.objects.none()
            # --replace must really rebuild this product's generated library.
            # Keeping rows from the current generator caused stale Freshener IDs/design JSON
            # to survive previous fixes.
            if opts["replace"]:
                # Umbrella rebuild must also replace previous named library rows
                # even when their generator tag was missing or different.
                if family(product) == "umbrella":
                    old_generated = DesignTemplate.objects.filter(
                        product=product,
                        name__startswith="Umbrella "
                    ).exclude(name__startswith="Umbrella Luxury ")
                else:
                    DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR).delete()
            existing=0 if opts["replace"] and family(product) == "umbrella" else DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR).count()
            target=max(0,opts["count"]-existing)
            for n in range(existing,existing+target):
                data=payload(product,n)
                if family(product) == "umbrella":
                    DesignTemplate.objects.update_or_create(
                        product=product, name=data["designName"],
                        defaults={"json_data":data,"is_active":True},
                    )
                else:
                    DesignTemplate.objects.create(product=product,name=data["designName"],json_data=data,is_active=True)
            final_count=DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR,is_active=True).count()
            if opts["replace"] and final_count >= opts["count"]:
                if family(product) == "umbrella":
                    # Preserve old records for recovery; do not show them in gallery.
                    old_generated.exclude(json_data__generator=GENERATOR).update(is_active=False)
                else:
                    old_generated.delete()
            total+=target
            ruler=physical(product)
            self.stdout.write(f"{product.id} — {product.name}: {existing+target} templates; ruler={'%.3f x %.3f in'%ruler if ruler else 'ADMIN CONFIG REQUIRED'}")
        self.stdout.write(self.style.SUCCESS(f"Done. Created {total} editable Promotional Product templates. Legacy asset rows {sorted(LEGACY_PRODUCT_IDS)} were excluded."))
