
import copy, math, colorsys
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, DesignTemplate

GENERATOR="zenvibe-canopy-100-unique-v9-all-pages-clean"
W=1200
FAMILIES=[
"Botanical Garden","Watercolor Floral","Cherry Blossom","Tropical Leaf","Wildflower","Rose Gold Floral",
"Art Deco","Luxury Marble","Terrazzo","Geometric Luxe","Gradient Mesh","Aurora",
"Corporate Blue","Tech Circuit","Fintech Grid","Construction","Real Estate","Healthcare",
"Coffee House","Bakery","Restaurant","Food Festival","Farmers Market","Organic Produce",
"Fitness","Sports Club","Motorsport","Outdoor Adventure","Surf","Cycling",
"Beauty","Spa","Fashion","Jewellery","Wedding","Photography",
"Kids Festival","Education","Community","Charity","Music Festival","Night Market",
"Minimal Black","Minimal White","Monochrome","Editorial","Swiss Modern","Bauhaus",
"Retro 70s","Memphis","Pop Art","Neon","Cyber","Futurist",
"Earthy Boho","Moroccan","Mediterranean","Japanese Sakura","Scandinavian","Coastal",
"Abstract Waves","Paper Cut","Topographic","Contour Lines","Sunburst","Chevron",
"Diagonal Motion","Ribbon","Orbit","Hexagon","Diamond","Arch",
"Premium Crest","Heritage","Monogram","Signature","Gold Frame","Luxury Dark",
"Eco Green","Sustainable","Solar","Landscape","Pet Brand","Automotive",
"Property Expo","Trade Show","Startup","Professional Services","Finance","Legal",
"Christmas","Spring","Summer","Autumn","Winter","Valentine",
"Festival Confetti","Celebration","Premium Event","Bold Brand"
]

def palette(i):
    h=(i*.61803398875)%1.0
    def hx(hh,s,l):
        r,g,b=colorsys.hls_to_rgb(hh%1, l, s)
        return '#%02X%02X%02X'%(int(r*255),int(g*255),int(b*255))
    bg=hx(h,.55,.22 if i%3 else .88)
    p1=hx(h+.09,.66,.46)
    p2=hx(h+.48,.62,.50)
    acc=hx(h+.17,.78,.56)
    light="#FFFFFF" if i%3 else "#172033"
    return bg,p1,p2,acc,light

def o(t,n,x,y,fill,**kw):
    # Structural/production geometry can be locked so it cannot intercept clicks
    # intended for editable artwork/text or be dragged out of ruler alignment.
    editable = bool(kw.pop("editable", True))
    locked = bool(kw.pop("locked", not editable))
    d={"type":t,"id":n,"name":n,"left":float(x),"top":float(y),"fill":fill,
       "customerEditable":editable,"locked":locked,
       "selectable":editable and not locked,"evented":editable and not locked,
       "opacity":float(kw.pop("opacity",1)),"angle":float(kw.pop("angle",0))}
    d.update(kw); return d
def rect(n,x,y,w,h,c,**kw): return o("rect",n,x,y,c,width=float(w),height=float(h),**kw)
def poly(n,pts,c,**kw):
    """Fabric Polygon coordinates must be local to the object.

    Older versions stored absolute canvas points with left/top=0. Fabric recalculates
    polygon pathOffset/bounds, so the editor could shift or clip artwork even though
    the SVG preview looked correct. Store local points and the real object left/top.
    """
    pts=[(float(x),float(y)) for x,y in pts]
    min_x=min(x for x,_ in pts); min_y=min(y for _,y in pts)
    local=[[x-min_x,y-min_y] for x,y in pts]
    return o("polygon",n,min_x,min_y,c,points=local,**kw)

def circ(n,x,y,r,c,**kw): return o("circle",n,x,y,c,radius=float(r),**kw)

def line(n,x1,y1,x2,y2,c,sw=3,**kw):
    """Render a line as a thin polygon instead of Fabric.Line.

    Fabric.Line applies its own internal origin/path calculations, which caused the
    canopy production seams to shift, shorten, or form a broken V when combined
    with stored left/top values. A thin polygon has deterministic bounds and uses
    the same stable local-coordinate format as every other canopy polygon.
    """
    x1=float(x1); y1=float(y1); x2=float(x2); y2=float(y2)
    sw=max(1.0,float(sw))
    dx=x2-x1; dy=y2-y1
    length=math.hypot(dx,dy)
    if length <= 0.0001:
        return rect(n,x1,y1,sw,sw,c,**kw)
    # perpendicular half-width
    px=-(dy/length)*(sw/2.0)
    py=(dx/length)*(sw/2.0)
    pts=[
        (x1+px,y1+py),
        (x2+px,y2+py),
        (x2-px,y2-py),
        (x1-px,y1-py),
    ]
    return poly(n,pts,c,**kw)
