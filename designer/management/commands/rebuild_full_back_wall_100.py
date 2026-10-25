
from pathlib import Path
import colorsys
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.conf import settings
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-full-back-wall-v11-scale-content-aligned"

THEMES = [
"Botanical Luxe","Wildflower Noir","Rose Garden","Tropical Palm","Cherry Blossom","Eucalyptus Gold","Lavender Estate","Peony Blush","Monstera Luxe","Floral Arch",
"Art Deco Gold","Black Tie","Emerald Prestige","Royal Purple","Navy Copper","Ivory Minimal","Marble Gold","Terrazzo Luxe","Geometric Prism","Executive Blue",
"Luxury Waves","Aurora","Gradient Mesh","Abstract Flow","Paper Cut","Contour Lines","Topographic","Orbit","Ribbon Motion","Diagonal Luxe",
"Architecture","Real Estate","Finance","Legal","Consulting","Technology","Cyber Grid","Data Wave","Construction","Automotive",
"Coffee House","Bakery","Restaurant","Food Festival","Farm Market","Organic Produce","Wellness","Spa","Beauty","Salon",
"Fitness","Running","Football","Basketball","Motorsport","Outdoor Adventure","Camping","Surf","Coastal","Mountain",
"Wedding","Engagement","Celebration","Festival","Music","Nightlife","Community","Charity","Education","Graduation",
"Kids Bright","Candy Pop","Retro 70s","Retro 80s","Y2K","Pop Art","Memphis","Bauhaus","Swiss Editorial","Magazine",
"Japanese Minimal","Moroccan","Mediterranean","Indian Festive","Nordic","Bohemian","Heritage","Mosaic","Mandala","Premium Monogram",
"Autumn","Winter","Spring","Summer","Christmas","New Year","Valentine","Canada Event","Trade Show","Premium Event"
]

LEAF="M0 28 C18 0 48 0 62 10 C48 38 20 48 0 28 Z"
FLOWER="M30 15 C20 -2 5 8 14 24 C-4 24 1 43 19 37 C14 55 35 57 37 39 C52 49 64 31 48 23 C58 7 39 0 30 15 Z"
STAR="M30 0 L37 21 L60 21 L41 34 L48 56 L30 43 L12 56 L19 34 L0 21 L23 21 Z"

def base(t, **kw):
    d={"type":t,"customerEditable":True,"locked":False,"selectable":True,"evented":True}
    d.update(kw); return d

def rect(x,y,w,h,c,**kw): return base("rect",left=x,top=y,width=w,height=h,fill=c,**kw)
def circle(x,y,r,c,**kw): return base("circle",left=x,top=y,radius=r,width=2*r,height=2*r,fill=c,**kw)
def tri(x,y,w,h,c,a=0,**kw): return base("triangle",left=x,top=y,width=w,height=h,fill=c,angle=a,**kw)
def path(p,x,y,c,s=1,a=0,**kw): return base("path",path=p,left=x,top=y,fill=c,scaleX=s,scaleY=s,angle=a,**kw)
def line(x1,y1,x2,y2,c,sw=3,**kw): return base("line",x1=x1,y1=y1,x2=x2,y2=y2,stroke=c,strokeWidth=sw,fill=None,**kw)
def text(v,x,y,size,c,w=500,weight="700",align="left",a=0):
    return base("textbox",text=v,left=x,top=y,width=w,height=size*1.5,fontSize=size,
                fontFamily="Poppins",fontWeight=weight,fill=c,textAlign=align,angle=a)

def palette(i):
    premium=[
      ("#0B1F1A","#F7F2E7","#C8A96B","#E8DDC3","#081411"), # emerald/gold
      ("#101828","#F8F5EE","#C9A35E","#D9D2C3","#090E18"), # midnight/champagne
      ("#3A0F1F","#FFF7F1","#CDA46D","#E7C9B5","#220812"), # burgundy
      ("#24123F","#FBF7F0","#D3B36A","#CDBCE3","#130923"), # aubergine
      ("#262321","#FAF7F0","#B89562","#DDD2C2","#141211"), # charcoal
      ("#123B38","#FFF9EE","#D5B06B","#BFD8D1","#09211F"), # teal
      ("#5A3428","#FFF8F1","#C89A65","#E7C8AD","#2D1913"), # mocha
      ("#17243A","#F8F3E8","#B99255","#C8D2DE","#0B1220"), # navy
      ("#4A3A2A","#FFF9F0","#C6A15B","#E4D7BD","#251D15"), # olive-brown
      ("#2B1836","#FFF7F4","#D0A06C","#E2C7D7","#160C1C"), # plum
    ]
    return premium[i%len(premium)]

