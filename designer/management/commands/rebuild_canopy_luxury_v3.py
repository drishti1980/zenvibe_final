import copy, math
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-canopy-luxury-v3"
W = 1200

PALETTES = [
("#071B33","#0A66C2","#FFFFFF","#F2B134"),("#111827","#0F766E","#F9FAFB","#F59E0B"),
("#24123A","#7C3AED","#FFFFFF","#D4AF37"),("#3B0A0A","#B91C1C","#FFF7ED","#D4AF37"),
("#0B2B26","#047857","#FFFFFF","#EAB308"),("#171717","#404040","#FFFFFF","#C9A227"),
("#0B1F3A","#2563EB","#F8FAFC","#F97316"),("#2D0A31","#A21CAF","#FFFFFF","#22D3EE"),
("#102A43","#0E7490","#F0F9FF","#FB923C"),("#1E1B4B","#4F46E5","#FFFFFF","#FACC15"),
("#2B1B12","#92400E","#FFF7ED","#D4AF37"),("#0F2F2F","#115E59","#F0FDFA","#F59E0B"),
("#1F2937","#334155","#FFFFFF","#38BDF8"),("#3F0D20","#BE123C","#FFF1F2","#FBBF24"),
("#0C2340","#0057B8","#FFFFFF","#FFB81C"),("#162315","#4D7C0F","#F7FEE7","#D4AF37"),
("#251B37","#6D28D9","#FAF5FF","#EAB308"),("#14213D","#FCA311","#FFFFFF","#E5E5E5"),
("#052E16","#15803D","#FFFFFF","#FBBF24"),("#18181B","#52525B","#FAFAFA","#E11D48"),
]

MOTIFS = ["sweep","ribbon","arch","orbit","crest","wave","facets","frame","chevron","spotlight"]
LAYOUTS = ["center","left","right","split","band","badge","minimal","editorial","corner","hero"]

def base(t,n,x,y,fill,**kw):
    d={"id":n,"name":n,"type":t,"left":float(x),"top":float(y),"fill":fill,
       "opacity":float(kw.pop("opacity",1)),"angle":float(kw.pop("angle",0)),
       "customerEditable":True,"locked":False,"selectable":True,"evented":True}
    d.update(kw); return d

def rect(n,x,y,w,h,c,**kw): return base("rect",n,x,y,c,width=float(w),height=float(h),**kw)
def poly(n,pts,c,**kw): return base("polygon",n,0,0,c,points=[[float(a),float(b)] for a,b in pts],**kw)
def circle(n,x,y,r,c,**kw): return base("circle",n,x,y,c,radius=float(r),**kw)
def text(n,x,y,w,s,size,c,weight=600,align="center",angle=0,**kw):
    return base("textbox",n,x,y,c,width=float(w),text=s,fontSize=float(size),
                font="Montserrat",fontFamily="Montserrat",fontWeight=weight,
                textAlign=align,lineHeight=1.05,angle=angle,**kw)
def line(n,x1,y1,x2,y2,c,sw=3,**kw):
    return base("line",n,0,0,c,points=[float(x1),float(y1),float(x2),float(y2)],
                stroke=c,strokeWidth=float(sw),**kw)

PATHS={
"leaf":"M5 48 C22 8 72 0 96 8 C88 52 56 88 10 94 C31 65 51 43 78 24 C50 37 28 48 5 48 Z",
"star":"M50 0 L61 35 L98 35 L68 57 L79 92 L50 71 L21 92 L32 57 L2 35 L39 35 Z",
"shield":"M50 0 L92 16 L85 62 C80 80 66 92 50 100 C34 92 20 80 15 62 L8 16 Z",
"diamond":"M50 0 L100 50 L50 100 L0 50 Z",
"spark":"M50 0 L60 38 L100 50 L60 62 L50 100 L40 62 L0 50 L40 38 Z",
"hex":"M25 0 L75 0 L100 50 L75 100 L25 100 L0 50 Z",
"wave":"M0 55 C24 8 52 8 76 55 C98 94 120 94 145 55 L145 100 L0 100 Z",
}
def path(n,key,x,y,size,c,angle=0,opacity=1):
    return base("path",n,x,y,c,path=PATHS[key],scaleX=size/100,scaleY=size/100,
                stroke=None,strokeWidth=0,angle=angle,opacity=opacity)

