"""Vibrant editorial calendars: editable graphic artwork and 12 readable months."""
import calendar
import math
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

GENERATOR="zenvibe-calendar-editable-v3"
OLD=("zenvibe-calendar-editable-v1","zenvibe-calendar-editable-v2")
PALETTES=[
("#30106B","#FFF4C9","#FF5E5B","#00D7B4"),
("#102A78","#FFF5EA","#FF3D8D","#FFC93C"),
("#173F3B","#FFF6DF","#FF7B39","#70E4C1"),
("#42136F","#FFF2FB","#F74BA3","#7FE5FA"),
("#142C56","#FFF9DA","#FFB000","#FF5C75"),
("#4A144B","#FFF4E9","#F85B44","#7DDDD4"),
("#123B7A","#F5F8FF","#FFCF33","#FF5B9C"),
("#1D4940","#FFF7EA","#FC6176","#A3D943"),
("#452061","#FFF9F0","#FF793F","#42D3E5"),
("#172B64","#FFF3EC","#F3496C","#72DBB5")]
THEMES=[
("THE ART OF LIVING","A YEAR OF BEAUTIFUL MOMENTS"),
("THE QUIET COLLECTION","TIMELESS DAYS, BEAUTIFULLY KEPT"),
("GOLDEN HOUR","MAKE EVERY MOMENT COUNT"),
("BOTANICAL NOTES","GROW THROUGH EVERY SEASON"),
("ATELIER","CURATED FOR YOUR EVERYDAY"),
("THE TRAVEL EDITION","COLLECT MOMENTS, NOT THINGS"),
("HERITAGE","A STORY WORTH REMEMBERING"),
("THE MODERN HOME","LITTLE MOMENTS, BIG MEMORIES"),
("STUDIO DAYS","CREATE YOUR OWN STORY"),
("A YEAR IN BLOOM","TWELVE CHAPTERS TO CHERISH")]
def rect(i,x,y,w,h,fill,stroke=None,sw=1):
 d={"id":i,"type":"rect","left":round(x,2),"top":round(y,2),"width":round(w,2),"height":round(h,2),"fill":fill,"selectable":True,"evented":True,"customerEditable":True}
 if stroke:d.update(stroke=stroke,strokeWidth=sw)
 return d
def txt(i,x,y,w,s,size,color,align="left",weight="500",font="Georgia"):
 return {"id":i,"type":"textbox","left":round(x,2),"top":round(y,2),"width":round(w,2),"text":str(s),"fontSize":round(size,2),"fontFamily":font,"fontWeight":weight,"fill":color,"textAlign":align,"selectable":True,"evented":True,"customerEditable":True}
def circle(i,x,y,r,fill,stroke=None):
 return {"id":i,"type":"circle","left":round(x,2),"top":round(y,2),"radius":round(r,2),"fill":fill,"stroke":stroke or fill,"strokeWidth":1,"selectable":True,"evented":True,"customerEditable":True}
def artwork(i,x,y,w,h,variant,dark,accent,soft):
 """Native editable graphic illustrations instead of uneditable empty photo placeholders."""
 o=[rect("art-back",x,y,w,h,dark)]
 unit=min(w,h)
 if variant==0: # Art deco fan
  for k in range(9):
   o.append(rect("deco-%d"%k,x+w*(.1+k*.09),y+h*.16,w*.016,h*.7,accent if k%2 else soft))
 elif variant==1: # Sunrise over layered horizon
  o.append(circle("sun",x+w*.58,y+h*.14,unit*.19,accent))
  for k in range(4):o.append(rect("land-%d"%k,x,y+h*(.58+k*.1),w,h*.105,(soft,accent,soft,accent)[k]))
 elif variant==2: # Modern abstract composition
  o += [circle("orb-1",x+w*.1,y+h*.09,unit*.27,accent),circle("orb-2",x+w*.53,y+h*.32,unit*.23,soft),rect("bar",x+w*.12,y+h*.69,w*.76,h*.065,accent)]
 elif variant==3: # Botanical stems and leaves
  for k in range(5):
   xx=x+w*(.16+k*.17)
   o.append(rect("stem-%d"%k,xx,y+h*.2,w*.007,h*.65,dark))
   for q in range(3):o.append(circle("leaf-%d-%d"%(k,q),xx-w*.055,y+h*(.25+q*.17),unit*.045,accent if q%2 else soft))
 elif variant==4: # Architectural arches
  for k in range(3):
   xx=x+w*(.1+k*.29)
   o += [rect("pillar-%d"%k,xx,y+h*.28,w*.19,h*.52,soft if k==1 else accent),
         circle("arch-%d"%k,xx,y+h*.16,w*.095,dark if k==1 else accent)]
 elif variant==5: # Night sky
  o.append(circle("moon",x+w*.55,y+h*.1,unit*.19,accent))
  for k in range(18):
   xx=x+w*(.07+((k*37)%83)/100)
   yy=y+h*(.07+((k*23)%69)/100)
   o.append(circle("star-%d"%k,xx,yy,max(1,unit*.004),soft))
 elif variant==6: # Geometric textile
  for k in range(7):
   o.append(rect("stripe-%d"%k,x+w*(k/7),y,w*.045,h,accent if k%2 else soft))
  o.append(circle("medallion",x+w*.34,y+h*.27,unit*.17,accent))
 elif variant==7: # Gallery frame
  o += [rect("outer-frame",x+w*.1,y+h*.1,w*.8,h*.8,soft,accent,3),
        rect("inner-frame",x+w*.16,y+h*.17,w*.68,h*.66,accent),
        circle("gallery-disc",x+w*.34,y+h*.29,unit*.18,soft)]
 elif variant==8: # Minimal editorial bands
  o += [rect("large-band",x,y+h*.12,w,h*.26,accent),rect("small-band",x+w*.12,y+h*.48,w*.76,h*.11,accent),
        rect("fine-band",x+w*.22,y+h*.68,w*.56,h*.018,soft)]
 else: # Abstract tiled mosaic
  for r in range(3):
   for c in range(4):
    o.append(rect("tile-%d-%d"%(r,c),x+w*(.06+c*.225),y+h*(.08+r*.29),w*.19,h*.24,
                  (accent,soft,"#FFFFFF")[(r+c)%3]))
 return o
