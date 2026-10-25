
from pathlib import Path
import math
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from django.conf import settings
from designer.models import Product, DesignTemplate

GENERATOR="zenvibe-canopy-10x20-v32-all-pages-fully-editable"
DEFAULT_PAGES=[
("Canopy Tent Top",240,160),("Inside Back Wall",233,80),("Outside Back Wall",233,80),
("Inside Right Side Wall",118,38),("Outside Right Side Wall",118,38),
("Inside Left Side Wall",118,38),("Outside Left Side Wall",118,38)]
THEMES=("Botanical Luxe,Wildflower,Rose Garden,Tropical Palm,Cherry Blossom,Eucalyptus,Lavender,Sunflower,Peony,Monstera,"
"Art Deco Gold,Marble Luxe,Terrazzo,Geometric Prism,Corporate Blue,Executive Black,Emerald Gold,Royal Purple,Navy Copper,Minimal Ivory,"
"Tech Grid,Neon Future,Cyber Gradient,Circuit,Data Wave,Construction,Architecture,Real Estate,Finance,Legal,"
"Coffee House,Bakery,Restaurant,Food Truck,Farm Market,Organic,Wellness,Spa,Beauty,Salon,"
"Fitness,Running,Football,Basketball,Motorsport,Outdoor Adventure,Camping,Surf,Coastal,Mountain,"
"Wedding,Engagement,Celebration,Festival,Music,Nightlife,Community,Charity,Education,Graduation,"
"Kids Bright,Candy Pop,Retro 70s,Retro 80s,Y2K,Pop Art,Memphis,Bauhaus,Swiss Editorial,Magazine,"
"Japanese Minimal,Moroccan,Mediterranean,Indian Festive,Nordic,Bohemian,Heritage,Geometric Mosaic,Mosaic,Mandala,"
"Autumn,Winter,Spring,Summer,Christmas,New Year,Halloween,Valentine,Rainbow Event,Canada Event,"
"Abstract Flow,Liquid Shapes,Paper Cut,Line Art,Dot Matrix,Checker,Chevron,Diagonal Motion,Orbit,Premium Monogram").split(",")
PAL=[("#0E7490","#fff","#083344","#F59E0B"),("#0F172A","#fff","#334155","#D4AF37"),
("#064E3B","#fff","#14532D","#FBBF24"),("#4C1D95","#fff","#7E22CE","#F59E0B"),
("#831843","#fff","#450A0A","#EAB308"),("#1E3A8A","#fff","#172554","#F97316"),
("#831843","#fff","#500724","#FDA4AF"),("#134E4A","#fff","#042F2E","#2DD4BF"),
("#3F3F46","#fff","#18181B","#A3E635"),("#312E81","#fff","#1E1B4B","#C084FC")]

def rect(x,y,w,h,c,editable=True,**k):
 d={"type":"rect","left":float(x),"top":float(y),"width":float(w),"height":float(h),"fill":c,
    "customerEditable":bool(editable),"locked":not bool(editable),
    "selectable":bool(editable),"evented":bool(editable)}
 d.update(k); return d

def text(s,x,y,w,z,c,a=0,weight="700"):
 return {"type":"textbox","text":s,"left":float(x),"top":float(y),"width":float(w),
         "fontSize":float(z),"fontFamily":"Poppins","fontWeight":weight,"fill":c,"angle":float(a),
         "textAlign":"center","lineHeight":1.08,"charSpacing":0,
         "originX":"center","originY":"center",
         "customerEditable":True,"locked":False,"selectable":True,"evented":True}

def locked_bar(name,x,y,w,h,c,**k):
 # V32: bars are artwork, not immutable production guides.
 q=rect(x,y,w,h,c,editable=True,**k)
 q["name"]=name
 q["isProductionGuide"]=False
 q["customerEditable"]=True
 q["locked"]=False
 q["selectable"]=True
 q["evented"]=True
 return q

def circle(x,y,r,c,o=.4):
 return {"type":"circle","left":x,"top":y,"radius":r,"width":2*r,"height":2*r,"fill":c,"opacity":o,
         "customerEditable":True,"locked":False,"selectable":True,"evented":True}
def tri(x,y,w,h,c,a=0,o=.5):
 return {"type":"triangle","left":x,"top":y,"width":w,"height":h,"fill":c,"angle":a,"opacity":o,
         "customerEditable":True,"locked":False,"selectable":True,"evented":True}
def vector(path,x,y,c,scale=1,a=0):
 return {"type":"path","path":path,"left":x,"top":y,"fill":c,"scaleX":scale,"scaleY":scale,"angle":a,
         "customerEditable":True,"locked":False,"selectable":True,"evented":True}