def decoration(motif,w,h,p,k):
    bg,pri,light,acc=p; o=[]; s=min(w,h)
    if motif=="sweep":
        o += [poly("sweep1",[(0,0),(w*.44,0),(w*.26,h),(0,h)],pri,opacity=.92),
              poly("sweep2",[(w*.18,0),(w*.63,0),(w*.48,h),(w*.07,h)],acc,opacity=.42)]
    elif motif=="ribbon":
        o += [poly("rib1",[(0,h*.10),(w*.75,0),(w,h*.23),(0,h*.47)],pri),
              poly("rib2",[(0,h*.72),(w,h*.38),(w,h*.58),(0,h*.91)],acc,opacity=.82)]
    elif motif=="arch":
        o += [circle("arch1",w*.66,-s*.28,s*.52,pri,opacity=.75),
              circle("arch2",w*.72,-s*.19,s*.39,bg,opacity=1),
              path("leaf1","leaf",w*.08,h*.10,s*.16,acc,-25,.8)]
    elif motif=="orbit":
        for i in range(4):
            a=i*math.pi/2; r=s*.105
            o.append(circle(f"orb{i}",w*.5-r+math.cos(a)*s*.24,h*.5-r+math.sin(a)*s*.24,
                            r,pri if i%2==0 else acc,opacity=.35))
        o.append(path("orbitmark","spark",w*.455,h*.405,s*.10,acc,0,.9))
    elif motif=="crest":
        o += [path("crest","shield",w*.40,h*.12,s*.28,pri),
              path("creststar","star",w*.465,h*.215,s*.11,light)]
    elif motif=="wave":
        o += [path("wave1","wave",-w*.02,h*.58,w*.90,pri,0,.88),
              path("wave2","wave",w*.22,h*.67,w*.72,acc,0,.42)]
    elif motif=="facets":
        o += [poly("f1",[(0,0),(w*.38,0),(w*.52,h*.52),(0,h*.82)],pri),
              poly("f2",[(w*.38,0),(w,0),(w*.67,h*.42),(w*.52,h*.52)],acc,opacity=.6),
              poly("f3",[(0,h*.82),(w*.52,h*.52),(w,h),(0,h)],pri,opacity=.5)]
    elif motif=="frame":
        m=s*.045
        o += [rect("frame1",m,m,w-2*m,h-2*m,"rgba(0,0,0,0)",stroke=acc,strokeWidth=max(2,s*.006)),
              rect("frame2",m*1.8,m*1.8,w-3.6*m,h-3.6*m,"rgba(0,0,0,0)",stroke=pri,strokeWidth=max(2,s*.003)),
              path("frameleaf","leaf",m*.5,h*.08,s*.14,acc,-28,.75)]
    elif motif=="chevron":
        for i in range(4):
            y=h*(.06+i*.19)
            o.append(poly(f"ch{i}",[(0,y),(w*.28,y+h*.09),(0,y+h*.18),(w*.12,y+h*.09)],
                          pri if i%2==0 else acc,opacity=.75))
    elif motif=="spotlight":
        o += [poly("sl",[(0,0),(w*.50,h*.52),(0,h)],pri,opacity=.72),
              poly("sr",[(w,0),(w*.50,h*.52),(w,h)],acc,opacity=.58)]
    return o