def text(n,x,y,w,s,fs,c,weight=700,align="center",angle=0,**kw):
    return o("textbox",n,x,y,c,width=float(w),text=s,fontSize=float(fs),font="Poppins",
             fontFamily="Poppins",fontWeight=weight,textAlign=align,lineHeight=1.08,
             charSpacing=0,stroke=None,strokeWidth=0,angle=angle,
             originX="center",originY="center",**kw)

PATH={
"leaf":"M5 55 C20 8 70 2 98 10 C91 55 58 91 12 95 C30 68 54 42 82 22 C52 36 28 50 5 55 Z",
"flower":"M50 35 C25 0 0 25 35 50 C0 75 25 100 50 65 C75 100 100 75 65 50 C100 25 75 0 50 35 Z",
"petal":"M50 0 C78 25 80 65 50 100 C20 65 22 25 50 0 Z",
"star":"M50 0 L61 35 L98 35 L68 57 L79 92 L50 71 L21 92 L32 57 L2 35 L39 35 Z",
"hex":"M25 0 L75 0 L100 50 L75 100 L25 100 L0 50 Z",
"diamond":"M50 0 L100 50 L50 100 L0 50 Z",
"arch":"M0 100 A50 50 0 0 1 100 100 L80 100 A30 30 0 0 0 20 100 Z",
"wave":"M0 50 C25 0 50 0 75 50 C100 100 125 100 150 50 L150 100 L0 100 Z",
}
def path(n,k,x,y,s,c,ang=0,op=1):
    return o("path",n,x,y,c,path=PATH[k],scaleX=s/100,scaleY=s/100,stroke=None,strokeWidth=0,angle=ang,opacity=op)

def structural_top(p):
    bg,p1,p2,acc,light=p; m=70; v=92; c=600
    return [
      rect("base",0,0,W,W,bg,editable=False),
      poly("north",[(m,v),(W-m,v),(c,c)],p1,editable=False),
      poly("east",[(W-m,v),(W-m,W-v),(c,c)],p2,editable=False),
      poly("south",[(W-m,W-v),(m,W-v),(c,c)],bg,editable=False),
      poly("west",[(m,W-v),(m,v),(c,c)],p1,opacity=.82,editable=False),
      rect("vn",m,0,W-2*m,v,bg,editable=False),
      rect("vs",m,W-v,W-2*m,v,bg,editable=False),
      rect("vw",0,v,m,W-2*v,bg,editable=False),
      rect("ve",W-m,v,m,W-2*v,bg,editable=False),
    ]

def production_seams(p):
    m=70; v=92
    return [
      line("seamA",m,v,W-m,W-v,"#E12B2B",3,opacity=.92,editable=False),
      line("seamB",W-m,v,m,W-v,"#E12B2B",3,opacity=.92,editable=False),
    ]

def florals(i,p):
    bg,p1,p2,acc,light=p; z=[]
    # floral family gets materially different density/orientation based on its exact family
    density=4+(i%5)
    for j in range(density):
        x=110+(j*173+i*37)%850; y=120+(j*211+i*29)%820; s=55+(j%3)*28
        z += [path(f"flower{j}","flower",x,y,s,acc,(j*19)%50,0.72),
              path(f"leaf{j}a","leaf",x-35,y+35,s*.72,p2,-38,0.78),
              path(f"leaf{j}b","leaf",x+55,y+25,s*.62,p1,35,0.72)]
    return z