LEAF="M0 28 C18 0 48 0 62 10 C48 38 20 48 0 28 Z"
FLOWER="M30 15 C20 -2 5 8 14 24 C-4 24 1 43 19 37 C14 55 35 57 37 39 C52 49 64 31 48 23 C58 7 39 0 30 15 Z"
STAR="M30 0 L37 21 L60 21 L41 34 L48 56 L30 43 L12 56 L19 34 L0 21 L23 21 Z"

def decoration(i,W,H,p):
 bg,fg,dark,ac=p; m=i%20; o=[]
 # 20 materially different luxury composition families.
 if m in (0,1,2,3,4,5):  # botanical / floral families
  count=9 if m%2==0 else 7
  for n in range(count):
   x=55+n*(W-160)/max(1,count-1); y=55+(n%3)*58
   o += [vector(LEAF,x,y,ac,.75+(n%3)*.12,-48+n*13)]
  flowers=3+(m%4)
  for n in range(flowers):
   x=W*.68+n*55; y=70+(n%2)*62
   o += [vector(FLOWER,x,y,fg,.55+(n%2)*.15,n*22),circle(x+25,y+22,8,ac,.9)]
  if m in (2,5):
   for n in range(4): o += [vector(LEAF,70+n*62,H*.62+n*15,fg,1.15,-70+n*16)]
 elif m in (6,7,8):  # Art Deco / geometric
  o += [rect(30,30,W-60,H-60,"transparent",stroke=ac,strokeWidth=5),
        rect(48,48,W-96,H-96,"transparent",stroke=fg,strokeWidth=1)]
  for n in range(7):
   o += [vector(STAR,75+n*165,62+(n%2)*52,ac,.72,n*11)]
  o += [tri(W*.08,H*.18,W*.18,H*.55,ac,0,.22),tri(W*.76,H*.20,W*.18,H*.52,fg,180,.08)]
 elif m in (9,10): # marble prestige
  for n in range(7):
   y=35+n*H/7
   o += [vector("M0 30 C45 -10 85 70 130 30 C175 -10 215 70 260 30", -20,y,ac,2.4,-8+n*3)]
  o += [rect(W*.72,-H*.12,W*.34,H*1.25,fg,angle=16,opacity=.07)]
 elif m in (11,12): # royal monogram
  o += [circle(W*.50,H*.40,min(W,H)*.19,"transparent",1),
        circle(W*.50,H*.40,min(W,H)*.15,"transparent",1)]
  # circles above are decorative fills; add gold crown/star cluster
  for n in range(5): o += [vector(STAR,W*.38+n*55,H*.12,ac,.62,n*8)]
  for n in range(6): o += [vector(LEAF,W*.35+n*52,H*.62,ac,.58,-60+n*24)]
 elif m in (13,14): # celestial
  for n in range(18):
   x=55+(n*71)%(W-100); y=50+((n*47)%(max(80,int(H*.55))))
   o += [vector(STAR,x,y,ac,.30+(n%3)*.10,n*13)]
  o += [circle(W*.82,H*.22,58,fg,.10),circle(W*.79,H*.19,58,bg,1)]
 elif m in (15,16): # opulent waves
  for n in range(6):
   o += [vector("M0 30 C45 -10 85 70 130 30 C175 -10 215 70 260 30", -10,55+n*65,ac,2.5,n*2)]
  o += [rect(0,H*.78,W,H*.22,dark,opacity=.42)]
 elif m in (17,18): # premium angular
  o += [tri(-20,20,W*.52,H*.88,ac,0,.34),tri(W*.66,10,W*.34,H*.82,fg,180,.08),
        rect(W*.04,H*.08,12,H*.70,ac),rect(W*.93,H*.18,12,H*.65,ac)]
 else: # heritage frame
  o += [rect(28,28,W-56,H-56,"transparent",stroke=ac,strokeWidth=5),
        rect(46,46,W-92,H-92,"transparent",stroke=fg,strokeWidth=1)]
  for x,y,a in [(50,50,0),(W-115,50,90),(W-115,H-115,180),(50,H-115,270)]:
   o += [vector(FLOWER,x,y,ac,.65,a),vector(LEAF,x+35,y+35,fg,.55,a+35)]
 return o

