"""Luxury editable 12-month calendar layouts. Photo areas are editable placeholders."""
import calendar
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

GENERATOR = "zenvibe-calendar-editable-v1"
PALETTES = [
 ("#1C2934","#FAF8F3","#B99560"),("#153C35","#FBF8EF","#B7A27A"),
 ("#34283C","#FFF9F3","#D6B6A2"),("#253F59","#F7F9FC","#B6A77E"),
 ("#47362E","#FFF9EE","#D6AE78"),("#2D3332","#F4F0E9","#C4B7A0"),
 ("#293850","#F5F3ED","#C2A269"),("#4C3541","#FFF7F6","#C79C9D"),
 ("#263C37","#FAF7F0","#C7B88B"),("#313036","#F7F5F1","#D6C1A0")]
def box(i,x,y,w,h,fill,stroke=None):
    d={"id":i,"type":"rect","left":round(x,2),"top":round(y,2),"width":round(w,2),
       "height":round(h,2),"fill":fill,"selectable":True,"evented":True,"customerEditable":True}
    if stroke: d.update(stroke=stroke,strokeWidth=1.5)
    return d
def label(i,x,y,w,h,value,size,color,align="left",weight="600"):
    return {"id":i,"type":"textbox","left":round(x,2),"top":round(y,2),
            "width":round(w,2),"height":round(h,2),"text":str(value),
            "fontFamily":"Arial","fontWeight":weight,"fontSize":round(size,2),
            "fill":color,"textAlign":align,"selectable":True,"evented":True,"customerEditable":True}
def photo_tiles(x,y,w,h,variant,dark,light,accent):
    """Ten distinct collage structures; photo regions remain user-replaceable."""
    pad=min(w,h)*.018
    if variant==0: tiles=[(0,0,1,1)]
    elif variant==1: tiles=[(0,0,.49,1),(.51,0,.49,1)]
    elif variant==2: tiles=[(0,0,1,.49),(0,.51,1,.49)]
    elif variant==3: tiles=[(0,0,.65,1),(.67,0,.33,.49),(.67,.51,.33,.49)]
    elif variant==4: tiles=[(0,0,.33,.49),(.35,0,.65,1),(0,.51,.33,.49)]
    elif variant==5: tiles=[(0,0,.49,.49),(.51,0,.49,.49),(0,.51,.49,.49),(.51,.51,.49,.49)]
    elif variant==6: tiles=[(0,0,1,.63),(0,.65,.32,.35),(.34,.65,.32,.35),(.68,.65,.32,.35)]
    elif variant==7: tiles=[(0,0,.32,1),(.34,0,.32,1),(.68,0,.32,1)]
    elif variant==8: tiles=[(0,0,.49,.65),(.51,0,.49,.32),(.51,.34,.49,.66),(0,.67,.49,.33)]
    else: tiles=[(0,0,.32,.49),(.34,0,.32,.49),(.68,0,.32,.49),(0,.51,.49,.49),(.51,.51,.49,.49)]
    out=[]
    for n,(a,b,c,d) in enumerate(tiles):
        tx=x+a*w+pad; ty=y+b*h+pad; tw=c*w-2*pad; th=d*h-2*pad
        out.append(box("photo-%d"%n,tx,ty,tw,th,("#E4DDD2","#D7DED8","#DFD7D8")[n%3],accent))
        out.append(label("photo-hint-%d"%n,tx+tw*.06,ty+th*.39,tw*.88,th*.16,
                         "ADD PHOTO",max(10,min(tw*.032,th*.12)),dark,"center","500"))
    return out
