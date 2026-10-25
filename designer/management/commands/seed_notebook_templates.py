from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-notebook-luxury-v3"
OLD_NAMES = ["Notebook 001", "Notebook 002", "Notebook 003"]
PALETTES = [
    ("#111827","#F9FAFB","#C9A227"),("#173F35","#FBF7EE","#B78B45"),
    ("#30243B","#FFFAF2","#C6A15B"),("#102A43","#F7FAFC","#D4AF37"),
    ("#3B2F2F","#FFFAF0","#A67C52"),
]

def rect(i,x,y,w,h,fill,stroke=None,sw=0):
    o={"id":i,"type":"rect","left":x,"top":y,"width":w,"height":h,"fill":fill,
       "selectable":True,"evented":True,"customerEditable":True}
    if stroke: o.update(stroke=stroke,strokeWidth=sw)
    return o

def text(i,x,y,w,value,size,fill,font="Poppins",weight="600",align="center"):
    return {"id":i,"type":"textbox","left":x,"top":y,"width":w,"text":value,
            "fontSize":size,"fontFamily":font,"fontWeight":weight,"fill":fill,
            "textAlign":align,"selectable":True,"evented":True,"customerEditable":True}

def line(i,x,y,w,c,h=4):
    return rect(i,x,y,w,h,c)

def objects(n):
    dark,light,gold=PALETTES[n%len(PALETTES)]
    b=n%20; v=n//20
    o=[rect("background",0,0,700,1000,light)]
    layouts=[
      [rect("spine",0,0,62,1000,dark),text("title",115,275,500,"YOUR STORY",70,dark,"Georgia","700","left"),text("sub",115,375,480,"NOTES • IDEAS • PLANS",22,gold,align="left")],
      [rect("header",0,0,700,285,dark),text("mark",205,75,290,"ZV",100,gold,"Georgia","700"),text("title",80,410,540,"EXECUTIVE NOTES",46,dark)],
      [rect("frame",60,70,580,860,light,dark,3),text("title",100,330,500,"THE JOURNAL",58,dark,"Georgia","700"),line("rule",215,440,270,gold,5),text("year",180,510,340,"2026",28,dark)],
      [rect("band",0,610,700,225,dark),text("title",70,665,560,"CREATE",76,light,weight="800"),text("sub",90,865,520,"EVERYDAY NOTEBOOK",20,gold)],
      [rect("left",0,0,235,1000,dark),text("title",290,260,340,"IDEAS",72,dark,weight="800",align="left"),text("sub",295,365,300,"start here.",30,gold,align="left")],
      [text("title",70,190,560,"LESS / MORE",64,dark,"Georgia","700"),line("rule",120,325,460,gold),text("sub",110,395,480,"FOCUS • PLAN • DO",23,dark)],
      [rect("top",0,0,700,95,gold),rect("bottom",0,905,700,95,dark),text("title",90,365,520,"PRIVATE NOTES",54,dark,weight="700")],
      [rect("card",80,175,540,650,dark),text("title",130,345,440,"FIELD NOTES",58,light,"Georgia","700"),text("sub",150,470,400,"VOL. 01",24,gold)],
      [text("initial",120,125,460,"N",320,gold,"Georgia","700"),text("title",100,610,500,"NOTEBOOK",43,dark,weight="700")],
      [rect("stripe",0,0,95,1000,dark),rect("gold",95,0,24,1000,gold),text("title",180,370,430,"WORK / LIFE",56,dark,weight="800",align="left")],
      [rect("frame",55,55,590,890,light,gold,5),text("title",100,310,500,"SIGNATURE",56,dark,"Georgia","700"),text("sub",120,425,460,"NOTE COLLECTION",22,dark)],
      [rect("block",0,0,700,480,dark),text("title",80,185,540,"THINK.",78,light,weight="800"),text("sub",90,585,520,"WRITE IT DOWN",29,gold)],
      [text("small",80,170,540,"PROJECT",34,gold,weight="700"),text("title",80,245,540,"BOOK",105,dark,weight="800"),line("rule",90,430,520,dark,5)],
      [rect("band",80,0,150,1000,gold),text("title",290,325,330,"DAILY",60,dark,weight="800",align="left"),text("sub",295,420,300,"NOTES",31,dark,align="left")],
      [rect("panel",60,90,580,820,dark),rect("inner",90,120,520,760,dark,gold,3),text("title",130,375,440,"ARCHIVE",58,light,"Georgia","700")],
      [text("quote",80,255,540,"MAKE SPACE\nFOR IDEAS",62,dark,"Georgia","700","left"),rect("dot",80,545,75,75,gold)],
      [rect("top",0,0,700,330,gold),text("title",80,125,540,"STUDIO",76,dark,weight="800"),text("sub",90,450,520,"CREATIVE NOTEBOOK",26,dark)],
      [rect("rail",300,0,100,1000,dark),text("a",55,250,210,"PLAN",50,dark,weight="800"),text("b",430,610,210,"DO",50,gold,weight="800")],
      [text("num",70,185,560,"01",190,gold,"Georgia","700"),text("sub",110,565,480,"PERSONAL JOURNAL",29,dark,weight="700")],
      [rect("header",70,100,560,175,dark),text("title",100,150,500,"YOUR BRAND",46,light,weight="700"),text("sub",100,365,500,"PREMIUM NOTEBOOK",27,gold)],
    ]
    o += layouts[b]
    if v==1: o += [line("lux",70,70,350,gold),text("edition",455,52,170,"SIGNATURE",14,dark,align="right")]
    elif v==2: o += [rect("c1",35,35,95,12,gold),rect("c2",570,953,95,12,dark)]
    elif v==3: o += [rect("outer",28,28,644,944,light,gold,3),rect("inner2",45,45,610,910,light,dark,1)]
    elif v==4: o += [rect("railL",38,100,4,800,gold),rect("railR",658,100,4,800,gold)]
    return o