def visible_top_guides(W,H):
 # 10x20 roof: four valance boundaries, one central ridge, four diagonal seams.
 v=max(44,round(min(W,H)*.075))
 x1=W*.30; x2=W*.70; cy=H*.50
 thick=max(5,round(min(W,H)*.007))
 c="#111111"; g=[]

 def hbar(name,x,y,w):
  g.append(locked_bar(name,x,y-thick/2,w,thick,c))
 def vbar(name,x,y,h):
  g.append(locked_bar(name,x-thick/2,y,thick,h,c))
 def diag(name,x1_,y1_,x2_,y2_):
  import math
  dx=x2_-x1_; dy=y2_-y1_; ln=math.hypot(dx,dy)
  ang=math.degrees(math.atan2(dy,dx))
  q=locked_bar(name,x1_,y1_-thick/2,ln,thick,c,angle=ang,originX="left",originY="center")
  g.append(q)

 hbar("valance-top",0,v,W); hbar("valance-bottom",0,H-v,W)
 vbar("valance-left",v,0,H); vbar("valance-right",W-v,0,H)
 hbar("roof-centre-ridge",x1,cy,x2-x1)
 diag("roof-top-left",v,v,x1,cy); diag("roof-bottom-left",v,H-v,x1,cy)
 diag("roof-top-right",W-v,v,x2,cy); diag("roof-bottom-right",W-v,H-v,x2,cy)
 return g

def align_top_artwork(objects,W,H):
 """Inset decorative artwork into the roof body so motifs/text are not cut off.
 Production guides and the full-page background are excluded."""
 v=78
 sx=(W-2*v)/W
 sy=(H-2*v)/H
 for q in objects:
  if q.get("type")=="rect" and float(q.get("left",0))==0 and float(q.get("top",0))==0:
   continue
  if q.get("isProductionGuide"):
   continue
  if "left" in q:
   q["left"]=v+float(q["left"])*sx
  if "top" in q:
   q["top"]=v+float(q["top"])*sy
  if "scaleX" in q: q["scaleX"]=float(q["scaleX"])*sx
  else: q["scaleX"]=sx
  if "scaleY" in q: q["scaleY"]=float(q["scaleY"])*sy
  else: q["scaleY"]=sy
 return objects


def seam_rect(x1,y1,x2,y2,color="#111111",thickness=4):
    dx=float(x2)-float(x1); dy=float(y2)-float(y1)
    length=(dx*dx+dy*dy)**0.5
    angle=math.degrees(math.atan2(dy,dx))
    return {
        "type":"rect","left":(float(x1)+float(x2))/2.0,
        "top":(float(y1)+float(y2))/2.0,"width":length,
        "height":float(thickness),"fill":color,"angle":angle,
        "originX":"center","originY":"center",
        "selectable":True,"evented":True,"editable":True,"locked":False,
        "customerEditable":True,"hasControls":True,"hasBorders":True,
        "name":"Editable seam / guide"
    }

def face_text(s,left,top,width,font_size,color,angle=0,weight="700",align="center"):
    return {
        "type":"textbox","text":s,"left":float(left),"top":float(top),
        "width":float(width),"fontSize":float(font_size),
        "fontFamily":"Poppins","fontWeight":weight,"fill":color,
        "angle":float(angle),"textAlign":align,"lineHeight":1.04,"charSpacing":0,
        "originX":"left","originY":"top",
        "customerEditable":True,"locked":False,"selectable":True,"evented":True
    }

def panel_text(s,cx,cy,width,font_size,color,angle=0,weight="500"):
    """Editable textbox whose rotation occurs around its visual centre."""
    return {
        "type":"textbox","text":s,
        "left":float(cx),"top":float(cy),"width":float(width),
        "fontSize":float(font_size),"fontFamily":"Poppins",
        "fontWeight":weight,"fill":color,
        "angle":float(angle),"textAlign":"center",
        "lineHeight":1.02,"charSpacing":0,
        "originX":"center","originY":"center",
        "customerEditable":True,"locked":False,
        "selectable":True,"evented":True
    }

def fitted_panel_text(s,cx,cy,box_w,font_size,color,angle=0,weight="500"):
    """
    Loader-safe text placement.
    The current editor reconstructs Fabric text using left/top anchoring, so merely
    writing originX/originY='center' into JSON is not sufficient.  Compute the
    left/top anchor for the rotated bounding box explicitly so every label remains
    inside its intended canopy panel.
    """
    lines=str(s).split("\n")
    line_h=float(font_size)*1.04
    box_h=max(line_h, len(lines)*line_h)

    # Desired visual bounding-box top-left.
    bx=float(cx)-float(box_w)/2.0
    by=float(cy)-box_h/2.0
    a=int(round(float(angle))) % 360

    if a == 0:
        left,top=bx,by
    elif a == 180:
        # top-left-origin rotation: anchor must be visual bottom-right
        left,top=bx+float(box_w),by+box_h
    elif a == 90:
        # rotated visual bbox is box_h wide x box_w tall
        left=float(cx)+box_h/2.0
        top=float(cy)-float(box_w)/2.0
    elif a == 270:  # -90
        left=float(cx)-box_h/2.0
        top=float(cy)+float(box_w)/2.0
    else:
        left,top=bx,by

    return {
        "type":"textbox","text":s,
        "left":left,"top":top,"width":float(box_w),
        "fontSize":float(font_size),"fontFamily":"Poppins",
        "fontWeight":weight,"fill":color,
        "angle":float(angle),"textAlign":"center",
        "lineHeight":1.04,"charSpacing":0,
        "originX":"left","originY":"top",
        "customerEditable":True,"locked":False,
        "selectable":True,"evented":True
    }