def page(year,month,index,w,h):
    dark,light,accent=PALETTES[index%10]
    composition=index//10
    margin=min(w,h)*.035
    # Photo and calendar rectangles never intersect. Different composition types
    # change photo position and calendar proportions, not merely color.
    if composition==0: photo=(0,0,w,h*.53); cal=(0,h*.53,w,h*.47)
    elif composition==1: photo=(0,0,w,h*.63); cal=(0,h*.63,w,h*.37)
    elif composition==2: photo=(0,0,w,h*.44); cal=(0,h*.44,w,h*.56)
    elif composition==3: photo=(0,h*.47,w,h*.53); cal=(0,0,w,h*.47)
    elif composition==4: photo=(0,h*.60,w,h*.40); cal=(0,0,w,h*.60)
    elif composition==5: photo=(0,h*.39,w,h*.61); cal=(0,0,w,h*.39)
    elif composition==6: photo=(0,0,w*.56,h); cal=(w*.56,0,w*.44,h)
    elif composition==7: photo=(w*.44,0,w*.56,h); cal=(0,0,w*.44,h)
    elif composition==8: photo=(0,0,w*.44,h); cal=(w*.44,0,w*.56,h)
    else: photo=(w*.56,0,w*.44,h); cal=(0,0,w*.56,h)
    px,py,pw,ph=photo; cx,cy,cw,ch=cal
    o=[box("background",0,0,w,h,light)]
    o+=photo_tiles(px,py,pw,ph,index%10,dark,light,accent)
    o.append(box("calendar-panel",cx,cy,cw,ch,light))
    m=min(cw,ch)*.07
    inner_x=cx+m; inner_w=cw-2*m
    title_h=ch*.15
    o.append(label("month",inner_x,cy+ch*.055,inner_w,title_h,
                   calendar.month_name[month].upper(),max(14,min(cw*.063,ch*.11)),dark,"center","700"))
    o.append(label("year",inner_x,cy+ch*.21,inner_w,ch*.08,str(year),
                   max(11,min(cw*.033,ch*.063)),accent,"center"))
    o.append(box("divider",inner_x,cy+ch*.31,inner_w,max(1,ch*.003),accent))
    # Seven columns and six date rows reserve fixed slots even in six-week months.
    grid_top=cy+ch*.37; grid_h=ch*.51; colw=inner_w/7; rowh=grid_h/7
    font=max(7,min(colw*.32,rowh*.43))
    for col,day in enumerate(("S","M","T","W","T","F","S")):
        o.append(label("weekday-%d"%col,inner_x+col*colw,grid_top,colw,rowh*.8,
                       day,font*.83,dark,"center"))
    for row,week in enumerate(calendar.Calendar(firstweekday=6).monthdayscalendar(year,month)):
        for col,day in enumerate(week):
            if day:
                o.append(label("day-%d"%day,inner_x+col*colw,grid_top+(row+1)*rowh,
                               colw,rowh*.8,day,font,dark,"center"))
    o.append(label("brand",inner_x,cy+ch*.92,inner_w,ch*.045,"YOUR BRAND",
                   max(8,min(cw*.025,ch*.035)),dark,"center"))
    return {"name":calendar.month_name[month],"background":light,"objects":o}
def payload(product,year,index):
    w,h=product.width,product.height
    return {"version":2,"generator":GENERATOR,"templateType":"editable-master",
      "designName":"Luxury Calendar %d - %03d"%(year,index+1),
      "document":{"width":w,"height":h,"unit":"in",
                  "physical":{"widthIn":float(product.print_width_in),
                              "heightIn":float(product.print_height_in)},
                  "profile":"calendar"},
      "pages":[page(year,m,index,w,h) for m in range(1,13)],
      "editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1"}
class Command(BaseCommand):
    help="Seed 100 editable luxury 12-month calendar templates, optionally replacing old generated versions."
    def add_arguments(self,parser):
        parser.add_argument("--product-id",type=int,required=True)
        parser.add_argument("--year",type=int,default=2027)
        parser.add_argument("--dry-run",action="store_true")
        parser.add_argument("--replace",action="store_true")
    def handle(self,*args,**options):
        year=options["year"]
        if not 1900<=year<=2100: raise CommandError("Invalid year")
        try: product=Product.objects.get(pk=options["product_id"])
        except Product.DoesNotExist: raise CommandError("Product not found")
        if not product.print_width_in or not product.print_height_in:
            raise CommandError("Configure physical print dimensions first")
        existing=DesignTemplate.objects.filter(product=product,json_data__generator=GENERATOR)
        count=existing.count()
        if count and not options["replace"]:
            raise CommandError("%d generated templates exist; use --replace to replace them"%count)
        self.stdout.write("Product %s: 100 luxury calendar layouts, 12 editable pages each; replacing %d"%(product.id,count if options["replace"] else 0))
        if options["dry_run"]: return
        with transaction.atomic():
            if options["replace"]: existing.delete()
            for i in range(100):
                data=payload(product,year,i)
                DesignTemplate.objects.create(product=product,name=data["designName"],
                                              json_data=data,is_active=True)
        self.stdout.write(self.style.SUCCESS("Created 100 luxury calendar templates"))
