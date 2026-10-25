from __future__ import annotations

import copy
import html
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product, ProductColorVariant

GENERATOR = "zenvibe-umbrella-luxury-editable-v1"
W = H = 1000

COLORS = [
    ("Black", "black", "#111111"),
    ("Orange", "orange", "#F05A18"),
    ("Yellow", "yellow", "#F4E400"),
    ("Blue", "blue", "#1769D2"),
    ("Green", "green", "#48D600"),
    ("Purple", "purple", "#7114C7"),
    ("Red", "red", "#E52521"),
]
PALETTES = [
    ("#111827","#F9FAFB","#C8A45D"),("#172554","#FFFFFF","#D7B56D"),
    ("#1F2937","#F8F5EE","#B68D40"),("#052E2B","#F5F0E6","#C6A15B"),
    ("#3B1020","#FFF7ED","#D5A85A"),("#18181B","#FAFAFA","#A78BFA"),
    ("#0F172A","#E2E8F0","#38BDF8"),("#292524","#FAFAF9","#D6D3D1"),
    ("#312E81","#EEF2FF","#F59E0B"),("#3F3F46","#FFFFFF","#E4E4E7"),
]

def rect(i,x,y,w,h,fill,opacity=1):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"rect","left":x,"top":y,
            "width":w,"height":h,"fill":fill,"opacity":opacity,"customerEditable":True}
def circle(i,cx,cy,r,fill):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"circle","left":cx-r,"top":cy-r,
            "radius":r,"fill":fill,"customerEditable":True}
def text(i,x,y,w,value,size,fill,weight=500,align="center"):
    return {"id":i,"name":i.replace("_"," ").title(),"type":"textbox","left":x,"top":y,"width":w,
            "text":value,"fontSize":size,"fontFamily":"Poppins","fontWeight":weight,"fill":fill,
            "textAlign":align,"lineHeight":1.05,"customerEditable":True}
def line(i,x,y,w,h,fill):
    return rect(i,x,y,w,h,fill)