def unique_art(i,p):
    fam=FAMILIES[i]; bg,p1,p2,acc,light=p; z=[]
    if i<12: # floral/botanical
        z+=florals(i,p)
        if i in (1,5): z += [circ("wash1",180,170,230,p2,opacity=.18),circ("wash2",760,700,190,acc,opacity=.15)]
    elif i<18: # luxury/corporate
        for j in range(3+(i%3)):
            z.append(poly(f"lux{j}",[(90+j*90,100),(250+j*110,100),(560,600),(380+j*60,600)],acc if j%2 else p2,opacity=.22+.1*j))
    elif i<24: # food/market
        for j in range(7):
            z.append(circ(f"dot{j}",120+j*145,170+(j%2)*80,28+(j%3)*9,acc if j%2 else p2,opacity=.55))
        z += [path("marketleaf","leaf",130,720,180,p2,-30,.55)]
    elif i<30: # sports
        for j in range(5):
            z.append(poly(f"speed{j}",[(40+j*85,160),(110+j*85,160),(430+j*75,520),(360+j*75,520)],acc if j%2 else p2,opacity=.65))
    elif i<36: # beauty/fashion
        z += [path("beauty1","arch",170,150,240,acc,0,.35),path("beauty2","arch",790,720,190,p2,180,.3)]
        for j in range(4): z.append(path(f"bfl{j}","flower",170+j*210,760-(j%2)*100,90,acc,j*17,.45))
    elif i<42: # community/music
        for j in range(14):
            z.append(path(f"conf{j}","star",80+(j*83)%1000,130+(j*137)%850,25+(j%4)*8,[p1,p2,acc][j%3],j*13,.6))
    elif i<48: # minimal/editorial
        z += [rect("edblock",105,155,230,520,p2,opacity=.18),line("edline",105,720,480,720,acc,5)]
        z += [text("edition",115,630,210,f"{i-41:02d}",88,acc,800,"left")]
    elif i<54: # retro/neon
        for j in range(6):
            z.append(circ(f"retro{j}",80+j*155,150+(j%2)*160,70,[p1,p2,acc][j%3],opacity=.5))
    elif i<60: # world styles
        z += florals(i,p) if i in (57,58) else [path("world","arch",430,420,340,acc,0,.28)]
    elif i<66: # abstract
        if i%2: 
            for j in range(4): z.append(path(f"wave{j}","wave",50+j*210,180+j*120,230,[p1,p2,acc][j%3],0,.35))
        else:
            for j in range(6): z.append(line(f"cont{j}",100,180+j*90,1100,100+j*105,[p1,p2,acc][j%3],4,opacity=.35))
    elif i<72:
        for j in range(5): z.append(poly(f"geo{j}",[(90+j*150,120),(260+j*120,120),(520+j*70,600),(390+j*80,600)],[p1,p2,acc][j%3],opacity=.42))
    elif i<78:
        z += [path("emblem","diamond" if i%2 else "hex",470,470,260,acc,0,.32),
              rect("emblemframe",420,420,360,360,"rgba(0,0,0,0)",stroke=acc,strokeWidth=5)]
    elif i<84:
        z += florals(i,p) if i==81 else [path("eco","leaf",120,650,240,p2,-30,.45)]
    elif i<90:
        z += [rect("corpbar",0,190,430,120,acc,opacity=.55),poly("corpangle",[(0,310),(430,310),(620,600),(0,600)],p2,opacity=.25)]
    elif i<96: # seasonal
        z += florals(i,p) if i in (91,92,93) else [path("season","star",180,170,150,acc,0,.55),path("season2","star",820,760,110,p2,20,.45)]
    else:
        for j in range(12): z.append(circ(f"cele{j}",90+(j*89)%1000,120+(j*151)%900,18+(j%4)*8,[p1,p2,acc][j%3],opacity=.7))
    return z

def branding(i,p):
    bg,p1,p2,acc,light=p
    mode=i%5
    headline=["YOUR LOGO","YOUR COMPANY","YOUR LOGO","YOUR BRAND","YOUR LOGO"][mode]
    company=["COMPANY NAME","YOUR COMPANY NAME","COMPANY NAME","BRAND NAME","COMPANY NAME"][mode]
    return [
      text("north_logo",600,250,430,headline,64,light,800,angle=180),
      text("north_company",600,325,400,company,34,light,700,angle=180),
      text("south_logo",600,950,430,headline,64,light,800),
      text("south_company",600,875,400,company,34,light,700),
      text("west_logo",250,600,430,headline,64,light,800,angle=-90),
      text("west_company",325,600,400,company,34,light,700,angle=-90),
      text("east_logo",950,600,430,headline,64,light,800,angle=90),
      text("east_company",875,600,400,company,34,light,700,angle=90),
      text("valance_top",600,46,650,"EVENTS • TRADE SHOWS • PROMOTIONS",30,light,700,angle=180),
      text("valance_bottom",600,1154,650,"EVENTS • TRADE SHOWS • PROMOTIONS",30,light,700),
      text("valance_left",46,600,650,"EVENTS • TRADE SHOWS • PROMOTIONS",30,light,700,angle=-90),
      text("valance_right",1154,600,650,"EVENTS • TRADE SHOWS • PROMOTIONS",30,light,700,angle=90),
    ]