def brand_block(layout,w,h,p,half=False):
    bg,pri,light,acc=p; s=min(w,h); o=[]
    if layout=="center":
        o += [text("logo",w*.28,h*.28,w*.44,"YOUR LOGO",max(26,s*.095),light,800),
              text("company",w*.27,h*.43,w*.46,"COMPANY NAME",max(16,s*.050),light,700),
              text("tag",w*.25,h*.57,w*.50,"Premium • Professional • Memorable",max(12,s*.032),light,500)]
    elif layout=="left":
        o += [text("eyebrow",w*.08,h*.18,w*.34,"YOUR BRAND",max(12,s*.030),acc,700,"left"),
              text("logo",w*.08,h*.28,w*.38,"YOUR LOGO",max(28,s*.10),light,800,"left"),
              text("company",w*.08,h*.46,w*.40,"COMPANY NAME",max(16,s*.046),light,650,"left"),
              text("tag",w*.08,h*.60,w*.46,"Make your event impossible to miss.",max(12,s*.030),light,500,"left")]
    elif layout=="right":
        o += [text("eyebrow",w*.58,h*.18,w*.32,"EVENT BRANDING",max(12,s*.030),acc,700,"right"),
              text("logo",w*.52,h*.29,w*.38,"YOUR LOGO",max(28,s*.10),light,800,"right"),
              text("company",w*.50,h*.47,w*.40,"COMPANY NAME",max(16,s*.046),light,650,"right"),
              text("tag",w*.48,h*.61,w*.42,"Stand out. Stay remembered.",max(12,s*.030),light,500,"right")]
    elif layout=="split":
        o += [rect("splitcard",w*.08,h*.20,w*.35,h*.52,light,opacity=.94),
              text("logo",w*.11,h*.31,w*.29,"YOUR LOGO",max(25,s*.085),pri,800),
              text("company",w*.11,h*.49,w*.29,"COMPANY NAME",max(14,s*.042),pri,700),
              text("headline",w*.50,h*.30,w*.42,"BUILT TO\nBE SEEN",max(24,s*.075),light,800,"left"),
              text("tag",w*.50,h*.57,w*.39,"Events • Markets • Exhibitions",max(12,s*.030),acc,600,"left")]
    elif layout=="band":
        o += [rect("brandband",0,h*.34,w,h*.31,pri,opacity=.94),
              text("logo",w*.10,h*.405,w*.28,"YOUR LOGO",max(22,s*.070),light,800),
              text("headline",w*.42,h*.39,w*.48,"YOUR COMPANY",max(26,s*.078),light,800,"left"),
              text("tag",w*.42,h*.53,w*.44,"Branding that travels with you.",max(12,s*.030),light,500,"left")]
    elif layout=="badge":
        o += [circle("brandcircle",w*.39,h*.20,s*.18,light,opacity=.96),
              path("badgeicon","diamond",w*.465,h*.275,s*.08,acc),
              text("logo",w*.34,h*.39,w*.32,"YOUR LOGO",max(20,s*.058),pri,800),
              text("company",w*.30,h*.58,w*.40,"COMPANY NAME",max(14,s*.038),light,700)]
    elif layout=="minimal":
        o += [text("logo",w*.08,h*.23,w*.34,"YOUR LOGO",max(28,s*.095),light,800,"left"),
              line("rule",w*.08,h*.45,w*.48,h*.45,acc,max(3,s*.008)),
              text("company",w*.08,h*.50,w*.42,"COMPANY NAME",max(16,s*.045),light,700,"left"),
              text("tag",w*.08,h*.63,w*.44,"Simple. Bold. Recognizable.",max(12,s*.030),light,500,"left")]
    elif layout=="editorial":
        o += [text("number",w*.07,h*.12,w*.18,"01",max(35,s*.15),acc,800,"left"),
              text("logo",w*.27,h*.22,w*.52,"YOUR LOGO",max(30,s*.10),light,800,"left"),
              text("company",w*.28,h*.43,w*.46,"COMPANY NAME",max(16,s*.045),light,700,"left"),
              text("tag",w*.28,h*.58,w*.50,"Corporate events • Outdoor activations",max(12,s*.030),light,500,"left")]
    elif layout=="corner":
        o += [rect("cornercard",w*.06,h*.08,w*.36,h*.42,light,opacity=.94),
              text("logo",w*.09,h*.17,w*.30,"YOUR LOGO",max(24,s*.078),pri,800),
              text("company",w*.09,h*.34,w*.30,"COMPANY NAME",max(14,s*.040),pri,700),
              text("tag",w*.55,h*.63,w*.35,"YOUR MESSAGE HERE",max(16,s*.045),light,700,"right")]
    else: # hero
        o += [text("kicker",w*.20,h*.15,w*.60,"PREMIUM EVENT PRESENCE",max(12,s*.032),acc,700),
              text("logo",w*.18,h*.29,w*.64,"YOUR LOGO",max(34,s*.115),light,800),
              text("company",w*.25,h*.50,w*.50,"COMPANY NAME",max(17,s*.048),light,700),
              text("tag",w*.25,h*.64,w*.50,"SHOW UP • STAND OUT • STAY TOP OF MIND",max(11,s*.027),light,600)]
    return o