def top_page(i,W,H,p):
    """Recreated Page 1: conservative safe-zone layout for the 240 x 160 roof.

    All editable branding is deliberately pulled well inside the four roof panels.
    This compensates for the current editor loader's rotated-text bounding behaviour
    without changing editor.js. Structural seams remain locked.
    """
    bg,fg,dark,ac=p
    seam="#171717"

    # 240 x 160 physical ratio -> 1200 x 800 logical artboard.
    xL,xR=W*.080,W*.920
    yT,yB=H*.100,H*.900
    jL,jR=W*.300,W*.700
    yM=H*.500
    sw=max(2.5,W*.0022)

    objs=[rect(0,0,W,H,bg,editable=True,name="Editable background")]

    # Unique decoration for every template, kept subtle so branding stays readable.
    art=decoration(i,W,H,p)
    for q in art:
        q["opacity"]=min(float(q.get("opacity",.08)),.055)
        q["customerEditable"]=True
        q["locked"]=False
        q["selectable"]=True
        q["evented"]=True
    objs += art

    # Exact roof construction: four valances, four diagonals and centre ridge.
    objs += [
        seam_rect(0,yT,W,yT,seam,sw),
        seam_rect(0,yB,W,yB,seam,sw),
        seam_rect(xL,0,xL,H,seam,sw),
        seam_rect(xR,0,xR,H,seam,sw),
        seam_rect(xL,yT,jL,yM,seam,sw),
        seam_rect(xL,yB,jL,yM,seam,sw),
        seam_rect(xR,yT,jR,yM,seam,sw),
        seam_rect(xR,yB,jR,yM,seam,sw),
        seam_rect(jL,yM,jR,yM,seam,sw),
    ]

    # IMPORTANT: these anchors are intentionally more conservative than the
    # reference artwork. They keep the complete text inside the visible artboard
    # even with the current Fabric loader's left/top rotation handling.
    objs += [
        # Top valance -- upside down, but safely below the canvas edge.
        fitted_panel_text("ADD YOUR TAG LINE HERE", W*.50, H*.070,
                          W*.36, 22, fg, 180, "600"),

        # Upper roof panel.
        fitted_panel_text("ADD YOUR\nLOGO HERE", W*.50, H*.285,
                          W*.27, 38, fg, 180, "600"),

        # Side roof panels. Pulled toward the centre to prevent rotated bounding
        # boxes from disappearing beyond the left/right clipping boundary.
        fitted_panel_text("ADD YOUR\nLOGO HERE", W*.205, H*.500,
                          H*.205, 28, fg, -90, "600"),
        fitted_panel_text("ADD YOUR\nLOGO HERE", W*.795, H*.500,
                          H*.205, 28, fg, 90, "600"),

        # Lower roof panel. Deliberately raised from the old 70.6% position.
        fitted_panel_text("ADD YOUR\nLOGO HERE", W*.50, H*.625,
                          W*.27, 38, fg, 0, "600"),

        # Bottom valance. Deliberately raised from the old 95.4% position.
        fitted_panel_text("ADD YOUR TAG LINE HERE", W*.50, H*.845,
                          W*.36, 22, fg, 0, "600"),
    ]
    return objs