def decoration(i,W,H,p):
    """25 genuinely different composition engines x 4 branding variants = 100.
    Variation is structural, not merely a palette swap."""
    bg,white,accent,soft,dark=p
    m=i%25; o=[]
    if m==0: # botanical corners
        for n in range(7): o.append(path(LEAF,20+n*38,20+n*17,accent,.75+n*.05,-55+n*10,opacity=.78))
        for n in range(6): o.append(path(LEAF,W-250+n*32,H-150+n*10,soft,.7+n*.05,125+n*8,opacity=.7))
    elif m==1: # wildflower field
        for n in range(13):
            x=30+n*(W-80)/12; h=70+(n%5)*24
            o += [line(x,H-18,x,H-h,soft,3,opacity=.65),path(FLOWER,x-18,H-h-25,accent,.45+(n%3)*.08,n*17)]
    elif m==2: # rose garden clusters
        for x,y,sc in [(45,45,1.2),(120,75,.8),(W-180,35,1.0),(W-105,95,.7),(W-160,H-125,.85)]:
            o.append(path(FLOWER,x,y,accent,sc,15,opacity=.85))
            o.append(path(LEAF,x+35,y+35,soft,sc*.75,35,opacity=.65))
    elif m==3: # tropical palm
        for x,y,a0 in [(30,35,-35),(W-180,30,145),(35,H-130,15),(W-170,H-125,205)]:
            for n in range(5): o.append(path(LEAF,x+n*18,y+n*8,accent,1.0-n*.08,a0+n*13,opacity=.78))
    elif m==4: # cherry blossom branch
        o.append(line(15,H*.78,W*.55,H*.18,soft,7,opacity=.55))
        for n in range(10):
            x=50+n*W*.05; y=H*.72-n*H*.055
            o.append(path(FLOWER,x,y,accent,.38+(n%2)*.12,n*21,opacity=.9))
    elif m==5: # eucalyptus wreath
        cx,cy=W*.77,H*.47
        for n in range(18):
            ang=n*20; rad=105
            x=cx+rad*__import__("math").cos(__import__("math").radians(ang))
            y=cy+rad*.55*__import__("math").sin(__import__("math").radians(ang))
            o.append(path(LEAF,x,y,soft,.55,ang+90,opacity=.65))
    elif m==6: # art deco fan
        o += [rect(24,24,W-48,H-48,"transparent",stroke=accent,strokeWidth=5)]
        for n in range(9): o.append(line(W*.5,H*.5,35+n*(W-70)/8,25,soft,3,opacity=.65))
        for n in range(9): o.append(line(W*.5,H*.5,35+n*(W-70)/8,H-25,accent,2,opacity=.45))
    elif m==7: # double deco frame
        o += [rect(28,28,W-56,H-56,"transparent",stroke=accent,strokeWidth=5),
              rect(48,48,W-96,H-96,"transparent",stroke=soft,strokeWidth=2)]
        for x,y,a0 in [(28,28,0),(W-88,28,90),(W-88,H-88,180),(28,H-88,270)]:
            o.append(path(STAR,x,y,accent,.8,a0))
    elif m==8: # marble veins
        for n in range(8):
            o.append(path("M0 30 C45 -10 85 70 130 30 C175 -10 215 70 260 30",
                          -40,15+n*H/8,accent,2.7,-10+n*3,opacity=.25))
    elif m==9: # terrazzo
        for n in range(32):
            x=(n*137)%int(W-60)+20; y=(n*83)%int(H-50)+15
            o.append(tri(x,y,14+(n%4)*8,18+(n%3)*9,accent if n%2 else soft,n*29,opacity=.5))
    elif m==10: # prism geometry
        o += [tri(-60,-40,W*.50,H*.90,accent,9,opacity=.38),
              tri(W*.62,-30,W*.48,H*.80,soft,165,opacity=.25),
              tri(W*.68,H*.42,W*.38,H*.62,accent,205,opacity=.22)]
    elif m==11: # executive bands
        o += [rect(0,0,W*.16,H,accent),rect(W*.16,0,18,H,soft),
              rect(W*.73,0,W*.27,H,soft,opacity=.10)]
    elif m==12: # royal crest
        o += [circle(W*.5-95,H*.5-95,95,accent,opacity=.18),
              circle(W*.5-70,H*.5-70,70,"transparent",stroke=soft,strokeWidth=4)]
        for n in range(8): o.append(path(STAR,W*.5-25+(n%4-1.5)*65,H*.5-25+(n//4-.5)*75,accent,.45,n*15))
    elif m==13: # diamond society
        for n in range(7):
            size=55+n*25
            o.append(rect(W*.5-size/2,H*.5-size/2,size,size,"transparent",stroke=accent if n%2 else soft,
                          strokeWidth=3,angle=45,opacity=.45))
    elif m==14: # celestial
        for n in range(18):
            x=(n*151)%int(W-80)+30; y=(n*97)%int(H-60)+20
            o.append(path(STAR,x,y,accent,.18+(n%3)*.08,n*11,opacity=.7))
        o.append(circle(W*.78,H*.18,72,soft,opacity=.16))
    elif m==15: # luxury waves
        for n in range(6):
            o.append(path("M0 40 C130 -30 250 110 390 35 C520 -25 650 100 800 35",
                          -40,10+n*H/6,soft if n%2 else accent,1.7,n*2,opacity=.18))
    elif m==16: # heritage frame
        o += [rect(18,18,W-36,H-36,"transparent",stroke=soft,strokeWidth=7),
              rect(38,38,W-76,H-76,"transparent",stroke=accent,strokeWidth=2)]
        for n in range(5):
            o.append(path(STAR,55+n*55,55,accent,.35,n*10))
            o.append(path(STAR,W-85-n*55,H-85,soft,.35,n*10))
    elif m==17: # architectural arch
        o += [rect(W*.08,H*.15,W*.28,H*.72,accent,opacity=.14),
              circle(W*.08,H*.02,W*.14,accent,opacity=.14),
              rect(W*.67,H*.08,W*.22,H*.84,soft,opacity=.10)]
    elif m==18: # ribbon motion
        o += [rect(-80,H*.12,W*1.18,62,accent,angle=-8,opacity=.42),
              rect(-70,H*.70,W*1.16,45,soft,angle=7,opacity=.30)]
    elif m==19: # orbit
        for n in range(5):
            o.append(circle(W*.73-n*18,H*.48-n*18,45+n*35,"transparent",
                            stroke=accent if n%2 else soft,strokeWidth=3,opacity=.38))
    elif m==20: # sunburst
        cx,cy=W*.12,H*.78
        for n in range(18):
            import math
            a=math.radians(n*20); o.append(line(cx,cy,cx+math.cos(a)*W*.42,cy+math.sin(a)*H*.65,accent,3,opacity=.25))
    elif m==21: # checker luxe
        sz=70
        for yy in range(0,int(H)+sz,sz):
            for xx in range(0,int(W)+sz,sz):
                if (xx//sz+yy//sz)%2==0:o.append(rect(xx,yy,sz,sz,accent,opacity=.08))
    elif m==22: # diagonal motion
        for n in range(7): o.append(rect(-130+n*210,-100,82,H*1.7,accent if n%2 else soft,angle=24,opacity=.18))
    elif m==23: # mosaic
        for n in range(26):
            x=(n*173)%int(W-100)+30; y=(n*113)%int(H-80)+25
            o.append(rect(x,y,24+(n%4)*11,24+(n%3)*12,accent if n%2 else soft,angle=45,opacity=.28))
    else: # premium monogram split
        o += [rect(0,0,W*.42,H,accent,opacity=.18),rect(W*.42,0,5,H,soft),
              circle(W*.73,H*.50-105,105,"transparent",stroke=accent,strokeWidth=5,opacity=.42)]
        for n in range(6): o.append(path(STAR,W*.70+(n%3)*55,H*.36+(n//3)*85,soft,.42,n*20,opacity=.7))
    return o

def branding(i,W,H,p):
    bg,ivory,gold,soft,dark=p
    mode=i%5
    if mode==0: # editorial left
        return [
          text("YOUR LOGO",W*.105,H*.19,28,gold,260,"600"),
          text("COMPANY",W*.105,H*.35,54,ivory,560,"700"),
          text("NAME",W*.105,H*.50,54,ivory,560,"700"),
          rect(W*.105,H*.66,95,3,gold),
          text("YOUR SIGNATURE LINE",W*.105,H*.70,19,soft,430,"400"),
          text("WEBSITE.COM  •  123 456 7890",W*.105,H*.80,17,ivory,520,"500")]
    if mode==1: # centred prestige
        return [
          text("YOUR LOGO",W*.5-130,H*.19,26,gold,260,"600","center"),
          text("COMPANY NAME",W*.5-330,H*.39,52,ivory,660,"700","center"),
          rect(W*.5-60,H*.57,120,3,gold),
          text("PREMIUM BRAND EXPERIENCE",W*.5-260,H*.63,18,soft,520,"400","center"),
          text("WEBSITE.COM",W*.5-170,H*.78,17,ivory,340,"500","center")]
    if mode==2: # right luxury
        return [
          text("YOUR LOGO",W*.67,H*.19,27,gold,260,"600","right"),
          text("COMPANY",W*.53,H*.36,52,ivory,430,"700","right"),
          text("NAME",W*.53,H*.51,52,ivory,430,"700","right"),
          text("DISTINCTIVE • TIMELESS • YOURS",W*.53,H*.69,17,soft,430,"400","right"),
          text("123 456 7890",W*.66,H*.79,16,ivory,280,"500","right")]
    if mode==3: # monogram centre
        return [
          circle(W*.5-48,H*.20,48,"transparent",stroke=gold,strokeWidth=3),
          text("ZN",W*.5-36,H*.25,32,gold,72,"600","center"),
          text("YOUR COMPANY",W*.5-310,H*.48,48,ivory,620,"700","center"),
          text("SIGNATURE COLLECTION",W*.5-230,H*.64,18,soft,460,"400","center"),
          text("WEBSITE.COM",W*.5-160,H*.77,16,ivory,320,"500","center")]
    return [ # split editorial
          text("YOUR LOGO",W*.09,H*.17,25,gold,250,"600"),
          text("CREATE",W*.09,H*.35,48,ivory,440,"700"),
          text("AN IMPRESSION",W*.09,H*.50,48,ivory,520,"700"),
          text("Premium presentation for remarkable brands",W*.09,H*.68,18,soft,500,"400"),
          text("WEBSITE.COM",W*.70,H*.79,16,ivory,250,"500","right")]

def enforce_safe_layout(objs,W,H):
    # 2-inch physical safe zone for 117x80 back wall.
    sx=W*(2.0/117.0); sy=H*(2.0/80.0)
    right=W-sx; bottom=H-sy
    for o in objs:
        typ=str(o.get("type","")).lower()
        if typ not in ("text","i-text","textbox","image"): continue
        if o.get("decorative") or o.get("background"): continue
        x=float(o.get("left",o.get("x",0)) or 0)
        y=float(o.get("top",o.get("y",0)) or 0)

        if typ in ("text","i-text","textbox"):
            fs=float(o.get("fontSize",32) or 32)
            txt=str(o.get("text",""))
            # Conservative Fabric text width estimate.
            width=float(o.get("width",0) or 0)
            if width<=0: width=max(fs*.60*len(txt),fs)
            height=float(o.get("height",0) or fs*1.25)
            # Shrink only if necessary to fit safe printable width.
            avail=right-sx
            if width>avail and width>0:
                k=avail/width
                fs=max(12,fs*k)
                o["fontSize"]=fs
                width*=k; height*=k
        else:
            width=float(o.get("width",o.get("w",0)) or 0)*float(o.get("scaleX",1) or 1)
            height=float(o.get("height",o.get("h",0)) or 0)*float(o.get("scaleY",1) or 1)

        x=max(sx,min(x,right-width))
        y=max(sy,min(y,bottom-height))
        o["left"]=x; o["top"]=y
    return objs

def make_page(i,W,H,p,inside):
    bg,ivory,gold,soft,dark=p
    # Both sides are full designs. Page 2 uses a related but different
    # composition family, preserving the same brand language.
    if inside:
        page_i=i
        brand_i=i
        page_bg=bg
    else:
        page_i=(i*7+11)%100
        brand_i=(i+2)%100
        page_bg=dark if i%3==0 else bg

    objs=[rect(0,0,W,H,page_bg)]
    art=decoration(page_i,W,H,p)
    for q in art:
        q["opacity"]=min(float(q.get("opacity",1)), .44)
    objs += art
    brand_objs=branding(brand_i,W,H,p)
    dx=((i*13)%17)-8
    dy=((i*11)%13)-6
    for bo in brand_objs:
        if str(bo.get("type","")).lower() in ("text","i-text","textbox","image"):
            bo["left"]=float(bo.get("left",bo.get("x",0)) or 0)+dx
            bo["top"]=float(bo.get("top",bo.get("y",0)) or 0)+dy
    objs += brand_objs

    # V11: no random overlay shapes over customer content.

    # Side marker is metadata only, never visible customer text.
    page=enforce_safe_layout(objs,W,H)
    return page

def preview_svg(i,p):
    bg,ivory,gold,soft,dark=p
    # Every index gets a unique structural signature: family geometry + index-specific
    # border/medallion/rule placement. Text is kept inside x=55..645 / y=55..425.
    family=i%20
    variant=i//20
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="700" height="480" viewBox="0 0 700 480">',
           '<rect width="700" height="480" fill="%s"/>'%bg]
    if family==0:
        parts += ['<path d="M0 0 H205 Q105 115 0 245Z" fill="%s" opacity=".72"/>'%gold,
                  '<path d="M700 480 H510 Q605 370 700 255Z" fill="%s" opacity=".24"/>'%soft]
    elif family==1:
        parts += ['<rect x="26" y="26" width="648" height="428" fill="none" stroke="%s" stroke-width="4"/>'%gold,
                  '<rect x="46" y="46" width="608" height="388" fill="none" stroke="%s" stroke-width="1"/>'%soft]
    elif family==2:
        parts += ['<circle cx="555" cy="240" r="145" fill="none" stroke="%s" stroke-width="5" opacity=".52"/>'%gold,
                  '<circle cx="555" cy="240" r="105" fill="none" stroke="%s" stroke-width="2" opacity=".34"/>'%soft]
    elif family==3:
        parts += ['<polygon points="0,0 280,0 115,480 0,480" fill="%s" opacity=".42"/>'%gold]
    elif family==4:
        parts += ['<path d="M0 420 C180 290 250 100 500 0" fill="none" stroke="%s" stroke-width="18" opacity=".30"/>'%gold,
                  '<path d="M70 480 C240 345 330 155 620 0" fill="none" stroke="%s" stroke-width="4" opacity=".42"/>'%soft]
    elif family==5:
        parts += ['<rect width="105" height="480" fill="%s"/>'%gold,'<rect x="105" width="10" height="480" fill="%s"/>'%soft]
    elif family==6:
        parts += ['<polygon points="0,0 235,0 0,245" fill="%s" opacity=".52"/>'%gold,
                  '<polygon points="700,480 465,480 700,235" fill="%s" opacity=".22"/>'%soft]
    elif family==7:
        parts += ['<ellipse cx="350" cy="240" rx="260" ry="150" fill="none" stroke="%s" stroke-width="3" opacity=".42"/>'%gold]
    elif family==8:
        parts += ['<rect x="45" y="55" width="210" height="370" rx="105" fill="%s" opacity=".15"/>'%gold,
                  '<rect x="525" y="70" width="125" height="340" rx="62" fill="%s" opacity=".10"/>'%soft]
    elif family==9:
        parts += ['<path d="M0 85 H700" stroke="%s" stroke-width="4"/>'%gold,
                  '<path d="M0 395 H700" stroke="%s" stroke-width="2" opacity=".45"/>'%soft]
    elif family==10:
        parts += ['<polygon points="0,480 260,480 0,220" fill="%s" opacity=".48"/>'%gold,
                  '<line x1="260" y1="480" x2="700" y2="40" stroke="%s" stroke-width="3" opacity=".4"/>'%soft]
    elif family==11:
        for n in range(6):
            parts.append('<circle cx="%d" cy="%d" r="%d" fill="%s" opacity=".18"/>'%(70+n*115,65+(n%2)*345,28+n*4,gold))
    elif family==12:
        parts += ['<path d="M0 90 C180 20 250 180 420 90 S610 10 720 95" fill="none" stroke="%s" stroke-width="15" opacity=".24"/>'%gold,
                  '<path d="M0 390 C180 320 250 480 420 390 S610 310 720 395" fill="none" stroke="%s" stroke-width="7" opacity=".22"/>'%soft]
    elif family==13:
        parts += ['<rect x="70" y="55" width="560" height="370" fill="none" stroke="%s" stroke-width="2" transform="rotate(-2 350 240)"/>'%gold,
                  '<rect x="88" y="72" width="524" height="336" fill="none" stroke="%s" stroke-width="1" transform="rotate(2 350 240)"/>'%soft]
    elif family==14:
        parts += ['<circle cx="110" cy="110" r="82" fill="%s" opacity=".20"/>'%gold,
                  '<circle cx="610" cy="390" r="115" fill="%s" opacity=".12"/>'%soft]
    elif family==15:
        parts += ['<polygon points="0,0 700,0 700,65 0,130" fill="%s" opacity=".36"/>'%gold,
                  '<polygon points="0,420 700,350 700,480 0,480" fill="%s" opacity=".20"/>'%soft]
    elif family==16:
        parts += ['<path d="M70 420 Q350 40 630 420" fill="none" stroke="%s" stroke-width="4" opacity=".42"/>'%gold,
                  '<path d="M120 420 Q350 105 580 420" fill="none" stroke="%s" stroke-width="2" opacity=".30"/>'%soft]
    elif family==17:
        parts += ['<rect x="0" y="0" width="275" height="480" fill="%s" opacity=".18"/>'%gold,
                  '<line x1="275" y1="0" x2="275" y2="480" stroke="%s" stroke-width="5"/>'%soft]
    elif family==18:
        parts += ['<polygon points="0,0 150,0 700,390 700,480 570,480 0,90" fill="%s" opacity=".22"/>'%gold]
    else:
        parts += ['<circle cx="350" cy="240" r="150" fill="none" stroke="%s" stroke-width="2" opacity=".38"/>'%gold,
                  '<line x1="200" y1="240" x2="500" y2="240" stroke="%s" stroke-width="3" opacity=".5"/>'%soft]

    # Variant signature makes each of the 5 cycles structurally different.
    if variant==0:
        parts += ['<line x1="58" y1="62" x2="170" y2="62" stroke="%s" stroke-width="4"/>'%gold]
    elif variant==1:
        parts += ['<circle cx="615" cy="78" r="22" fill="none" stroke="%s" stroke-width="3"/>'%gold]
    elif variant==2:
        parts += ['<rect x="55" y="385" width="150" height="5" fill="%s"/>'%gold]
    elif variant==3:
        parts += ['<line x1="620" y1="90" x2="620" y2="210" stroke="%s" stroke-width="4"/>'%gold]
    else:
        parts += ['<rect x="60" y="58" width="580" height="364" fill="none" stroke="%s" stroke-width="1" opacity=".35"/>'%soft]

    mode=i%5
    positions=[(95,"start"),(350,"middle"),(605,"end"),(350,"middle"),(105,"start")]
    x,anchor=positions[mode]
    parts += ['<text x="%d" y="195" fill="%s" font-family="Arial" font-size="22" font-weight="600" text-anchor="%s">YOUR LOGO</text>'%(x,gold,anchor),
              '<text x="%d" y="250" fill="%s" font-family="Arial" font-size="34" font-weight="700" text-anchor="%s">COMPANY NAME</text>'%(x,ivory,anchor),
              '<text x="%d" y="286" fill="%s" font-family="Arial" font-size="14" text-anchor="%s">%s</text>'%(x,soft,anchor,THEMES[i]),
              '<text x="%d" y="325" fill="%s" font-family="Arial" font-size="13" text-anchor="%s">WEBSITE.COM</text>'%(x,ivory,anchor),
              '</svg>']
    return "".join(parts)

class Command(BaseCommand):
    help="Create 100 editable luxury two-page Full Back Wall templates."

    def add_arguments(self,p):
        p.add_argument("--product-id",type=int)
        p.add_argument("--count",type=int,default=100)
        p.add_argument("--replace",action="store_true")
        p.add_argument("--dry-run",action="store_true")
        p.add_argument("--tent-size",choices=["10x10","10x20"],default=None)

    def handle(self,*args,**o):
        if o["product_id"]:
            product=Product.objects.get(pk=o["product_id"])
        else:
            product=(Product.objects.filter(name__icontains="back").filter(name__icontains="wall")
                     .filter(is_active=True).order_by("-id").first())
            if not product: raise CommandError("Full Back Wall product not found. Pass --product-id.")

        specs=[]
        try:
            ss=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
            if len(ss)==2:
                specs=[(x.label,float(x.print_width_in),float(x.print_height_in)) for x in ss]
        except Exception:
            pass

        if not specs:
            width=233 if o["tent_size"]=="10x20" else 117
            specs=[("Inside Back Wall",width,80),("Outside Back Wall",width,80)]

        self.stdout.write("PRODUCT %s: %s"%(product.id,product.name))
        for n,w,h in specs:self.stdout.write("  %s: %g x %g in"%(n,w,h))
        if o["dry_run"]:
            self.stdout.write(self.style.SUCCESS("DRY RUN OK: %d templates x 2 pages"%min(o["count"],100))); return

        if o["replace"]:
            DesignTemplate.objects.filter(product=product,name__startswith="Full Back Wall Luxury").delete()

        folder=Path(settings.MEDIA_ROOT)/"template_previews"; folder.mkdir(parents=True,exist_ok=True)
        count=min(o["count"],100)

        for i in range(count):
            p=palette(i); pages=[]
            for pi,(label,wi,hi) in enumerate(specs):
                W=1200; H=round(W*hi/wi)
                pages.append({"name":label,"surfaceKey":"page-%d"%(pi+1),"background":p[0],
                    "width":W,"height":H,"canvas":{"width":W,"height":H},
                    "physical":{"widthIn":wi,"heightIn":hi,"unit":"in"},
                    "safeMarginIn":2,"objects":make_page(i,W,H,p,inside=(pi==0))})
            data={"version":2,"templateType":"editable-master","generator":GENERATOR,
                  "designFamily":THEMES[i],"designCode":"BACKWALL-%03d"%(i+1),
                  "pageCount":2,"unit":"in","pages":pages,"editable":True,
                  "editorNative":True,"editorSchema":"fabric-primitives-v1","vectorArtwork":True}

            fn="full_back_wall_luxury_v11_%03d.svg"%(i+1)
            svg=preview_svg(i,p).encode("utf-8")
            (folder/fn).write_bytes(svg)
            t,_=DesignTemplate.objects.update_or_create(
                product=product,
                name="Full Back Wall Luxury V11 %03d · %s"%(i+1,THEMES[i]),
                defaults={"json_data":data,"is_active":True})
            if hasattr(t,"preview"):
                t.preview.save(fn,ContentFile(svg),save=False)
                t.save(update_fields=["preview"])

        self.stdout.write(self.style.SUCCESS("Created/updated %d luxury templates; 2 pages each."%count))