def wall(i,w,h,p,half):
    fam=FAMILIES[i]; bg,p1,p2,acc,light=p
    z=[rect("wallbase",0,0,w,h,bg,editable=False)]
    cx=w/2

    # Edge-only decoration keeps the central brand area clean.
    if i<12:
        motif=min(115,h*.22)
        z += [
          path("wall_leaf_left","leaf",32,h*.10,motif,p2,-28,.24),
          path("wall_flower_right","flower",w-motif-38,h*.62,motif*.82,acc,18,.20),
        ]
    else:
        mode=i%6
        if mode==0:
            z += [rect("wall_edge_left",0,0,w*.08,h,p1,opacity=.18)]
        elif mode==1:
            z += [path("wall_leaf_right","leaf",w-min(170,h*.30)-35,h*.12,min(170,h*.30),p2,-25,.20)]
        elif mode==2:
            z += [circ("wall_circle",w*.84,-h*.18,h*.34,acc,opacity=.12)]
        elif mode==3:
            z += [poly("wall_angle",[(0,0),(w*.12,0),(w*.07,h),(0,h)],p1,opacity=.18)]
        elif mode==4:
            z += [path("wall_mark","diamond",w*.86,h*.64,min(110,h*.20),acc,0,.15)]
        else:
            z += [path("wall_mark","arch",w*.03,h*.62,min(110,h*.20),p2,0,.15)]

    if half:
        # Pages 4-7: 117 x 38. Large centered brand block and a TRUE full-width
        # promotional valance extending exactly from x=0 to x=w.
        bar_h=max(70,h*.19)
        bar_y=h-bar_h
        z += [
          text("wall_logo",cx,h*.30,w*.72,"YOUR LOGO",max(50,h*.155),light,800),
          text("wall_company",cx,h*.52,w*.68,"COMPANY NAME",max(27,h*.080),light,700),
          rect("wall_full_width_valance",0,bar_y,w,bar_h,p1,editable=False),
          text("wall_valance_text",cx,bar_y+bar_h/2,w*.88,
               "EVENTS • TRADE SHOWS • PROMOTIONS",max(23,h*.065),light,800),
        ]
    else:
        # Pages 2-3: 117 x 80. Everything is centered with generous left/right
        # margins, preventing the clipping visible in the user's screenshots.
        contact_h=max(72,h*.105)
        contact_y=h-contact_h
        z += [
          text("wall_family",cx,h*.14,w*.72,fam.upper(),max(22,h*.045),acc,700),
          text("wall_logo",cx,h*.34,w*.72,"YOUR LOGO",max(58,h*.120),light,800),
          text("wall_company",cx,h*.51,w*.68,"COMPANY NAME",max(31,h*.064),light,700),
          text("wall_message",cx,h*.67,w*.72,
               "EVENTS • TRADE SHOWS • PROMOTIONS",max(23,h*.047),light,650),
          rect("wall_contact_bar",0,contact_y,w,contact_h,p1,editable=False),
          text("wall_contact",cx,contact_y+contact_h/2,w*.86,
               "yourcompany.com   •   000 000 0000   •   info@yourcompany.com",
               max(18,h*.034),light,700),
        ]
    return z

def page(label,wi,hi,objs,bg):
    h=W if abs(wi-hi)<.01 else round(W*hi/wi)
    return {"name":label,"surfaceKey":label.lower().replace(" ","-"),"background":bg,
            "width":W,"height":h,"documentWidth":W,"documentHeight":h,
            "canvas":{"width":W,"height":h},
            "physical":{"widthIn":wi,"heightIn":hi,"unit":"in"},"safeMarginIn":2,"objects":objs}

def esc(v): return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def preview(pg):
    z=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pg["width"]} {pg["height"]}">']
    for a in pg["objects"]:
        t=a["type"]; f=a.get("fill","none"); op=a.get("opacity",1)
        if f=="rgba(0,0,0,0)": f="none"
        if t=="rect": z.append(f'<rect x="{a["left"]}" y="{a["top"]}" width="{a["width"]}" height="{a["height"]}" fill="{f}" stroke="{a.get("stroke") or "none"}" stroke-width="{a.get("strokeWidth",0)}" opacity="{op}"/>')
        elif t=="polygon":
            left=float(a.get("left",0)); top=float(a.get("top",0))
            pts=" ".join(f"{left+float(x)},{top+float(y)}" for x,y in a["points"])
            z.append(f'<polygon points="{pts}" fill="{f}" opacity="{op}"/>')
        elif t=="circle":
            r=a["radius"]; z.append(f'<circle cx="{a["left"]+r}" cy="{a["top"]+r}" r="{r}" fill="{f}" opacity="{op}"/>')
        elif t=="line":
            left=float(a.get("left",0)); top=float(a.get("top",0))
            x1,y1,x2,y2=a["points"]
            z.append(f'<line x1="{left+float(x1)}" y1="{top+float(y1)}" x2="{left+float(x2)}" y2="{top+float(y2)}" stroke="{a.get("stroke")}" stroke-width="{a.get("strokeWidth",2)}" opacity="{op}"/>')
        elif t=="path": z.append(f'<path d="{esc(a["path"])}" fill="{f}" transform="translate({a["left"]} {a["top"]}) scale({a.get("scaleX",1)} {a.get("scaleY",1)}) rotate({a.get("angle",0)} 50 50)" opacity="{op}"/>')
        elif t=="textbox":
            x=float(a["left"]); y=float(a["top"])
            angle=float(a.get("angle",0) or 0)
            transform=f' transform="rotate({angle} {x} {y})"' if angle else ""
            z.append(f'<text x="{x}" y="{y}" dominant-baseline="middle" text-anchor="middle" font-family="Poppins,Arial,sans-serif" font-size="{a["fontSize"]}" font-weight="{a["fontWeight"]}" fill="{f}" opacity="{op}"{transform}>{esc(a["text"])}</text>')
    z.append("</svg>"); return "".join(z)