def wall_page(i,W,H,p,half=False):
 bg,fg,dark,ac=p
 cx=W/2

 # V32: every visible object on pages 2-7 is a normal editable Fabric primitive.
 # Avoid path/vector decorations here: they were the source of the stray grey/image-like artifact.
 o=[rect(0,0,W,H,bg,editable=True,name="Editable background")]

 # Unique but clean edge artwork. Rect/circle/triangle only.
 family=i%10
 if family==0:
  o += [circle(W*.055,H*.10,max(18,H*.055),ac,.88),
        circle(W*.90,H*.67,max(13,H*.040),fg,.35)]
 elif family==1:
  o += [tri(W*.015,H*.05,W*.10,H*.24,ac,-12,.78),
        tri(W*.88,H*.62,W*.08,H*.20,fg,168,.22)]
 elif family==2:
  for n in range(4):
   o += [circle(W*(.04+n*.035),H*.10,max(10,H*.028),ac,.72)]
 elif family==3:
  o += [rect(W*.025,H*.08,W*.018,H*.70,ac,editable=True,opacity=.78,name="Editable accent"),
        rect(W*.955,H*.20,W*.012,H*.55,fg,editable=True,opacity=.25,name="Editable accent")]
 elif family==4:
  o += [tri(W*.01,H*.08,W*.13,H*.34,ac,0,.52),
        circle(W*.90,H*.12,max(16,H*.045),fg,.25)]
 elif family==5:
  o += [rect(W*.03,H*.08,W*.12,H*.035,ac,editable=True,name="Editable accent"),
        rect(W*.85,H*.82,W*.12,H*.035,ac,editable=True,name="Editable accent")]
 elif family==6:
  for n in range(3):
   o += [circle(W*(.06+n*.045),H*.15+n*H*.08,max(12,H*.032),ac,.62)]
 elif family==7:
  o += [tri(W*.02,H*.12,W*.09,H*.26,ac,18,.65),
        tri(W*.89,H*.56,W*.07,H*.22,fg,198,.20)]
 elif family==8:
  o += [rect(W*.02,H*.10,W*.055,H*.055,ac,editable=True,angle=45,name="Editable diamond"),
        rect(W*.91,H*.70,W*.045,H*.045,fg,editable=True,angle=45,opacity=.45,name="Editable diamond")]
 else:
  o += [circle(W*.05,H*.12,max(15,H*.045),ac,.78),
        rect(W*.90,H*.70,W*.055,H*.055,ac,editable=True,angle=45,opacity=.65,name="Editable accent")]

 if half:
  bar_h=max(78,H*.20); by=H-bar_h
  o += [
   text("YOUR LOGO",cx,H*.30,W*.68,max(54,H*.155),fg),
   text("COMPANY NAME",cx,H*.52,W*.64,max(29,H*.082),fg),
   locked_bar("Editable accent bar",0,by,W,bar_h,ac),
   text("EVENTS • TRADE SHOWS • PROMOTIONS",cx,by+bar_h/2,W*.88,max(25,H*.070),dark,0,"800"),
  ]
 else:
  bar_h=max(82,H*.11); by=H-bar_h
  o += [
   text(THEMES[i].upper(),cx,H*.13,W*.68,max(22,H*.040),ac,0,"700"),
   text("YOUR LOGO",cx,H*.33,W*.68,max(62,H*.115),fg),
   text("COMPANY NAME",cx,H*.50,W*.62,max(33,H*.061),fg),
   text("EVENTS • TRADE SHOWS • PROMOTIONS",cx,H*.66,W*.68,max(25,H*.046),fg,0,"600"),
   locked_bar("Editable accent bar",0,by,W,bar_h,ac),
   text("yourcompany.com   •   000 000 0000   •   info@yourcompany.com",
        cx,by+bar_h/2,W*.86,max(19,H*.035),dark,0,"700"),
  ]
 return o

