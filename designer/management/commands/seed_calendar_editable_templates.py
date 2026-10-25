"""Photo-led calendars with correctly sized editable photos and monthly planners."""
import calendar
import math
import hashlib
from io import BytesIO
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageOps
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import Product, DesignTemplate

GENERATOR="zenvibe-calendar-editable-v13"
OLD=("zenvibe-calendar-editable-v1","zenvibe-calendar-editable-v2","zenvibe-calendar-editable-v3","zenvibe-calendar-editable-v4","zenvibe-calendar-editable-v5","zenvibe-calendar-editable-v6","zenvibe-calendar-editable-v7","zenvibe-calendar-editable-v8","zenvibe-calendar-editable-v9","zenvibe-calendar-editable-v10","zenvibe-calendar-editable-v11","zenvibe-calendar-editable-v12")
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
# Curated photographic references; replace with locally hosted licensed images before production.
# The images are editable Fabric objects rather than painted into a flat background.
PHOTO_URLS=[
 "https://images.unsplash.com/photo-1500534623283-312aade485b7?w=1000&q=85",
 "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1000&q=85",
 "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=1000&q=85",
 "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1000&q=85",
 "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1000&q=85",
 "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1000&q=85",
 "https://images.unsplash.com/photo-1480796927426-f609979314bd?w=1000&q=85",
 "https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=1000&q=85",
 "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=1000&q=85",
 "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=1000&q=85",
 "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1000&q=85",
 "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1000&q=85",
]
def _fitted_photo(src,w,h):
 """Pre-crop to the exact Fabric object's dimensions.
 The editor otherwise loads the original intrinsic size and can cover the calendar.
 """
 if w<=0 or h<=0:raise CommandError("Invalid photo slot dimensions")
 path=src.split("/media/",1)[1] if "/media/" in src else src.lstrip("/")
 key=hashlib.sha256(("%s|%.3f|%.3f"%(path,w,h)).encode()).hexdigest()[:20]
 target="calendar_assets/fitted/%s.jpg"%key
 if not default_storage.exists(target):
  with default_storage.open(path,"rb") as f:
   original=Image.open(f).convert("RGB")
   fitted=ImageOps.fit(original,(max(1,round(w)),max(1,round(h))),method=Image.Resampling.LANCZOS)
  out=BytesIO();fitted.save(out,format="JPEG",quality=90)
  default_storage.save(target,ContentFile(out.getvalue()))
 return default_storage.url(target)

def photo_object(name,x,y,w,h,src):
 fitted=_fitted_photo(src,w,h)
 return {"id":name,"type":"image","left":round(x,2),"top":round(y,2),
         "width":round(w),"height":round(h),"src":fitted,"baseSrc":fitted,
         "scaleX":1,"scaleY":1,"originX":"left","originY":"top",
         "selectable":True,"evented":True,"customerEditable":True,
         "manualReplacement":True,"fieldType":"calendar-photo",
         "backgroundAsset":False,"replaceable":True,"crossOrigin":"anonymous"}

def photo_collage(x,y,w,h,index,month,dark,accent,urls):
 # Ten composition families, varied further by index and month.
 mode=index%10
 gap=min(w,h)*.018
 if mode in (0,5): boxes=[(x,y,w,h)]
 elif mode in (1,6):boxes=[(x,y,w*.61-gap/2,h),(x+w*.61+gap/2,y,w*.39-gap/2,h)]
 elif mode in (2,7):boxes=[(x,y,w,h*.57-gap/2),(x,y+h*.57+gap/2,w,h*.43-gap/2)]
 elif mode in (3,8):boxes=[(x,y,w*.54-gap/2,h),(x+w*.54+gap/2,y,w*.46-gap/2,h*.49-gap/2),(x+w*.54+gap/2,y+h*.49+gap/2,w*.46-gap/2,h*.51-gap/2)]
 else:boxes=[(x,y,w*.5-gap/2,h*.5-gap/2),(x+w*.5+gap/2,y,w*.5-gap/2,h*.5-gap/2),(x,y+h*.5+gap/2,w*.5-gap/2,h*.5-gap/2),(x+w*.5+gap/2,y+h*.5+gap/2,w*.5-gap/2,h*.5-gap/2)]
 result=[rect("photo-area",x,y,w,h,dark)]
 for j,(bx,by,bw,bh) in enumerate(boxes):
  result.append(photo_object("replace-photo-%d"%j,bx,by,bw,bh,urls[(index*7+month+j*3)%len(urls)]))
  result.append(rect("photo-border-%d"%j,bx,by,bw,bh,"rgba(0,0,0,0)",accent,max(1,min(w,h)*.006)))
 return result