def page(label,w,h,wi,hi,bg,objects):
    return {"name":label,"surfaceKey":label.lower().replace(" ","-"),"background":bg,
            "width":int(w),"height":int(h),"canvas":{"width":int(w),"height":int(h)},
            "physical":{"widthIn":float(wi),"heightIn":float(hi),"unit":"in"},
            "safeMarginIn":2,"objects":objects}

def top_page(label,wi,hi,p,motif,layout,k):
    h=W; bg,pri,light,acc=p; m=66; val=92; c=W/2
    # Print-template geometry: 4 roof faces + 4 valances. No overlapping center copy.
    o=[rect("bg",0,0,W,h,bg),
       poly("roof_n",[(m,m),(W-m,m),(c,c)],pri),
       poly("roof_e",[(W-m,m),(W-m,h-m),(c,c)],acc,opacity=.72),
       poly("roof_s",[(W-m,h-m),(m,h-m),(c,c)],pri,opacity=.86),
       poly("roof_w",[(m,h-m),(m,m),(c,c)],acc,opacity=.55),
       rect("val_n",m,0,W-2*m,val,pri),rect("val_s",m,h-val,W-2*m,val,pri),
       rect("val_w",0,m,val,h-2*m,pri),rect("val_e",W-val,m,val,h-2*m,pri)]
    # Decoration is deliberately clipped conceptually to roof composition area by sizing.
    o += decoration(motif,W,h,p,k)
    # Four independent roof-face logo zones like a real canopy-top artwork template.
    o += [text("north_logo",W*.36,h*.17,W*.28,"YOUR LOGO",42,light,800),
          text("south_logo",W*.36,h*.73,W*.28,"YOUR LOGO",42,light,800,angle=180),
          text("west_logo",W*.08,h*.37,W*.28,"YOUR LOGO",42,light,800,angle=-90),
          text("east_logo",W*.64,h*.37,W*.28,"YOUR LOGO",42,light,800,angle=90),
          text("val_n_text",W*.28,25,W*.44,"COMPANY NAME • WEBSITE",24,light,700,angle=180),
          text("val_s_text",W*.28,h-66,W*.44,"COMPANY NAME • WEBSITE",24,light,700),
          text("val_w_text",18,h*.28,h*.44,"COMPANY NAME",24,light,700,angle=-90),
          text("val_e_text",W-18,h*.28,h*.44,"COMPANY NAME",24,light,700,angle=90),
          line("seam1",m,m,W-m,h-m,"#EF4444",2,opacity=.38),
          line("seam2",W-m,m,m,h-m,"#EF4444",2,opacity=.38)]
    return page(label,W,h,wi,hi,bg,o)

def wall_page(label,wi,hi,p,motif,layout,k):
    h=max(260,round(W*hi/wi)); bg,pri,light,acc=p
    o=[rect("bg",0,0,W,h,bg)]
    o += decoration(motif,W,h,p,k)
    o += brand_block(layout,W,h,p,half=hi<50)
    # Keep contact information in a dedicated lower safe strip; no text collisions.
    if hi>=50:
        o += [text("contact",W*.58,h*.79,W*.31,"yourcompany.com  •  000 000 0000",
                   max(12,min(W,h)*.028),acc,650,"right")]
    else:
        o += [rect("lower_band",0,h*.82,W,h*.18,pri),
              text("lower_text",W*.18,h*.855,W*.64,"EVENTS • TRADE SHOWS • PROMOTIONS",
                   max(12,min(W,h)*.035),light,700)]
    return page(label,W,h,wi,hi,bg,o)