def svg(i,p):
 bg,fg,dark,ac=p
 family=i%25
 variant=(i//25)%4
 art=[]

 # 25 genuinely different preview composition engines × 4 variants = 100.
 if family==0: # botanical corners
  for n in range(7):
   x=35+n*38; y=55+n*22
   art.append(f'<ellipse cx="{x}" cy="{y}" rx="34" ry="11" fill="{ac}" opacity=".82" transform="rotate({-48+n*11} {x} {y})"/>')
  for n in range(6):
   x=565-n*34; y=65+n*24
   art.append(f'<ellipse cx="{x}" cy="{y}" rx="31" ry="10" fill="{fg}" opacity=".55" transform="rotate({48-n*9} {x} {y})"/>')
 elif family==1: # wildflower field
  for n in range(14):
   x=25+n*43; y=315-(n%5)*28
   art.append(f'<line x1="{x}" y1="390" x2="{x+12}" y2="{y}" stroke="{ac}" stroke-width="3"/>')
   art.append(f'<circle cx="{x+12}" cy="{y}" r="{8+(n%3)*3}" fill="{fg}" stroke="{ac}" stroke-width="3"/>')
 elif family==2: # rose garden
  for n in range(9):
   x=45+(n%5)*120; y=55+(n//5)*255
   art.append(f'<circle cx="{x}" cy="{y}" r="27" fill="{ac}" opacity=".85"/>')
   art.append(f'<circle cx="{x+13}" cy="{y-5}" r="17" fill="{fg}" opacity=".72"/>')
 elif family==3: # tropical palm
  for n in range(8):
   x=40+n*76
   art.append(f'<ellipse cx="{x}" cy="{75+(n%2)*245}" rx="65" ry="15" fill="{ac}" opacity=".72" transform="rotate({-55+n*17} {x} {75+(n%2)*245})"/>')
 elif family==4: # cherry blossom branch
  art.append(f'<path d="M0 330 C150 250 210 110 600 55" fill="none" stroke="{ac}" stroke-width="8"/>')
  for n in range(13):
   x=70+n*40; y=300-n*18+(n%3)*24
   art.append(f'<circle cx="{x}" cy="{y}" r="12" fill="{fg}" stroke="{ac}" stroke-width="3"/>')
 elif family==5: # eucalyptus wreath
  art.append(f'<circle cx="300" cy="195" r="135" fill="none" stroke="{ac}" stroke-width="5"/>')
  for n in range(18):
   import math
   ang=n*20*math.pi/180; x=300+135*math.cos(ang); y=195+135*math.sin(ang)
   art.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="25" ry="9" fill="{ac}" opacity=".78" transform="rotate({n*20+35} {x:.1f} {y:.1f})"/>')
 elif family==6: # art deco fan
  for n in range(9):
   art.append(f'<line x1="300" y1="205" x2="{60+n*60}" y2="35" stroke="{ac}" stroke-width="4"/>')
  art += [f'<rect x="24" y="24" width="552" height="352" fill="none" stroke="{ac}" stroke-width="5"/>']
 elif family==7: # marble
  for n in range(8):
   y=35+n*48
   art.append(f'<path d="M0 {y} C100 {y-65} 190 {y+75} 300 {y} S500 {y-55} 600 {y+18}" fill="none" stroke="{ac}" stroke-width="{2+n%3}" opacity=".78"/>')
 elif family==8: # terrazzo
  for n in range(28):
   x=(n*83)%580+10; y=(n*57)%370+15
   art.append(f'<polygon points="{x},{y} {x+18+n%12},{y+5} {x+9},{y+24+n%8}" fill="{ac if n%2 else fg}" opacity=".55"/>')
 elif family==9: # prism
  art += [f'<polygon points="0,0 270,0 380,400 0,400" fill="{ac}" opacity=".38"/>',
          f'<polygon points="600,0 430,0 355,400 600,400" fill="{fg}" opacity=".12"/>',
          f'<polygon points="185,0 420,0 300,400" fill="{dark}" opacity=".38"/>']
 elif family==10: # executive bands
  art += [f'<rect x="0" y="0" width="600" height="65" fill="{ac}"/>',
          f'<rect x="0" y="335" width="600" height="65" fill="{ac}"/>',
          f'<line x1="70" y1="105" x2="530" y2="105" stroke="{fg}" stroke-width="2"/>']
 elif family==11: # royal crest
  art += [f'<circle cx="300" cy="195" r="128" fill="none" stroke="{ac}" stroke-width="6"/>',
          f'<circle cx="300" cy="195" r="105" fill="none" stroke="{fg}" stroke-width="2"/>',
          f'<polygon points="245,90 265,42 300,75 335,38 358,90" fill="{ac}"/>']
 elif family==12: # diamond society
  for n in range(7):
   x=70+n*78
   art.append(f'<polygon points="{x},55 {x+34},89 {x},123 {x-34},89" fill="none" stroke="{ac}" stroke-width="3"/>')
  art.append(f'<polygon points="300,255 355,310 300,365 245,310" fill="{ac}" opacity=".38"/>')
 elif family==13: # celestial
  for n in range(24):
   x=(n*71)%560+20; y=(n*43)%350+20
   r=3+(n%4)
   art.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{ac}"/>')
  art += [f'<circle cx="490" cy="95" r="55" fill="{fg}" opacity=".75"/>',
          f'<circle cx="465" cy="78" r="55" fill="{bg}"/>']
 elif family==14: # luxury waves
  for n in range(7):
   y=45+n*52
   art.append(f'<path d="M0 {y} C100 {y-55} 185 {y+55} 300 {y} S500 {y-45} 600 {y+10}" fill="none" stroke="{ac}" stroke-width="5"/>')
 elif family==15: # heritage frame
  art += [f'<rect x="25" y="25" width="550" height="350" fill="none" stroke="{ac}" stroke-width="6"/>',
          f'<rect x="43" y="43" width="514" height="314" fill="none" stroke="{fg}" stroke-width="1"/>']
  for x,y in [(50,50),(550,50),(50,350),(550,350)]:
   art.append(f'<circle cx="{x}" cy="{y}" r="22" fill="{ac}"/>')
 elif family==16: # arch
  art += [f'<path d="M105 365 V175 C105 55 495 55 495 175 V365" fill="none" stroke="{ac}" stroke-width="12"/>',
          f'<path d="M135 365 V185 C135 90 465 90 465 185 V365" fill="none" stroke="{fg}" stroke-width="2"/>']
 elif family==17: # ribbon
  art += [f'<polygon points="0,75 600,10 600,90 0,155" fill="{ac}" opacity=".68"/>',
          f'<polygon points="0,315 600,245 600,330 0,395" fill="{fg}" opacity=".10"/>']
 elif family==18: # orbit
  for r in (75,115,155):
   art.append(f'<ellipse cx="300" cy="195" rx="{r*1.55}" ry="{r}" fill="none" stroke="{ac}" stroke-width="3" transform="rotate({variant*12} 300 195)"/>')
  art.append(f'<circle cx="445" cy="115" r="14" fill="{fg}"/>')
 elif family==19: # sunburst
  for n in range(20):
   import math
   a=n*18*math.pi/180
   x=300+270*math.cos(a); y=195+190*math.sin(a)
   art.append(f'<line x1="300" y1="195" x2="{x:.1f}" y2="{y:.1f}" stroke="{ac}" stroke-width="4" opacity=".55"/>')
 elif family==20: # checker luxe
  for yy in range(0,400,50):
   for xx in range(0,600,50):
    if (xx//50+yy//50)%2==0:
     art.append(f'<rect x="{xx}" y="{yy}" width="50" height="50" fill="{ac}" opacity=".18"/>')
 elif family==21: # diagonal motion
  for n in range(-2,8):
   x=n*100
   art.append(f'<polygon points="{x},0 {x+65},0 {x+260},400 {x+195},400" fill="{ac}" opacity="{.16+.04*(n%3)}"/>')
 elif family==22: # mosaic
  for n in range(22):
   x=(n*91)%560+20; y=(n*67)%350+20
   art.append(f'<polygon points="{x},{y-18} {x+18},{y} {x},{y+18} {x-18},{y}" fill="{ac if n%2 else fg}" opacity=".38"/>')
 elif family==23: # mandala
  for r in (45,78,112,145):
   art.append(f'<circle cx="300" cy="195" r="{r}" fill="none" stroke="{ac}" stroke-width="3"/>')
  for n in range(12):
   import math
   a=n*30*math.pi/180; x=300+145*math.cos(a); y=195+145*math.sin(a)
   art.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="{fg}" stroke="{ac}" stroke-width="3"/>')
 else: # premium monogram split
  art += [f'<rect x="0" y="0" width="210" height="400" fill="{ac}" opacity=".55"/>',
          f'<line x1="235" y1="45" x2="235" y2="355" stroke="{ac}" stroke-width="4"/>',
          f'<circle cx="410" cy="195" r="105" fill="none" stroke="{ac}" stroke-width="5"/>']

 # Four variants change the composition, not just the colour.
 if variant==1:
  art.append(f'<rect x="18" y="18" width="564" height="364" fill="none" stroke="{fg}" stroke-width="2"/>')
 elif variant==2:
  art += [f'<polygon points="0,0 145,0 0,145" fill="{fg}" opacity=".12"/>',
          f'<polygon points="600,400 455,400 600,255" fill="{ac}" opacity=".35"/>']
 elif variant==3:
  art += [f'<rect x="0" y="330" width="600" height="70" fill="{dark}" opacity=".72"/>',
          f'<line x1="85" y1="62" x2="515" y2="62" stroke="{ac}" stroke-width="3"/>']

 # Preview must show the same physical roof-panel construction as the editor.
 roof = (
  '<g fill="none" stroke="#111827" stroke-width="3">'
  '<line x1="31" y1="31" x2="569" y2="31"/>'
  '<line x1="31" y1="369" x2="569" y2="369"/>'
  '<line x1="31" y1="31" x2="31" y2="369"/>'
  '<line x1="569" y1="31" x2="569" y2="369"/>'
  '<line x1="180" y1="200" x2="420" y2="200"/>'
  '<line x1="31" y1="31" x2="180" y2="200"/>'
  '<line x1="31" y1="369" x2="180" y2="200"/>'
  '<line x1="569" y1="31" x2="420" y2="200"/>'
  '<line x1="569" y1="369" x2="420" y2="200"/>'
  '<line x1="0" y1="31" x2="600" y2="31"/>'
  '<line x1="0" y1="369" x2="600" y2="369"/>'
  '<line x1="31" y1="0" x2="31" y2="400"/>'
  '<line x1="569" y1="0" x2="569" y2="400"/>'
  '</g>'
 )
 return ('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">'
 f'<rect width="600" height="400" fill="{bg}"/>{"".join(art)}{roof}'
 f'<rect x="190" y="145" width="220" height="118" rx="4" fill="{dark}" opacity=".55" stroke="{ac}" stroke-width="2"/>'
 f'<text x="300" y="184" text-anchor="middle" fill="{fg}" font-family="Georgia" font-size="28" font-weight="700">YOUR LOGO</text>'
 f'<line x1="225" y1="207" x2="375" y2="207" stroke="{ac}" stroke-width="3"/>'
 f'<text x="300" y="234" text-anchor="middle" fill="{ac}" font-family="Arial" font-size="13" font-weight="700">{THEMES[i]}</text>'
 f'<text x="300" y="255" text-anchor="middle" fill="{fg}" font-family="Arial" font-size="9">LUXURY COLLECTION</text></svg>')

class Command(BaseCommand):
 help="Create 100 editable seven-page 10x20 canopy templates."
 def add_arguments(self,p):
  p.add_argument("--product-id",type=int); p.add_argument("--count",type=int,default=100)
  p.add_argument("--replace",action="store_true"); p.add_argument("--dry-run",action="store_true")
 def handle(self,*a,**o):
  if o["product_id"]: product=Product.objects.get(pk=o["product_id"])
  else:
   product=Product.objects.filter(name__icontains="10").filter(name__icontains="20").filter(name__icontains="canopy").filter(is_active=True).order_by("-id").first()
   if not product: raise CommandError("10x20 canopy product not found; pass --product-id.")
  specs=list(DEFAULT_PAGES)
  try:
   ss=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
   if len(ss)==7: specs=[(x.label,float(x.print_width_in),float(x.print_height_in)) for x in ss]
  except Exception: pass
  self.stdout.write("PRODUCT %s: %s"%(product.id,product.name))
  for n,w,h in specs:self.stdout.write("  %s: %g x %g in"%(n,w,h))
  if o["dry_run"]:
   self.stdout.write(self.style.SUCCESS("DRY RUN OK: %s templates x 7 pages"%min(o["count"],100))); return
  if o["replace"]:
   # Clean every previous generated 10x20 Luxury card, including versions
   # created before generator tags were corrected.
   DesignTemplate.objects.filter(product=product,name__startswith="10x20 Luxury ").delete()
   DesignTemplate.objects.filter(product=product,name__startswith="10×20 Luxury ").delete()
   DesignTemplate.objects.filter(product=product,json_data__generator__startswith="zenvibe-canopy-10x20-").delete()
  folder=Path(settings.MEDIA_ROOT)/"template_previews"; folder.mkdir(parents=True,exist_ok=True)
  for i in range(min(o["count"],100)):
   p=PAL[i%len(PAL)]; pages=[]
   for pi,(name,wi,hi) in enumerate(specs):
    W=1200; H=round(W*hi/wi)
    objs=top_page(i,W,H,p) if pi==0 else wall_page(i,W,H,p,hi<50)
    pages.append({"name":name,"surfaceKey":"page-%d"%(pi+1),"background":p[0],"width":W,"height":H,
      "canvas":{"width":W,"height":H},"physical":{"widthIn":wi,"heightIn":hi,"unit":"in"},"safeMarginIn":2,"objects":objs})
   data={"version":"32","templateType":"editable-master","generator":GENERATOR,"designFamily":THEMES[i],
    "designCode":"10X20-%03d"%(i+1),"finishStyle":("glossy" if i%4 in (1,3) else "matte"),"compositionVariant":((i//20)%5)+1,"document":{"width":1200,"height":800,"unit":"px"},"pageCount":7,"unit":"in","pages":pages,"editable":True,
    "editorNative":True,"editorSchema":"fabric-primitives-v1","vectorArtwork":True}
   fn="canopy10x20_%03d.svg"%(i+1)
   svg_bytes=svg(i,p).encode("utf-8")
   (folder/fn).write_bytes(svg_bytes)

   # DesignTemplate in this project does NOT have a preview_image field.
   # Create/update only fields that exist on the model, then save the preview
   # through the existing `preview` FileField when available.
   template_name="10×20 V32 %03d · %s · %s"%(i+1,THEMES[i],("Glossy" if i%4 in (1,3) else "Matte"))
   t,_=DesignTemplate.objects.update_or_create(
       product=product,
       name=template_name,
       defaults={"json_data":data,"is_active":True},
   )
   if hasattr(t,"preview"):
       t.preview.save(fn,ContentFile(svg_bytes),save=False)
       t.save(update_fields=["preview"])
  self.stdout.write(self.style.SUCCESS("Created/updated %d templates; 7 pages each."%min(o["count"],100)))
