
import copy, math
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-canopy-luxury-v4-aligned"
W = 1200

PALETTES = [
("#0D5C4B","#5D8E33","#C19A13","#F8FAFC"),
("#2F2F2F","#7B6A32","#A78615","#FFFFFF"),
("#2457D6","#8A7894","#C7651F","#FFFFFF"),
("#A219B7","#6E67D8","#2EA6C1","#FFFFFF"),
("#111827","#334155","#B98A2F","#FFFFFF"),
("#1E3A5F","#0F766E","#D97706","#FFFFFF"),
("#40265E","#7C3AED","#C9A227","#FFFFFF"),
("#4A1010","#991B1B","#D4AF37","#FFFFFF"),
("#0B3B2E","#15803D","#D4AF37","#FFFFFF"),
("#172554","#1D4ED8","#F59E0B","#FFFFFF"),
("#2B1B12","#7C4A1D","#C8A24A","#FFFFFF"),
("#0F172A","#475569","#22C55E","#FFFFFF"),
("#3F0D20","#BE123C","#F59E0B","#FFFFFF"),
("#102A43","#0E7490","#F97316","#FFFFFF"),
("#1E1B4B","#4338CA","#FACC15","#FFFFFF"),
("#162315","#4D7C0F","#D4AF37","#FFFFFF"),
("#251B37","#6D28D9","#EAB308","#FFFFFF"),
("#14213D","#FCA311","#E5E5E5","#FFFFFF"),
("#052E16","#15803D","#FBBF24","#FFFFFF"),
("#18181B","#52525B","#E11D48","#FFFFFF"),
]

LAYOUTS = [
    "monogram","stripe","crest","corner","minimal",
    "split","arch","editorial","premium","signature"
]

def obj(t,n,x,y,fill,**kw):
    d={"type":t,"id":n,"name":n,"left":float(x),"top":float(y),"fill":fill,
       "opacity":float(kw.pop("opacity",1)),"angle":float(kw.pop("angle",0)),
       "customerEditable":True,"locked":False,"selectable":True,"evented":True}
    d.update(kw)
    return d

def rect(n,x,y,w,h,c,**kw):
    return obj("rect",n,x,y,c,width=float(w),height=float(h),**kw)

def poly(n,pts,c,**kw):
    return obj("polygon",n,0,0,c,points=[[float(a),float(b)] for a,b in pts],**kw)

def circle(n,x,y,r,c,**kw):
    return obj("circle",n,x,y,c,radius=float(r),**kw)

def line(n,x1,y1,x2,y2,c,sw=2,**kw):
    return obj("line",n,0,0,c,points=[float(x1),float(y1),float(x2),float(y2)],
               stroke=c,strokeWidth=float(sw),**kw)

def text(n,x,y,w,s,size,c,weight=700,align="center",angle=0,**kw):
    return obj("textbox",n,x,y,c,width=float(w),text=s,fontSize=float(size),
               font="Montserrat",fontFamily="Montserrat",fontWeight=weight,
               textAlign=align,lineHeight=1.0,angle=angle,**kw)

def top_base(p):
    bg,face2,face3,light = p
    m=70
    v=92
    c=W/2
    # Fixed production geometry. Every template uses this exact structure.
    o=[
        rect("canvas_bg",0,0,W,W,bg),
        # 4 roof faces
        poly("roof_top",[(m,v),(W-m,v),(c,c)],face2),
        poly("roof_right",[(W-m,v),(W-m,W-v),(c,c)],face3),
        poly("roof_bottom",[(W-m,W-v),(m,W-v),(c,c)],bg),
        poly("roof_left",[(m,W-v),(m,v),(c,c)],face2,opacity=.86),
        # fixed valances
        rect("valance_top",m,0,W-2*m,v,bg),
        rect("valance_bottom",m,W-v,W-2*m,v,bg),
        rect("valance_left",0,v,m,W-2*v,bg),
        rect("valance_right",W-m,v,m,W-2*v,bg),
        # corner tabs
        rect("tab_tl",0,0,m,v,bg), rect("tab_tr",W-m,0,m,v,bg),
        rect("tab_bl",0,W-v,m,v,bg), rect("tab_br",W-m,W-v,m,v,bg),
        # guide seams
        line("seam1",m,v,W-m,W-v,"#EF4444",1,opacity=.35),
        line("seam2",W-m,v,m,W-v,"#EF4444",1,opacity=.35),
    ]
    return o

