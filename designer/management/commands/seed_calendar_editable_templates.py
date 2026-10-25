"""Seed editable 2027 calendars using Zenvibe's Fabric primitive template schema."""
import calendar
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-calendar-editable-v1"
PALETTES = [
    ("#182A3A", "#FAF7F0", "#D6A95D"),
    ("#16463C", "#F5F7ED", "#B6CB8B"),
    ("#503049", "#FFF8F5", "#E0A8AA"),
    ("#123F60", "#F4FAFE", "#86C9D3"),
    ("#503B2B", "#FFF8E8", "#DDBD7E"),
]

def rect(key, x, y, w, h, color):
    return {"id":key,"type":"rect","left":round(x,2),"top":round(y,2),
            "width":round(w,2),"height":round(h,2),"fill":color,
            "selectable":True,"evented":True,"customerEditable":True}

def text(key, x, y, w, value, size, color, align="left"):
    return {"id":key,"type":"textbox","left":round(x,2),"top":round(y,2),
            "width":round(w,2),"text":str(value),"fontFamily":"Arial",
            "fontWeight":"700","fontSize":round(size,2),"fill":color,
            "textAlign":align,"selectable":True,"evented":True,"customerEditable":True}

def page(year, month, index, w, h):
    dark, light, accent = PALETTES[index % 5]
    base = (index // 5) % 20
    margin = w * .065
    obj = [rect("background",0,0,w,h,light)]
    # Twenty distinct arrangements; each has five palette editions.
    if base == 0: obj += [rect("header",0,0,w,h*.32,dark)]
    elif base == 1: obj += [rect("left-rail",0,0,w*.16,h,dark)]
    elif base == 2: obj += [rect("top-accent",0,0,w,h*.12,accent)]
    elif base == 3: obj += [rect("frame",margin,h*.04,w-2*margin,h*.26,dark),rect("inset",margin+w*.02,h*.06,w-2*margin-w*.04,h*.22,light)]
    elif base == 4: obj += [rect("split-left",0,0,w*.47,h*.29,dark),rect("split-right",w*.47,0,w*.53,h*.29,accent)]
    elif base == 5: obj += [rect("bottom-band",0,h*.88,w,h*.12,dark)]
    elif base == 6: obj += [rect("right-block",w*.68,0,w*.32,h*.31,dark)]
    elif base == 7: obj += [rect("center-band",0,h*.17,w,h*.13,dark)]
    elif base == 8: obj += [rect("thin-rail",margin,h*.03,w*.035,h*.28,accent)]
    elif base == 9: obj += [rect("title-panel",margin,h*.05,w-2*margin,h*.25,dark)]
    elif base == 10: obj += [rect("stripe-1",0,0,w,h*.07,dark),rect("stripe-2",0,h*.26,w,h*.05,accent)]
    elif base == 11: obj += [rect("left-panel",0,0,w*.28,h*.35,accent)]
    elif base == 12: obj += [rect("right-panel",w*.72,0,w*.28,h*.35,accent)]
    elif base == 13: obj += [rect("double-left",0,0,w*.09,h,dark),rect("double-right",w*.91,0,w*.09,h,accent)]
    elif base == 14: obj += [rect("title-rule",margin,h*.29,w-2*margin,h*.016,dark)]
    elif base == 15: obj += [rect("header-block",0,0,w,h*.35,accent)]
    elif base == 16: obj += [rect("top-left",0,0,w*.35,h*.31,dark)]
    elif base == 17: obj += [rect("top-right",w*.65,0,w*.35,h*.31,dark)]
    elif base == 18: obj += [rect("wide-inset",margin,h*.035,w-2*margin,h*.27,accent)]
    else: obj += [rect("full-heading",0,0,w,h*.30,dark),rect("edge",0,0,w*.045,h,accent)]
    heading_color = light if base in (0,7,9,19) else dark
    heading_x = margin + (w*.13 if base in (1,13) else 0)
    obj.extend([
        text("brand",heading_x,h*.055,w*.72,"YOUR BRAND",max(13,w*.025),heading_color),
        text("month",heading_x,h*.125,w*.78,calendar.month_name[month].upper(),max(28,w*.069),heading_color),
        text("year",heading_x,h*.23,w*.60,year,max(17,w*.033),heading_color),
    ])
    grid_top = h*.39
    grid_left = margin+w*.08 if base in (1,13) else margin
    grid_width = w-grid_left-margin
    cell_width = grid_width/7
    cell_height = h*.075
    for col, day in enumerate(("SUN","MON","TUE","WED","THU","FRI","SAT")):
        obj.append(text("weekday-%d"%col,grid_left+col*cell_width,grid_top,cell_width,day,max(11,w*.019),dark,"center"))
    for row, week in enumerate(calendar.Calendar(firstweekday=6).monthdayscalendar(year,month)):
        for col, day in enumerate(week):
            if day:
                obj.append(text("date-%d"%day,grid_left+col*cell_width,grid_top+(row+1)*cell_height,cell_width,day,max(13,w*.027),dark,"center"))
    obj += [rect("footer-line",margin,h*.91,w-2*margin,h*.004,accent),
            text("footer",margin,h*.935,w-2*margin,"YOUR BRAND • YOUR STORY",max(11,w*.018),dark,"center")]
    return {"name":calendar.month_name[month],"background":"#ffffff","objects":obj}

def payload(product,year,index):
    w,h=product.width,product.height
    return {"version":2,"generator":GENERATOR,"templateType":"editable-master",
            "designName":"Calendar %d - %03d"%(year,index+1),
            "document":{"width":w,"height":h,"unit":"in",
                        "physical":{"widthIn":float(product.print_width_in),"heightIn":float(product.print_height_in)},
                        "profile":"calendar"},
            "pages":[page(year,m,index,w,h) for m in range(1,13)],
            "editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1"}

class Command(BaseCommand):
    help = "Seed 100 editable 12-month calendar templates (20 layouts x 5 palette editions)."
    def add_arguments(self, parser):
        parser.add_argument("--product-id",type=int,required=True)
        parser.add_argument("--year",type=int,default=2027)
        parser.add_argument("--dry-run",action="store_true")
    def handle(self,*args,**options):
        year=options["year"]
        if not 1900 <= year <= 2100: raise CommandError("Invalid year")
        try: product=Product.objects.get(pk=options["product_id"])
        except Product.DoesNotExist: raise CommandError("Product not found")
        if not product.print_width_in or not product.print_height_in:
            raise CommandError("Configure product physical print dimensions in inches first")
        existing=DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR)
        if existing.exists(): raise CommandError("Calendar generator records already exist; refusing duplicate seeding")
        self.stdout.write("Product %s: 100 templates, 12 pages each; 20 layouts in 5 color editions"%product.id)
        if options["dry_run"]: return
        with transaction.atomic():
            for index in range(100):
                data=payload(product,year,index)
                DesignTemplate.objects.create(product=product,name=data["designName"],json_data=data,is_active=True)
        self.stdout.write(self.style.SUCCESS("Created 100 calendar templates"))