def objects_for(idx):
    dark, light, accent = PALETTES[idx % len(PALETTES)]
    family = idx % 20
    # 20 composition families x 5 geometry/typography variants = 100 materially distinct masters.
    v = idx // 20
    inset = 36 + v*11
    band = 46 + v*9
    objs=[]
    if family == 0:
        objs=[circle("monogram_ring",500,390,150,accent),circle("monogram_core",500,390,128,dark),
              text("monogram",365,315,270,"ZV",104,light,700),text("brand",190,575,620,"YOUR BRAND",55,dark,700),
              text("tagline",230,650,540,"PREMIUM • DISTINCTIVE",21,accent,600)]
    elif family == 1:
        objs=[rect("left_panel",inset,170,210,650,dark),line("gold_rule",285,260,8,460,accent),
              text("brand",335,315,520,"YOUR BRAND",62,dark,700,"left"),text("tagline",335,405,500,"ELEVATED EVERYDAY",25,accent,600,"left"),
              text("website",335,650,500,"yourbrand.com",20,dark,500,"left")]
    elif family == 2:
        objs=[rect("top_band",130,210,740,band,dark),rect("bottom_band",130,720,740,band,accent),
              text("brand",180,355,640,"YOUR BRAND",72,dark,800),text("tagline",210,465,580,"DESIGNED WITH PURPOSE",24,accent,600)]
    elif family == 3:
        objs=[circle("seal",500,420,190,dark),circle("seal_inner",500,420,165,light),
              text("initial",390,330,220,"A",120,dark,700),text("brand",220,635,560,"ATELIER",44,dark,700),
              text("since",300,690,400,"EST. 2026",18,accent,600)]
    elif family == 4:
        objs=[rect("corner_one",120,190,260,45,accent),rect("corner_two",620,765,260,45,dark),
              text("brand",165,365,670,"YOUR BRAND",76,dark,700),text("tagline",190,470,620,"QUIET LUXURY",29,accent,500)]
    elif family == 5:
        objs=[rect("center_card",215,245,570,510,light),rect("card_edge",215,245,16,510,accent),
              text("brand",285,355,430,"YOUR BRAND",58,dark,800),text("tagline",285,455,430,"SIGNATURE COLLECTION",22,accent,600),
              text("website",285,620,430,"YOURBRAND.COM",18,dark,500)]
    elif family == 6:
        objs=[line("diag_a",180,260,640,18,accent),line("diag_b",260,720,480,18,dark),
              text("brand",180,385,640,"YOUR BRAND",68,dark,800),text("tagline",220,495,560,"MAKE AN IMPRESSION",24,accent,600)]
    elif family == 7:
        objs=[circle("dot_a",260,330,55,accent),circle("dot_b",740,670,80,dark),circle("dot_c",700,285,25,accent),
              text("brand",230,435,540,"YOUR BRAND",62,dark,700),text("tagline",270,535,460,"MODERN ESSENTIALS",22,accent,600)]
    elif family == 8:
        objs=[rect("frame_top",155,205,690,10,dark),rect("frame_bottom",155,785,690,10,dark),
              rect("frame_left",155,205,10,590,dark),rect("frame_right",835,205,10,590,dark),
              text("brand",220,385,560,"YOUR BRAND",70,dark,700),text("tagline",250,500,500,"TIMELESS QUALITY",23,accent,600)]
    elif family == 9:
        objs=[rect("split_left",135,235,350,530,dark),rect("split_right",515,235,350,530,light),
              text("initial",190,370,240,"YB",95,light,700),text("brand",545,385,270,"YOUR\nBRAND",54,dark,800),
              text("tagline",545,545,270,"PREMIUM",20,accent,600)]
    elif family == 10:
        objs=[circle("halo",500,410,210,accent),circle("halo_cut",500,410,178,light),
              text("brand",230,370,540,"YOUR BRAND",60,dark,800),text("tagline",270,475,460,"THE SIGNATURE EDIT",21,dark,500)]
    elif family == 11:
        objs=[rect("vertical_band",430,160,140,680,dark),text("initial",440,330,120,"Z",105,light,800),
              text("brand",125,640,270,"YOUR BRAND",35,dark,700,"right"),text("tagline",605,640,270,"LUXURY\nREDEFINED",26,accent,600,"left")]
    elif family == 12:
        objs=[rect("label",190,330,620,330,dark),text("brand",240,400,520,"YOUR BRAND",66,light,700),
              line("label_rule",340,505,320,5,accent),text("tagline",260,545,480,"EXECUTIVE COLLECTION",19,light,500)]
    elif family == 13:
        objs=[circle("orb_a",330,390,125,dark),circle("orb_b",650,390,125,accent),
              text("brand",205,590,590,"YOUR BRAND",58,dark,700),text("tagline",280,675,440,"BOLD • REFINED",21,accent,600)]
    elif family == 14:
        objs=[rect("stripe_a",150,280,700,55,dark),rect("stripe_b",150,350,520,24,accent),
              text("brand",150,450,700,"YOUR BRAND",72,dark,800,"left"),text("tagline",150,555,700,"BUILT TO BE REMEMBERED",23,accent,600,"left")]
    elif family == 15:
        objs=[rect("badge",310,270,380,380,dark),circle("badge_dot",500,355,34,accent),
              text("initial",365,390,270,"YB",86,light,700),text("brand",240,700,520,"YOUR BRAND",40,dark,700)]
    elif family == 16:
        objs=[line("rule_a",190,320,620,6,dark),line("rule_b",300,690,400,6,accent),
              text("brand",190,390,620,"YOUR BRAND",76,dark,700),text("tagline",230,505,540,"SIMPLE. DISTINCT. YOURS.",22,accent,600)]
    elif family == 17:
        objs=[rect("offset_back",255,260,520,430,accent),rect("offset_front",225,230,520,430,light),
              text("brand",285,355,400,"YOUR BRAND",57,dark,800),text("tagline",285,460,400,"PREMIUM BRANDING",22,accent,600),
              text("website",285,570,400,"yourbrand.com",18,dark)]
    elif family == 18:
        objs=[circle("crest_outer",500,405,175,dark),circle("crest_inner",500,405,145,light),
              text("crest_initial",405,325,190,"V",112,dark,700),line("crest_rule",350,600,300,5,accent),
              text("brand",250,645,500,"YOUR BRAND",42,dark,700)]
    else:
        objs=[rect("lower_block",125,560,750,210,dark),text("brand",175,600,650,"YOUR BRAND",62,light,800),
              text("tagline",175,690,650,"LUXURY PROMOTIONAL GOODS",20,accent,600),circle("mark",500,360,90,accent),
              text("mark_text",430,315,140,"YB",48,dark,800)]
    # Variant changes spacing/geometry, not merely colour.
    if v:
        for o in objs:
            if o.get("type") in ("rect","circle","textbox"):
                o["left"] = float(o.get("left",0)) + (v-2)*6
    return objs