def _download_photos():
 """Store photos locally so the editor and preview use the same origin."""
 urls=[]
 for i,url in enumerate(PHOTO_URLS):
  path="calendar_assets/2027/photo_%02d.jpg"%i
  if not default_storage.exists(path):
   req=Request(url,headers={"User-Agent":"Mozilla/5.0"})
   try:
    with urlopen(req,timeout=15) as response:
     data=response.read(5_000_000)
    img=Image.open(BytesIO(data)).convert("RGB")
    img.thumbnail((1400,1400))
    out=BytesIO();img.save(out,format="JPEG",quality=86)
    default_storage.save(path,ContentFile(out.getvalue()))
   except Exception as exc:
    raise CommandError("Could not download calendar photo %d: %s. No templates were replaced."%(i,exc))
  urls.append(default_storage.url(path))
 return urls

def _preview(data,urls):
 """Make a real JPG gallery preview with photo collages and readable dates."""
 pg=data["pages"][0];w=float(data["document"]["width"]);h=float(data["document"]["height"])
 scale=min(840/max(w,1),1120/max(h,1))
 W=max(240,int(w*scale));H=max(320,int(h*scale))
 image=Image.new("RGB",(W,H),"#FFFFFF");d=ImageDraw.Draw(image)
 def xy(o):
  return [int(o["left"]*scale),int(o["top"]*scale),int((o["left"]+o["width"])*scale),int((o["top"]+o["height"])*scale)]
 for obj in pg["objects"]:
  kind=obj.get("type")
  if kind=="rect":
   box=xy(obj)
   fill=obj.get("fill","#FFFFFF")
   stroke=obj.get("stroke")
   if fill.startswith("rgba"):
    if stroke:d.rectangle(box,outline=stroke,width=max(1,int(obj.get("strokeWidth",1)*scale)))
    continue
   d.rectangle(box,fill=fill,outline=stroke,width=max(1,int(obj.get("strokeWidth",1)*scale)) if stroke else 1)
  elif kind=="circle":
   x=int(obj["left"]*scale);y=int(obj["top"]*scale);rr=max(1,int(obj["radius"]*scale))
   d.ellipse((x,y,x+rr*2,y+rr*2),fill=obj.get("fill","#243B35"))
  elif kind=="image":
   src=obj.get("src","")
   try:
    path=src.split("/media/",1)[1] if "/media/" in src else src.lstrip("/")
    with default_storage.open(path,"rb") as f:photo=Image.open(f).convert("RGB")
    box=xy(obj);ww=max(1,box[2]-box[0]);hh=max(1,box[3]-box[1])
    image.paste(ImageOps.fit(photo,(ww,hh)),(box[0],box[1]))
   except Exception as exc:
    raise CommandError("Preview photo unavailable: %s (%s)"%(src,exc))
  elif kind=="textbox":
   size=max(9,int(obj.get("fontSize",12)*scale))
   try:font=ImageFont.truetype("arial.ttf",size)
   except OSError:font=ImageFont.load_default()
   value=str(obj.get("text",""))
   x=int(obj["left"]*scale);y=int(obj["top"]*scale)
   if obj.get("textAlign")=="center":
    width=d.textbbox((0,0),value,font=font)[2]
    x+=max(0,(int(obj.get("width",0)*scale)-width)//2)
   d.text((x,y),value,font=font,fill=obj.get("fill","#142A28"))
 out=BytesIO();image.save(out,format="JPEG",quality=90)
 return ContentFile(out.getvalue())

DESIGNS=[
 ("Family Moments","Moments That Matter","#355A42","#F8F0E3","#CBA16B",0),
 ("Travel The World","Collect Beautiful Places","#145B9B","#FFF4E8","#FFAA46",1),
 ("Paws & Joy","Love Is A Four-Legged Word","#385D32","#FFF9E8","#D6A46C",2),
 ("Floral Elegance","A Year In Bloom","#853C67","#FFF1F5","#E8A6BC",3),
 ("Modern Minimal","Good Plans. Brighter Days.","#263B2D","#F8F5EB","#C5B9A3",4),
 ("Photo Collage","Collect Moments Not Things","#CB5A87","#FFF4D9","#F3B54A",5),
 ("Nature Escape","Explore Breathe Belong","#123F40","#F3F6EF","#84C7B2",6),
 ("Kids Fun","Little Moments, Big Memories","#1965B5","#FFF9DB","#FBCB3A",7),
 ("Luxury Classic","A Year Of New Beginnings","#191919","#FFF8E8","#CDAE65",8),
 ("Food & Lifestyle","Good Food Good Mood","#7C4937","#FFF7E9","#E6A469",9),
 ("Office Planner","Plan Focus Achieve","#264C3B","#FAF8F1","#B7C7A7",10),
 ("Seasons Collection","Four Seasons One Amazing Year","#42517C","#F8F5F1","#C1A4D7",11),
]
def page(year,month,index,w,h,urls):
 family=index//10
 variant=index%10
 title,tag,dark,bg,accent,style=DESIGNS[family%len(DESIGNS)]
 m=min(w,h)*.045
 # Twelve genuinely different compositions: split, full-bleed, triptych,
 # sidebars, photo strips, checkerboard, gallery and magazine arrangements.
 # Calendar product 222: never use cramped photo-left/date-right split layouts.
 # Keep a full-width, legible calendar below or above the photographic composition.
 # Ten variations retain different photo heights and alternate the reading order.
 fractions=(.46,.51,.44,.49,.42,.50,.47,.52,.43,.48)
 f=fractions[variant]
 usable_h=h-2*m
 gap=max(3,min(w,h)*.025)
 photo_h=usable_h*f-gap/2
 cal_h=usable_h*(1-f)-gap/2
 if variant in (2,5,8):
  cal=(m,m,w-2*m,cal_h)
  photo=(m,m+cal_h+gap,w-2*m,photo_h)
 else:
  photo=(m,m,w-2*m,photo_h)
  cal=(m,m+photo_h+gap,w-2*m,cal_h)
 px,py,pw,ph=photo;cx,cy,cw,ch=cal
 o=[rect("paper",0,0,w,h,bg),rect("outer-frame",m*.42,m*.42,w-m*.84,h-m*.84,"rgba(0,0,0,0)",dark,max(2,min(w,h)*.004))]
 # Photography is layered, separately editable, and the collage is different
 # for each of the twelve design families.
 gap=min(pw,ph)*(.012+.002*(family%5))
 split=.40+.035*(family%6)
 split2=.37+.045*((family+variant)%6)
 if variant in (0,5):slots=[(px,py,pw,ph)]
 elif variant in (1,6):slots=[(px,py,pw*split-gap,ph),(px+pw*split,py,pw*(1-split),ph)]
 elif variant in (2,7):slots=[(px,py,pw,ph*split2-gap),(px,py+ph*split2,pw*split-gap,ph*(1-split2)),(px+pw*split,py+ph*split2,pw*(1-split),ph*(1-split2))]
 elif variant in (3,8):slots=[(px,py,pw*split-gap,ph*split2-gap),(px+pw*split,py,pw*(1-split),ph*split2-gap),(px,py+ph*split2,pw*split-gap,ph*(1-split2)),(px+pw*split,py+ph*split2,pw*(1-split),ph*(1-split2))]
 elif variant==4:slots=[(px,py,pw*split-gap,ph),(px+pw*split,py,pw*(1-split),ph*split2-gap),(px+pw*split,py+ph*split2,pw*(1-split),ph*(1-split2))]
 else:slots=[(px,py,pw,ph*split2-gap),(px,py+ph*split2,pw,ph*(1-split2))]
 for j,(sx,sy,sw,sh) in enumerate(slots):
  o.append(photo_object("photo-%02d"%j,sx,sy,sw,sh,urls[(index*5+month+j*2)%len(urls)]))
  o.append(rect("photo-frame-%02d"%j,sx,sy,sw,sh,"rgba(0,0,0,0)",bg,max(2,min(w,h)*.004)))
 # Separate editorial caption from the photography to prevent lost text.
 # A contrasting solid plaque is always legible, even on bright photographs.
 bx=px+pw*.075
 bw=pw*.85
 bh=ph*.20
 by=py+ph*.74
 plaque=dark if variant in (1,3,6,8) else bg
 title_color="#FFFFFF" if plaque==dark else dark
 o.append(rect("title-shadow",bx+pw*.009,by+ph*.01,bw,bh,accent))
 o.append(rect("title-panel",bx,by,bw,bh,plaque,accent,max(1,min(w,h)*.002)))
 o.append(txt("collection-title",bx+bw*.055,by+bh*.13,bw*.89,title,
              max(13,min(bw*.052,bh*.26)),title_color,"center","700","Georgia"))
 o.append(txt("collection-subtitle",bx+bw*.055,by+bh*.65,bw*.89,tag,
              max(9,min(bw*.026,bh*.14)),title_color,"center","600","Arial"))
 # Date area uses generous white space and restrained grid lines.
 o.append(rect("calendar-paper",cx,cy,cw,ch,"#FFFFFF",dark,max(2,min(w,h)*.003)))
 o.append(rect("calendar-header",cx,cy,cw,ch*.18,dark))
 header_text="#FFFFFF"
 o.append(txt("month-title",cx+cw*.05,cy+ch*.025,cw*.90,
              calendar.month_name[month].upper()+"  "+str(year),
              max(14,min(cw*.067,ch*.105)),header_text,"center","700","Georgia"))
 # Ten different date treatments: pastel chips, dark weekends, colour bands,
 # rounded dots, minimal ruled, editorial, checker, outlined, highlighted, blocks.
 gx=cx+cw*.045;gy=cy+ch*.235;gw=cw*.91
 row=ch*.091;cell=gw/7
 fs=max(9,min(cell*.35,row*.40))
 date_style=variant
 weekdays=("SUN","MON","TUE","WED","THU","FRI","SAT")
 for col,label in enumerate(weekdays):
  hx=gx+col*cell
  if date_style in (0,3,6,9):
   o.append(rect("weekday-band-%d"%col,hx,gy,cell*.97,row*.72,
                 accent if col in (0,6) else dark))
   label_color="#FFFFFF"
  elif date_style in (1,4,7):
   o.append(rect("weekday-band-%d"%col,hx,gy,cell*.97,row*.72,
                 bg if col in (0,6) else "#F2F0EC"))
   label_color=dark
  else:
   o.append(rect("weekday-band-%d"%col,hx,gy,cell*.97,row*.72,
                 bg))
   label_color=dark
  o.append(txt("weekday-%d"%col,hx,gy+row*.10,cell,label,
               max(8,fs*.72),label_color,"center","700","Arial"))
 weeks=calendar.Calendar(firstweekday=6).monthdayscalendar(year,month)
 for ri in range(6):
  week=weeks[ri] if ri<len(weeks) else [0]*7
  for col,day in enumerate(week):
   x=gx+col*cell;y=gy+(ri+1)*row
   weekend=col in (0,6)
   if date_style==0:fill=bg if weekend else "#FFFFFF"
   elif date_style==1:fill="#FFFFFF"
   elif date_style==2:fill=bg if ri%2 else "#FFFFFF"
   elif date_style==3:fill=dark if weekend else bg
   elif date_style==4:fill="#FFFFFF"
   elif date_style==5:fill=bg if weekend else "#FFFFFF"
   elif date_style==6:fill=bg if (ri+col)%2 else "#FFFFFF"
   elif date_style==7:fill="#FFFFFF"
   elif date_style==8:fill=bg if weekend else "#FFFFFF"
   else:fill=bg if weekend else "#FFFFFF"
   stroke=accent if date_style in (1,7,8) else "#E7E4E0"
   o.append(rect("date-cell-%d-%d"%(ri,col),x,y,cell*.975,row*.94,
                 fill,stroke,max(.5,min(w,h)*.0008)))
   if not day:continue
   if date_style in (1,5,8):
    o.append(circle("date-dot-%d"%day,x+cell*.25,y+row*.13,
                    min(cell,row)*.22,dark))
    ink="#FFFFFF"
    dx=x+cell*.25
    dy=y+row*.17
    dw=cell*.44
    align="center"
   elif date_style==3 and weekend:
    ink="#FFFFFF";dx=x+cell*.08;dy=y+row*.11;dw=cell*.8;align="left"
   else:
    ink=dark
    dx=x+cell*.08;dy=y+row*.11;dw=cell*.8;align="left"
   o.append(txt("day-%d"%day,dx,dy,dw,str(day),fs,ink,align,"700","Arial"))
 o.append(rect("footer-rule",cx+cw*.06,cy+ch*.895,cw*.88,max(1,min(w,h)*.002),accent))
 o.append(txt("footer",cx+cw*.07,cy+ch*.92,cw*.86,"YOUR MEMORIES • YOUR YEAR",
              max(7,min(cw*.023,ch*.028)),dark,"center","500","Arial"))
 return {"name":calendar.month_name[month],"background":bg,"objects":o}
def payload(product,year,i,urls):
 w,h=product.width,product.height
 return {"version":2,"generator":GENERATOR,"templateType":"editable-master",
         "designName":"Photo Calendar %s %d - %03d"%(DESIGNS[i//10][0],year,i+1),
         "document":{"width":w,"height":h,"unit":"in",
                     "physical":{"widthIn":float(product.print_width_in),"heightIn":float(product.print_height_in)},
                     "profile":"calendar"},
         "pages":[page(year,m,i,w,h,urls) for m in range(1,13)],
         "photoSlotsEditable":True,"requiresImageCors":True,
         "editable":True,"editorNative":True,"editorSchema":"fabric-primitives-v1"}
class Command(BaseCommand):
 help="Generate 100 photo calendars with ten editable date-grid styles and 12 months."
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
  self.stdout.write("Preparing 100 photo-calendar designs with decorated date grids, 12 pages each")
  if o["dry_run"]:return
  urls=_download_photos()
  with transaction.atomic():
   if o["replace"]:qs.delete()
   for i in range(100):
    data=payload(p,o["year"],i,urls)
    template=DesignTemplate.objects.create(product=p,name=data["designName"],json_data=data,is_active=True)
    template.preview.save("calendar_%d_%03d.jpg"%(o["year"],i+1),_preview(data,urls),save=True)
  self.stdout.write(self.style.SUCCESS("Created 100 editable photo-calendar designs with decorated dates"))