def build(product,n):
    surfaces=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
    if len(surfaces)!=7: raise CommandError(f"Expected 7 active Admin surfaces; found {len(surfaces)}")
    motif=MOTIFS[n//10]; layout=LAYOUTS[n%10]; p=PALETTES[n%len(PALETTES)]
    pages=[]
    for i,s in enumerate(surfaces):
        wi=float(s.print_width_in); hi=float(s.print_height_in)
        pages.append(top_page(s.label,wi,hi,p,motif,layout,n) if i==0
                     else wall_page(s.label,wi,hi,p,motif,layout,n))
    return pages,motif,layout

def esc(v): return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
def preview(pg):
    w,h=pg["width"],pg["height"]; z=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">']
    for o in pg["objects"]:
        t=o["type"]; f=o.get("fill","none"); op=o.get("opacity",1)
        if f=="rgba(0,0,0,0)": f="none"
        if t=="rect": z.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" fill="{f}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>')
        elif t=="polygon": z.append(f'<polygon points="{" ".join(f"{x},{y}" for x,y in o["points"])}" fill="{f}" opacity="{op}"/>')
        elif t=="circle":
            r=o["radius"]; z.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{f}" opacity="{op}"/>')
        elif t=="line":
            x1,y1,x2,y2=o["points"]; z.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{o.get("stroke")}" stroke-width="{o.get("strokeWidth",2)}" opacity="{op}"/>')
        elif t=="path":
            z.append(f'<path d="{esc(o["path"])}" fill="{f}" transform="translate({o["left"]} {o["top"]}) scale({o.get("scaleX",1)} {o.get("scaleY",1)}) rotate({o.get("angle",0)} 50 50)" opacity="{op}"/>')
        elif t=="textbox":
            x=o["left"]+o["width"]/2; y=o["top"]+o["fontSize"]
            z.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Montserrat,Arial" font-size="{o["fontSize"]}" font-weight="{o["fontWeight"]}" fill="{f}" opacity="{op}">{esc(o["text"])}</text>')
    z.append("</svg>"); return "".join(z)

class Command(BaseCommand):
    help="Rebuild 100 luxury, aligned, fully editable 7-page 10x10 canopy templates."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=391); p.add_argument("--count",type=int,default=100)
        p.add_argument("--replace",action="store_true"); p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try: product=Product.objects.get(pk=o["product_id"])
        except Product.DoesNotExist: raise CommandError("Product not found")
        count=min(max(o["count"],1),100)
        if o["dry_run"]:
            pages,m,l=build(product,0)
            self.stdout.write(self.style.SUCCESS(f"DRY RUN OK: {count} templates; 7 pages; first={m}/{l}; sizes={[p['physical'] for p in pages]}"))
            return
        if o["replace"]:
            q=DesignTemplate.objects.filter(product=product,json_data__generator__in=[
                "zenvibe-canopy-7page-v1","zenvibe-canopy-7page-editable-v2",GENERATOR])
            d,_=q.delete(); self.stdout.write(f"Removed prior generated canopy records: {d}")
        seen=set()
        for n in range(count):
            pages,motif,layout=build(product,n)
            sig=(motif,layout)
            if sig in seen: raise CommandError("Duplicate composition")
            seen.add(sig)
            data={"version":3,"generator":GENERATOR,"templateType":"editable-master","editable":True,
                  "editorNative":True,"editorSchema":"fabric-primitives-v1","vectorArtwork":True,
                  "pageCount":7,"unit":"in","motif":motif,"layout":layout,
                  "pages":copy.deepcopy(pages),"adminPages":copy.deepcopy(pages)}
            name=f"Canopy Luxury {n+1:03d} · {motif.title()} · {layout.title()}"
            t,_=DesignTemplate.objects.update_or_create(product=product,name=name,
                    defaults={"json_data":data,"is_active":True})
            t.preview.save(f"canopy_luxury_v3_{n+1:03d}.svg",ContentFile(preview(pages[0]).encode()),save=False)
            t.save()
            self.stdout.write(f"{n+1:03d}/{count}: {name}")
        self.stdout.write(self.style.SUCCESS(f"Created {count} aligned editable 7-page luxury canopy templates."))