def top_design(layout,p,idx):
    bg,face2,face3,light=p
    acc = "#D4AF37" if idx % 2 == 0 else "#F59E0B"
    o=[]
    # Every layout stays inside known face-safe zones and does not cross face centers.
    if layout=="monogram":
        o += [circle("mark",515,515,85,light,opacity=.16),
              text("center_mark",500,525,200,"ZV",72,light,800)]
    elif layout=="stripe":
        o += [poly("stripe_top",[(280,120),(350,120),(520,430),(450,430)],acc,opacity=.78),
              poly("stripe_bottom",[(750,770),(820,770),(920,1080),(850,1080)],acc,opacity=.78)]
    elif layout=="crest":
        o += [rect("crest_box",500,490,200,220,"rgba(0,0,0,0)",stroke=acc,strokeWidth=6),
              text("crest_text",510,560,180,"EST.\n2026",32,light,800)]
    elif layout=="corner":
        o += [poly("corner_tl",[(70,92),(300,92),(70,320)],acc,opacity=.72),
              poly("corner_br",[(1130,1108),(900,1108),(1130,880)],acc,opacity=.72)]
    elif layout=="minimal":
        o += [line("min_rule1",395,600,805,600,acc,4),
              line("min_rule2",470,620,730,620,light,2,opacity=.6)]
    elif layout=="split":
        o += [poly("split_top",[(600,600),(830,250),(930,250),(650,600)],acc,opacity=.60),
              poly("split_bottom",[(600,600),(370,950),(270,950),(550,600)],acc,opacity=.60)]
    elif layout=="arch":
        o += [circle("arch_outer",480,470,120,acc,opacity=.32),
              circle("arch_inner",515,505,85,bg,opacity=1)]
    elif layout=="editorial":
        o += [text("edition",440,470,320,"PREMIUM",26,acc,700),
              text("edition_no",470,520,260,"01",82,light,800)]
    elif layout=="premium":
        o += [rect("premium_frame",410,420,380,360,"rgba(0,0,0,0)",stroke=acc,strokeWidth=5),
              line("premium_rule",470,510,730,510,acc,3)]
    else: # signature
        o += [text("signature",430,500,340,"SIGNATURE",34,acc,700),
              line("sig_line",445,555,755,555,light,2,opacity=.7)]
    return o

def top_branding(p):
    bg,face2,face3,light=p
    # Logos are fixed in true roof-face safe areas; never piled in centre.
    return [
        text("logo_top",430,185,340,"YOUR LOGO",44,light,800),
        text("logo_bottom",430,930,340,"YOUR LOGO",44,light,800,angle=180),
        text("logo_left",105,430,280,"YOUR LOGO",42,light,800,angle=-90),
        text("logo_right",815,430,280,"YOUR LOGO",42,light,800,angle=90),

        text("val_top",365,28,470,"COMPANY NAME • WEBSITE",20,light,700,angle=180),
        text("val_bottom",365,1136,470,"COMPANY NAME • WEBSITE",20,light,700),
        text("val_left",8,395,410,"COMPANY NAME",18,light,700,angle=-90),
        text("val_right",1147,395,410,"COMPANY NAME",18,light,700,angle=90),
    ]

def wall_objects(w,h,p,layout,is_half):
    bg,face2,face3,light=p
    acc="#D4AF37"
    o=[rect("wall_bg",0,0,w,h,bg)]

    # Fixed safe content system: 6% outer margin, 2in physical safety already represented by editor.
    mx=w*.07; my=h*.10

    # Decorative composition - never overlaps brand zone.
    if layout in ("monogram","crest","premium"):
        o += [rect("accent_panel",mx,my,w*.26,h*.78,face2,opacity=.90)]
    elif layout in ("stripe","split"):
        o += [poly("accent_poly",[(0,0),(w*.28,0),(w*.18,h),(0,h)],face2,opacity=.86)]
    elif layout in ("corner","arch"):
        o += [circle("accent_circle",w*.73,-h*.18,h*.42,face3,opacity=.48)]
    elif layout in ("minimal","signature"):
        o += [line("accent_rule",mx,h*.24,w*.40,h*.24,acc,4)]
    else:
        o += [rect("accent_top",0,0,w,h*.12,face2)]

    # Brand zone anchored independently from decoration.
    brand_x=w*.36 if layout in ("monogram","crest","premium") else w*.10
    brand_w=w*.54 if brand_x>w*.2 else w*.80

    o += [
        text("eyebrow",brand_x,my,brand_w,"PREMIUM EVENT BRANDING",max(12,h*.045),acc,700,"left"),
        text("logo",brand_x,my+h*.13,brand_w,"YOUR LOGO",max(26,h*.12),light,800,"left"),
        text("company",brand_x,my+h*.31,brand_w,"COMPANY NAME",max(18,h*.075),light,700,"left"),
        text("message",brand_x,my+h*.46,brand_w,"YOUR MESSAGE • YOUR EVENT • YOUR BRAND",
             max(11,h*.038),light,500,"left"),
    ]

    if is_half:
        band_h=h*.19
        o += [rect("bottom_band",0,h-band_h,w,band_h,face3),
              text("bottom_text",w*.18,h-band_h+h*.045,w*.64,
                   "EVENTS • TRADE SHOWS • PROMOTIONS",max(11,h*.045),light,700)]
    else:
        o += [text("contact",brand_x,my+h*.66,brand_w,
                   "www.yourcompany.com   •   000 000 0000",
                   max(11,h*.036),acc,600,"left")]
    return o