def build(idx, width_in, height_in, surface):
    objects=objects_for(idx)
    page={"name":surface,"background":"#FFFFFF","physical":{"widthIn":width_in,"heightIn":height_in},
          "objects":copy.deepcopy(objects)}
    return {"version":1,"templateType":"editable-master","reconstructed":True,"generator":GENERATOR,
            "designName":f"Umbrella Luxury {idx+1:03d}","document":{"width":W,"height":H,"profile":"umbrella",
            "physical":{"widthIn":width_in,"heightIn":height_in},"unit":"in"},"pageCount":1,
            "pages":[page],"adminPages":[copy.deepcopy(page)],"editable":True,"editorNative":True,
            "editorSchema":"fabric-primitives-v1","surface":surface,
            "source":{"type":"original-editor-native-vector-composition",
            "note":"Editable umbrella artwork only. Product colour/mockup remains a separate admin-driven product asset."}}

def svg_preview(objs):
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">','<rect width="1000" height="1000" fill="#fff"/>']
    for o in objs:
        fill=html.escape(str(o.get("fill","#111")))
        if o["type"]=="rect":
            out.append(f'<rect x="{o["left"]}" y="{o["top"]}" width="{o["width"]}" height="{o["height"]}" fill="{fill}" opacity="{o.get("opacity",1)}"/>')
        elif o["type"]=="circle":
            r=o["radius"]; out.append(f'<circle cx="{o["left"]+r}" cy="{o["top"]+r}" r="{r}" fill="{fill}"/>')
        elif o["type"]=="textbox":
            x=o["left"]+(o.get("width",0)/2 if o.get("textAlign")=="center" else 0)
            anchor="middle" if o.get("textAlign")=="center" else "start"
            out.append(f'<text x="{x}" y="{o["top"]+o.get("fontSize",20)}" text-anchor="{anchor}" font-family="Arial" font-size="{o.get("fontSize",20)}" font-weight="{o.get("fontWeight",500)}" fill="{fill}">{html.escape(str(o.get("text","")))}</text>')
    out.append("</svg>"); return "".join(out)

class Command(BaseCommand):
    help="Seed 100 luxury, editor-native umbrella templates and admin-configurable colour rows."

    def add_arguments(self, parser):
        parser.add_argument("--product-id",type=int,default=205)
        parser.add_argument("--count",type=int,default=100)
        parser.add_argument("--replace-generated",action="store_true")
        parser.add_argument("--seed-colors",action="store_true")
        parser.add_argument("--dry-run",action="store_true")

    def handle(self,*args,**opts):
        try: product=Product.objects.get(pk=opts["product_id"])
        except Product.DoesNotExist: raise CommandError("Umbrella product not found.")
        surface=product.print_surfaces.filter(is_active=True).order_by("sort_order","id").first()
        width_in=float((surface.print_width_in if surface else product.print_width_in) or 0)
        height_in=float((surface.print_height_in if surface else product.print_height_in) or 0)
        if width_in<=0 or height_in<=0:
            raise CommandError("Configure umbrella print width/height in Admin first. No physical dimensions are guessed.")
        count=max(1,min(100,opts["count"]))
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run OK: {product.id} {product.name}; {count} templates; {width_in:g} x {height_in:g} in."))
            return
        with transaction.atomic():
            if opts["seed_colors"]:
                for order,(name,key,hx) in enumerate(COLORS):
                    ProductColorVariant.objects.update_or_create(product=product,color_key=key,
                        defaults={"name":name,"hex_value":hx,"sort_order":order,"is_active":True})
            if opts["replace_generated"]:
                DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR).delete()
            for idx in range(count):
                data=build(idx,width_in,height_in,surface.label if surface else "Umbrella Print Area")
                name=f"Umbrella Luxury {idx+1:03d}"
                obj,_=DesignTemplate.objects.update_or_create(product=product,name=name,
                    defaults={"json_data":data,"is_active":True})
                obj.preview.save(f"umbrella_luxury_{product.id}_{idx+1:03d}.svg",
                    ContentFile(svg_preview(data["pages"][0]["objects"]).encode("utf-8")),save=False)
                obj.save()
        self.stdout.write(self.style.SUCCESS(
            f"{count} luxury editable umbrella templates ready for {product.id} {product.name}. "
            "Colours are ProductColorVariant rows editable in Admin; matching ProductImage labels provide colour mockups."
        ))