def page(year,month,index,w,h):
 dark,bg,accent,soft=PALETTES[index%10]
 theme,tag=THEMES[index//10]
 # Use a print-safe magazine layout: decorative artwork above calendar, no overlay.
 # Ten themes and ten different artwork systems; each combination is editable.
 m=min(w,h)*.045
 vertical=h>=w*.95
 if vertical:
  art=(m,m,w-2*m,h*.44)
  panel=(m,h*.52,w-2*m,h*.43)
 else:
  art=(m,m,w*.48-m,h-2*m)
  panel=(w*.53,m,w*.43,h-2*m)
 ax,ay,aw,ah=art;px,py,pw,ph=panel
 o=[rect("paper",0,0,w,h,bg)]
 o+=artwork(index,ax,ay,aw,ah,index%10,dark,accent,soft)
 # A strong editorial masthead over artwork; bounded separately from date grid.
 o.append(rect("masthead",ax+aw*.06,ay+ah*.68,aw*.88,ah*.24,bg))
 o.append(txt("theme",ax+aw*.1,ay+ah*.715,aw*.8,theme,max(10,min(aw*.04,ah*.06)),dark,"center","700"))
 o.append(txt("tagline",ax+aw*.08,ay+ah*.82,aw*.84,tag,max(8,min(aw*.018,ah*.032)),dark,"center","400","Arial"))
 o.append(rect("calendar-background",px,py,pw,ph,bg))
 o.append(rect("calendar-accent",px,py,pw,ph*.035,accent))
 o.append(rect("top-rule",px,py+ph*.04,pw,max(1,ph*.006),dark))
 o.append(txt("month",px,py+ph*.055,pw,calendar.month_name[month].upper(),
              max(13,min(pw*.065,ph*.10)),dark,"center","700"))
 o.append(txt("year",px,py+ph*.18,pw,str(year),max(10,min(pw*.03,ph*.05)),accent,"center","600","Arial"))
 o.append(rect("divider",px+pw*.07,py+ph*.29,pw*.86,max(1,ph*.009),accent))
 gx=px+pw*.075;gw=pw*.85;gy=py+ph*.36;row=ph*.075;cw=gw/7
 fs=max(8,min(cw*.4,row*.52))
 for col,name in enumerate(("S","M","T","W","T","F","S")):
  o.append(txt("weekday-%d"%col,gx+col*cw,gy,cw,name,fs*.8,dark,"center","700","Arial"))
 for ri,week in enumerate(calendar.Calendar(firstweekday=6).monthdayscalendar(year,month)):
  for col,day in enumerate(week):
   if day:
    o.append(txt("date-%d"%day,gx+col*cw,gy+(ri+1)*row,cw,day,fs,dark,"center","400","Arial"))
 o.append(rect("bottom-rule",px+pw*.07,py+ph*.88,pw*.86,max(1,ph*.003),accent))
 o.append(txt("brand",px+pw*.05,py+ph*.92,pw*.9,"YOUR BRAND",max(8,min(pw*.022,ph*.035)),dark,"center","600","Arial"))
 return {"name":calendar.month_name[month],"background":bg,"objects":o}
def payload(product,year,i):
 w,h=product.width,product.height
 return {"version":2,"generator":GENERATOR,"templateType":"editable-master",
         "designName":"Luxury %s %d - %03d"%(THEMES[i//10][0].title(),year,i+1),
         "document":{"width":w,"height":h,"unit":"in",
                     "physical":{"widthIn":float(product.print_width_in),"heightIn":float(product.print_height_in)},
                     "profile":"calendar"},
         "pages":[page(year,m,i,w,h) for m in range(1,13)],
         "editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1"}
class Command(BaseCommand):
 help="Generate 100 illustrated, editable calendar layouts with 12 months."
 def add_arguments(self,p):
  p.add_argument("--product-id",type=int,required=True)
  p.add_argument("--year",type=int,default=2027)
  p.add_argument("--dry-run",action="store_true")
  p.add_argument("--replace",action="store_true")
 def handle(self,*a,**o):
  if not 1900<=o["year"]<=2100:raise CommandError("Invalid year")
  try:p=Product.objects.get(pk=o["product_id"])
  except Product.DoesNotExist:raise CommandError("Product not found")
  if not p.print_width_in or not p.print_height_in:raise CommandError("Configure print dimensions first")
  qs=DesignTemplate.objects.filter(product=p,json_data__generator__in=[GENERATOR,*OLD])
  if qs.exists() and not o["replace"]:raise CommandError("Existing generated calendars; use --replace")
  self.stdout.write("Preparing 100 vibrant illustrated calendars, 12 pages each")
  if o["dry_run"]:return
  with transaction.atomic():
   if o["replace"]:qs.delete()
   for i in range(100):
    data=payload(p,o["year"],i)
    DesignTemplate.objects.create(product=p,name=data["designName"],json_data=data,is_active=True)
  self.stdout.write(self.style.SUCCESS("Created 100 editable illustrated calendars"))