def make_page(label,wi,hi,p,layout,idx):
    if abs(wi-hi)<0.001 and wi >= 100:
        return {
            "name":label,"surfaceKey":label.lower().replace(" ","-"),
            "background":p[0],"width":W,"height":W,
            "canvas":{"width":W,"height":W},
            "physical":{"widthIn":wi,"heightIn":hi,"unit":"in"},
            "safeMarginIn":2,
            "objects":top_base(p)+top_design(layout,p,idx)+top_branding(p)
        }
    h=round(W*hi/wi)
    return {
        "name":label,"surfaceKey":label.lower().replace(" ","-"),
        "background":p[0],"width":W,"height":h,
        "canvas":{"width":W,"height":h},
        "physical":{"widthIn":wi,"heightIn":hi,"unit":"in"},
        "safeMarginIn":2,
        "objects":wall_objects(W,h,p,layout,hi<50)
    }

def esc(v):
    return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def preview(pg):
    z=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {pg["width"]} {pg["height"]}">']
    for o in pg["objects"]:
        t=o["type"]; f=o.get("fill","none"); op=o.get("opacity",1)
        if f=="rgba(0,0,0,0)": f="none"
        if t=="rect":
            z.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" fill="{f}" stroke="{o.get("stroke") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{op}"/>')
        elif t=="polygon":
            pts=" ".join(f"{x},{y}" for x,y in o["points"])
            z.append(f'<polygon points="{pts}" fill="{f}" opacity="{op}"/>')
        elif t=="circle":
            r=o["radius"]
            z.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{f}" opacity="{op}"/>')
        elif t=="line":
            x1,y1,x2,y2=o["points"]
            z.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{o.get("stroke")}" stroke-width="{o.get("strokeWidth",2)}" opacity="{op}"/>')
        elif t=="textbox":
            # Preview intentionally renders one line compactly; editor remains full Fabric textbox.
            x=o["left"]+o["width"]/2
            y=o["top"]+o["fontSize"]
            z.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Montserrat,Arial" font-size="{o["fontSize"]}" font-weight="{o["fontWeight"]}" fill="{f}" opacity="{op}">{esc(o["text"].replace(chr(10)," "))}</text>')
    z.append("</svg>")
    return "".join(z)

class Command(BaseCommand):
    help="Rebuild aligned 100-template 7-page canopy library with fixed production geometry."
    def add_arguments(self,p):
        p.add_argument("--product-id",type=int,default=391)
        p.add_argument("--count",type=int,default=100)
        p.add_argument("--replace",action="store_true")
        p.add_argument("--dry-run",action="store_true")

    def handle(self,*args,**opt):
        product=Product.objects.filter(pk=opt["product_id"]).first()
        if not product:
            raise CommandError("Product not found")

        surfaces=list(product.print_surfaces.filter(is_active=True).order_by("sort_order","id"))
        if len(surfaces)!=7:
            raise CommandError(f"Expected exactly 7 active Admin surfaces, found {len(surfaces)}")

        count=min(max(opt["count"],1),100)

        if opt["dry_run"]:
            self.stdout.write("Admin surfaces:")
            for i,s in enumerate(surfaces,1):
                self.stdout.write(f"  {i}. {s.label}: {float(s.print_width_in):.3f} x {float(s.print_height_in):.3f} in")
            self.stdout.write(self.style.SUCCESS("DRY RUN OK: V4 fixed geometry, aligned logo zones, 7 pages."))
            return

        if opt["replace"]:
            qs=DesignTemplate.objects.filter(
                product=product,
                json_data__generator__in=[
                    "zenvibe-canopy-7page-v1",
                    "zenvibe-canopy-7page-editable-v2",
                    "zenvibe-canopy-luxury-v3",
                    GENERATOR,
                ],
            )
            deleted,_=qs.delete()
            self.stdout.write(f"Removed prior generated records: {deleted}")

        for i in range(count):
            palette=PALETTES[(i//5)%len(PALETTES)]
            layout=LAYOUTS[i%len(LAYOUTS)]

            pages=[]
            for s in surfaces:
                pages.append(
                    make_page(
                        s.label,
                        float(s.print_width_in),
                        float(s.print_height_in),
                        palette,
                        layout,
                        i
                    )
                )

            data={
                "version":4,
                "generator":GENERATOR,
                "templateType":"editable-master",
                "editable":True,
                "editorNative":True,
                "editorSchema":"fabric-primitives-v1",
                "pageCount":7,
                "unit":"in",
                "layout":layout,
                "pages":copy.deepcopy(pages),
                "adminPages":copy.deepcopy(pages),
            }

            name=f"Canopy Luxury Aligned {i+1:03d} · {layout.title()}"
            t,_=DesignTemplate.objects.update_or_create(
                product=product,
                name=name,
                defaults={"json_data":data,"is_active":True},
            )
            t.preview.save(
                f"canopy_luxury_aligned_v4_{i+1:03d}.svg",
                ContentFile(preview(pages[0]).encode("utf-8")),
                save=False,
            )
            t.save()
            self.stdout.write(f"{i+1:03d}/{count}: {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Created {count} aligned 7-page canopy templates for product {product.pk}."
        ))