class Command(BaseCommand):
    help="Create 100 materially unique, editable, seven-page canopy templates."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=391); p.add_argument("--replace",action="store_true"); p.add_argument("--dry-run",action="store_true")
    def handle(self,*args,**opt):
        product=Product.objects.filter(pk=opt["product_id"]).first()
        if not product: raise CommandError("Product not found")
        surfaces=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
        if len(surfaces)!=7:
            raise CommandError(
                f"Expected 7 active Admin print surfaces for this canopy product, found {len(surfaces)}. "
                "Configure them in Django Admin first; this template command will not guess ruler dimensions."
            )
        for surface in surfaces:
            if float(surface.print_width_in or 0) <= 0 or float(surface.print_height_in or 0) <= 0:
                raise CommandError(
                    f'Admin surface "{surface.label}" is missing a valid print width/height in inches.'
                )
        if len(FAMILIES)!=100: raise CommandError(f"Internal family count is {len(FAMILIES)}, expected 100")
        if opt["dry_run"]:
            self.stdout.write(self.style.SUCCESS("DRY RUN OK: 100 named design families, including floral/botanical, luxury, corporate, food, sport, beauty, seasonal and abstract."))
            return
        if opt["replace"]:
            q=DesignTemplate.objects.filter(product=product,json_data__generator__in=[
              "zenvibe-canopy-7page-v1","zenvibe-canopy-7page-editable-v2",
               "zenvibe-canopy-luxury-v3","zenvibe-canopy-luxury-v4-aligned",
               "zenvibe-canopy-100-unique-v5",
              "zenvibe-canopy-100-unique-v6-clean",
              "zenvibe-canopy-100-unique-v7-reference-clean",
              "zenvibe-canopy-100-unique-v8-large-type",
              GENERATOR])
            d,_=q.delete(); self.stdout.write(f"Removed prior generated records: {d}")
        for i,fam in enumerate(FAMILIES):
            p=palette(i); pages=[]
            for j,s in enumerate(surfaces):
                wi=float(s.print_width_in); hi=float(s.print_height_in)
                if j==0:
                    objs=structural_top(p)+unique_art(i,p)+branding(i,p)+production_seams(p)
                    # Both locked production diagonals are appended LAST and remain visible.
                else:
                    h=round(W*hi/wi); objs=wall(i,W,h,p,hi<50)
                pages.append(page(s.label,wi,hi,objs,p[0]))
            # Publish the exact Fabric coordinate system used by the generator.
            # Physical dimensions/rulers still come exclusively from Admin surfaces.
            first_page=pages[0]
            data={"version":9,"generator":GENERATOR,"templateType":"editable-master","editable":True,
                  "editorNative":True,"editorSchema":"fabric-primitives-v1","vectorArtwork":True,
                  "document":{"width":int(first_page["width"]),"height":int(first_page["height"]),
                              "unit":"in","physical":copy.deepcopy(first_page["physical"])},
                  "pageCount":len(pages),"unit":"in","designFamily":fam,"designNumber":i+1,
                  "pages":copy.deepcopy(pages),"adminPages":copy.deepcopy(pages)}
            name=f"Canopy {i+1:03d} · {fam}"
            t,_=DesignTemplate.objects.update_or_create(product=product,name=name,defaults={"json_data":data,"is_active":True})
            t.preview.save(f"canopy_unique_v9_{i+1:03d}.svg",ContentFile(preview(pages[0]).encode()),save=False)
            t.save()
            self.stdout.write(f"{i+1:03d}/100: {fam}")
        self.stdout.write(self.style.SUCCESS("Created 100 clean editable 7-page canopy templates with corrected full and half wall layouts."))