def payload(p,n):
    page={"name":"Front Cover","background":"#ffffff","objects":objects(n)}
    return {"version":2,"generator":GENERATOR,"templateType":"editable-master",
      "designName":f"Notebook Luxury {n+1:03d}",
      "showProductMockup":True,
      "document":{"width":700,"height":1000,"unit":"in",
        "physical":{"widthIn":float(p.print_width_in),"heightIn":float(p.print_height_in)},
        "profile":"notebook-front-cover"},
      "pages":[page],"editable":True,"editorNative":True,
      "editorSchema":"fabric-primitives-v1",
      "source":{"type":"zenvibe-notebook-luxury-original"}}

class Command(BaseCommand):
    help="Seed 100 editable luxury notebook templates for configured Custom Notebook products."
    def add_arguments(self,p):
        p.add_argument("--count",type=int,default=100)
        p.add_argument("--replace",action="store_true")
        p.add_argument("--product-id",type=int)
    @transaction.atomic
    def handle(self,*a,**o):
        qs=Product.objects.filter(category__slug="custom-notebooks",is_active=True).order_by("id")
        if o["product_id"]: qs=qs.filter(id=o["product_id"])
        if not qs.exists(): raise CommandError("No active Custom Notebook products found.")
        made=0
        for product in qs:
            if not all([product.workspace_width_in,product.workspace_height_in,product.print_width_in,product.print_height_in]):
                self.stdout.write(self.style.WARNING(f"{product.id} — {product.name}: skipped; physical geometry is not configured"))
                continue
            if o["replace"]:
                DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR).delete()
                DesignTemplate.objects.filter(product=product,name__in=OLD_NAMES).delete()
            current=DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR).count()
            for n in range(current,o["count"]):
                data=payload(product,n)
                DesignTemplate.objects.create(product=product,name=data["designName"],json_data=data,is_active=True)
                made+=1
            self.stdout.write(self.style.SUCCESS(f"{product.id} — {product.name}: {o['count']} luxury editable templates ready"))
        self.stdout.write(self.style.SUCCESS(f"Done. Created {made} templates."))
