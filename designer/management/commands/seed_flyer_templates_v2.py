# designer/management/commands/seed_flyer_templates_v2.py
#
# ZenVibe Flyer Library V2
# Creates 100 genuinely different, editor-native promotional flyer templates.
#
# Key differences from V1:
# - Real flyer hierarchy: hero area, headline, supporting copy, offer/event block, CTA, footer/contact.
# - 20 materially different layout architectures × 5 hero/art systems = 100 compositions.
# - Structural duplicate validation ignores colours and literal text.
# - Uses only editor-supported Fabric-style primitives: rect, circle, ellipse, line, polygon, textbox.
# - JSON is the editable master. SVG is preview only.
# - Includes document.width/document.height for the current ZenVibe editor scaling logic.
#
# Usage:
#   python manage.py seed_flyer_templates_v2 --product-id 62 --dry-run
#   python manage.py seed_flyer_templates_v2 --product-id 62 --replace-generated
#
# IMPORTANT:
# Flyer source canvas defaults to 800×1100 portrait. If your Product itself is 1000×800
# landscape, configure the product's internal editor canvas to portrait as well so the editor
# does not non-uniformly squash a portrait template into a landscape canvas.

import hashlib
import html
import json
import math
from copy import deepcopy

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product


LIBRARY_VERSION = 2
LIBRARY_KEY = "flyer_library_version"
LIBRARY_FLAG = "flyer_library"
GENERATOR_ID = "zenvibe-flyer-v2-pro-100"
PREFIX = "ZV2 Flyer"

SOURCE_W = 800
SOURCE_H = 1100

_counter = 0


# ---------------------------------------------------------------------------
# Fabric-style editable primitives
# ---------------------------------------------------------------------------

def oid(prefix="obj"):
    global _counter
    _counter += 1
    return f"{prefix}-{_counter:07d}"


def rect(x, y, w, h, fill, *, stroke=None, sw=0, rx=0, ry=0,
         opacity=1, name="Rectangle", angle=0):
    return {
        "id": oid("rect"), "name": name, "type": "rect",
        "left": round(x, 2), "top": round(y, 2),
        "width": round(w, 2), "height": round(h, 2),
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "rx": rx, "ry": ry, "opacity": opacity,
        "angle": angle, "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def circle(cx, cy, r, fill, *, stroke=None, sw=0, opacity=1, name="Circle"):
    return {
        "id": oid("circle"), "name": name, "type": "circle",
        "left": round(cx-r, 2), "top": round(cy-r, 2), "radius": round(r, 2),
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "angle": 0, "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def ellipse(cx, cy, rx, ry, fill, *, stroke=None, sw=0,
            opacity=1, angle=0, name="Ellipse"):
    return {
        "id": oid("ellipse"), "name": name, "type": "ellipse",
        "left": round(cx-rx, 2), "top": round(cy-ry, 2),
        "rx": round(rx, 2), "ry": round(ry, 2),
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "angle": angle, "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def line(x1, y1, x2, y2, stroke, *, sw=2, opacity=1, name="Line"):
    return {
        "id": oid("line"), "name": name, "type": "line",
        "x1": round(x1, 2), "y1": round(y1, 2),
        "x2": round(x2, 2), "y2": round(y2, 2),
        "left": round(min(x1, x2), 2), "top": round(min(y1, y2), 2),
        "stroke": stroke, "strokeWidth": sw, "opacity": opacity,
        "fill": None, "angle": 0, "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def polygon(points, fill, *, stroke=None, sw=0, opacity=1, name="Polygon"):
    return {
        "id": oid("poly"), "name": name, "type": "polygon",
        "points": [{"x": round(float(x), 2), "y": round(float(y), 2)} for x, y in points],
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "left": 0, "top": 0, "angle": 0,
        "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def textbox(text, x, y, w, size, fill, *, family="Inter", weight="400",
            align="left", line_height=1.05, name="Text", char_spacing=0,
            style="normal", angle=0):
    return {
        "id": oid("text"), "name": name, "type": "textbox",
        "text": text, "left": round(x, 2), "top": round(y, 2),
        "width": round(w, 2), "fontSize": round(size, 2),
        "fill": fill, "fontFamily": family, "font": family,
        "fontWeight": weight, "fontStyle": style,
        "textAlign": align, "lineHeight": line_height,
        "charSpacing": char_spacing, "scaleX": 1, "scaleY": 1,
        "angle": angle, "opacity": 1,
        "customerEditable": True,
        "selectable": True, "evented": True, "locked": False,
        "fieldType": "flyer-text",
    }


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

PALETTES = [
    {"name":"Ivory Navy","bg":"#F7F4EE","ink":"#10243A","accent":"#245E8F","accent2":"#B7D1E5","soft":"#E8EEF2","gold":"#C6A15B"},
    {"name":"Black Gold","bg":"#111113","ink":"#F7F2E8","accent":"#D1AE68","accent2":"#6E5732","soft":"#252527","gold":"#E5C27A"},
    {"name":"Emerald Cream","bg":"#F5F1E8","ink":"#183E34","accent":"#2A7258","accent2":"#A8C7B7","soft":"#E3ECE6","gold":"#B89555"},
    {"name":"Cobalt","bg":"#F5F7FB","ink":"#102D61","accent":"#2459E0","accent2":"#9DB8FF","soft":"#E7EDFF","gold":"#BE9B5B"},
    {"name":"Wine Blush","bg":"#F9EEF1","ink":"#571F37","accent":"#B43F6E","accent2":"#E2A9BD","soft":"#F4DDE5","gold":"#C39D59"},
    {"name":"Terracotta","bg":"#F5EAE2","ink":"#4A2C25","accent":"#B45E42","accent2":"#DEAB94","soft":"#EED7CB","gold":"#B98A4C"},
    {"name":"Sage","bg":"#F4F1E7","ink":"#34453D","accent":"#708F76","accent2":"#BFCDB9","soft":"#E3E8DA","gold":"#B89A62"},
    {"name":"Night Neon","bg":"#0A0C12","ink":"#F6F7FB","accent":"#31D4E8","accent2":"#8A66FF","soft":"#171B27","gold":"#D4B35F"},
    {"name":"Ruby","bg":"#2A1018","ink":"#FFF7EF","accent":"#B13253","accent2":"#DC9EB0","soft":"#461925","gold":"#DFB86E"},
    {"name":"Monochrome","bg":"#F4F4F2","ink":"#171717","accent":"#4A4A4A","accent2":"#B8B8B3","soft":"#E5E5E1","gold":"#9A865F"},
]

FONT_PAIRS = [
    ("Playfair Display","Inter"),
    ("Cormorant Garamond","Montserrat"),
    ("DM Serif Display","Inter"),
    ("Libre Baskerville","Montserrat"),
    ("Bodoni Moda","Inter"),
    ("Poppins","Inter"),
    ("Montserrat","Inter"),
    ("Oswald","Inter"),
    ("Raleway","Inter"),
    ("Cinzel","Montserrat"),
]

SECTORS = [
    ("Business Solutions","SMARTER BUSINESS.\nSTRONGER RESULTS.","Strategy • Systems • Growth","BOOK A CONSULTATION","03 9000 0000","zenvibe.com"),
    ("Luxury Branding","WE BUILD\nICONIC BRANDS","Identity • Direction • Digital","DISCOVER THE STUDIO","hello@studio.com","brandstudio.com"),
    ("Digital Marketing","GROW FASTER\nONLINE","SEO • Social • Performance","START YOUR CAMPAIGN","1300 555 110","growthagency.com"),
    ("Creative Agency","IDEAS THAT\nMOVE PEOPLE","Brand • Content • Experience","LET'S CREATE","hello@create.co","create.co"),
    ("Real Estate","FIND YOUR\nNEXT HOME","Premium properties • Personal service","VIEW PROPERTIES","0400 123 456","property.com"),
    ("Interior Design","DESIGNED FOR\nBETTER LIVING","Interiors • Styling • Space planning","BOOK A CONSULT","03 9000 2000","interiors.com"),
    ("Restaurant","A NIGHT WORTH\nTASTING","Seasonal menu • Local produce","RESERVE A TABLE","03 9000 3100","restaurant.com"),
    ("Cafe","GOOD COFFEE.\nGOOD DAYS.","Coffee • Brunch • Fresh bakes","VISIT TODAY","7AM–4PM DAILY","cafename.com"),
    ("Bakery","FRESHLY BAKED\nEVERY MORNING","Pastries • Cakes • Artisan bread","ORDER NOW","03 9000 3200","bakery.com"),
    ("Healthy Food","EAT BRIGHT.\nFEEL BETTER.","Fresh bowls • Honest ingredients","VIEW MENU","DELIVERY AVAILABLE","freshfood.com"),
    ("Fitness","BUILD YOUR\nSTRONGEST SELF","Strength • Conditioning • Coaching","JOIN TODAY","7 DAY TRIAL","fitness.com"),
    ("Yoga","MOVE. BREATHE.\nRESET.","Yoga • Pilates • Mindfulness","BOOK A CLASS","FIRST CLASS FREE","yogastudio.com"),
    ("Wellness","YOUR WELLNESS\nMATTERS","Holistic care for modern life","LEARN MORE","03 9000 4100","wellness.com"),
    ("Beauty","GLOW WITH\nCONFIDENCE","Skin • Beauty • Self-care","BOOK NOW","20% NEW CLIENT OFFER","beauty.com"),
    ("Hair Studio","YOUR HAIR.\nYOUR SIGNATURE.","Cut • Colour • Styling","BOOK AN APPOINTMENT","03 9000 4300","hairstudio.com"),
    ("Fashion","THE NEW\nCOLLECTION","Modern essentials • Limited release","SHOP NOW","NEW SEASON","fashion.com"),
    ("Jewellery","MADE TO\nBE REMEMBERED","Fine jewellery • Timeless design","EXPLORE","PRIVATE VIEWINGS","jewels.com"),
    ("Watches","TIME,\nREFINED.","Precision • Craft • Character","DISCOVER","LIMITED EDITION","watches.com"),
    ("Travel","GO SOMEWHERE\nBEAUTIFUL","Curated escapes • Tailored journeys","PLAN YOUR TRIP","SAVE 15%","travel.com"),
    ("Adventure","ADVENTURE\nAWAITS","Explore beyond the ordinary","START EXPLORING","WEEKEND PACKAGES","adventure.com"),
    ("Conference","BUSINESS\nCONFERENCE 2026","Ideas • Leaders • Opportunity","REGISTER NOW","18 OCT • MELBOURNE","conference.com"),
    ("Annual Summit","THE FUTURE\nSTARTS HERE","Connect • Learn • Lead","GET TICKETS","24–25 NOV","summit.com"),
    ("Education","LEARN TODAY.\nLEAD TOMORROW.","Programs for ambitious minds","APPLY NOW","2027 INTAKE OPEN","college.edu"),
    ("Online Course","LEARN FROM\nANYWHERE","Flexible • Practical • Career-ready","ENROL TODAY","START ANYTIME","academy.com"),
    ("Music Festival","LIVE LOUD.\nFEEL EVERYTHING.","One night • Multiple stages","GET TICKETS","SAT 14 NOV • 5PM","musicfest.com"),
    ("Night Party","AFTER\nDARK","Music • Lights • Late-night energy","RSVP NOW","FRIDAY • 9PM","afterdark.com"),
    ("Live Concert","LIVE IN\nCONCERT","One stage • One unforgettable night","GET TICKETS","ARENA • 8PM","liveconcert.com"),
    ("Art Exhibition","NEW\nPERSPECTIVES","Contemporary art exhibition","VIEW EXHIBITION","01–22 OCT","gallery.com"),
    ("Theatre","THE NIGHT\nBEGINS HERE","A new live production","BOOK SEATS","LIMITED SEASON","theatre.com"),
    ("Book Fair","READ.\nDISCOVER.\nCONNECT.","Authors • Talks • New releases","JOIN US","SUNDAY 10AM–5PM","bookfair.com"),
    ("Science Expo","IMAGINE\nWHAT'S NEXT","Science • Robotics • Discovery","REGISTER","FREE ENTRY","scienceexpo.com"),
    ("Technology","BUILD THE\nFUTURE","Cloud • AI • Digital transformation","TALK TO US","ENTERPRISE SOLUTIONS","technology.com"),
    ("Car Expo","ENGINEERED\nTO EXCITE","Performance • Design • Innovation","SEE THE RANGE","THIS WEEKEND","carexpo.com"),
    ("Auto Service","DRIVE WITH\nCONFIDENCE","Service • Repairs • Diagnostics","BOOK SERVICE","FROM $149","autoservice.com"),
    ("Car Rental","YOUR ROAD.\nYOUR WAY.","Flexible rental • Easy booking","BOOK A CAR","FROM $49/DAY","carrental.com"),
    ("Investment","BUILD WEALTH\nWITH CLARITY","Property • Strategy • Growth","SPEAK TO US","FREE STRATEGY CALL","invest.com"),
    ("Financial Planning","PLAN WITH\nCONFIDENCE","Goals • Advice • Future","BOOK A MEETING","03 9000 6100","finance.com"),
    ("Insurance","PROTECTION FOR\nWHAT MATTERS","Personal • Family • Business","GET A QUOTE","FAST ONLINE QUOTES","insurance.com"),
    ("Law","CLEAR ADVICE.\nSTRONG ADVOCACY.","Commercial • Property • Disputes","CONTACT US","03 9000 6300","lawfirm.com"),
    ("Medical","CARE YOU\nCAN TRUST","Professional care • Modern facilities","BOOK NOW","SAME DAY APPOINTMENTS","medical.com"),
    ("Dental","SMILE WITH\nCONFIDENCE","General • Cosmetic • Preventive","BOOK A VISIT","NEW PATIENT OFFER","dental.com"),
    ("Pet Care","HAPPY PETS.\nHAPPY HOMES.","Grooming • Wellness • Care","BOOK TODAY","03 9000 6600","petcare.com"),
    ("Veterinary","COMPASSIONATE\nPET CARE","Health • Prevention • Support","BOOK A VISIT","OPEN 7 DAYS","vetcare.com"),
    ("Pharmacy","HEALTHCARE,\nCLOSE TO HOME","Advice • Essentials • Wellness","VISIT US","OPEN LATE","pharmacy.com"),
    ("Home Cleaning","A CLEANER\nHOME AWAITS","Reliable • Detailed • Trusted","GET A QUOTE","20% FIRST CLEAN","cleaning.com"),
    ("Laundry","FRESH.\nCLEAN.\nEASY.","Wash • Dry • Fold • Delivery","BOOK PICKUP","SAME DAY SERVICE","laundry.com"),
    ("Moving","MOVE WITHOUT\nTHE STRESS","Packing • Transport • Storage","GET A QUOTE","LOCAL & INTERSTATE","moving.com"),
    ("Pest Control","PESTS OUT.\nPEACE IN.","Safe • Effective • Reliable","BOOK TODAY","FROM $129","pestcontrol.com"),
    ("Repair","FIXED FAST.\nDONE RIGHT.","Home • Office • Maintenance","CALL TODAY","SAME DAY SERVICE","repair.com"),
    ("Electrical","POWERED BY\nEXPERTS","Residential • Commercial • Emergency","BOOK AN ELECTRICIAN","24/7 SERVICE","electrical.com"),
    ("Plumbing","PLUMBING\nWITHOUT DELAY","Leaks • Hot water • Emergency","CALL NOW","24/7 RESPONSE","plumbing.com"),
    ("Landscaping","OUTDOOR SPACES\nMADE BETTER","Design • Build • Maintain","GET A QUOTE","FREE SITE VISIT","landscape.com"),
    ("IT Support","TECH HELP,\nWITHOUT THE WAIT","Support • Devices • Networks","GET SUPPORT","BUSINESS IT","itsupport.com"),
    ("Cyber Security","SECURE YOUR\nDIGITAL WORLD","Protection • Monitoring • Response","BOOK A REVIEW","FREE SECURITY CHECK","cyber.com"),
    ("Mobile App","TURN YOUR IDEA\nINTO AN APP","Design • Development • Launch","START A PROJECT","IOS & ANDROID","mobileapp.com"),
    ("UI UX","DESIGN PEOPLE\nLOVE TO USE","Research • UX • Interface","WORK WITH US","PRODUCT DESIGN","uxstudio.com"),
    ("Web Development","WEBSITES THAT\nWORK HARDER","Design • Build • Optimise","START YOUR WEBSITE","FAST • SECURE","webstudio.com"),
    ("Software","SOFTWARE BUILT\nAROUND YOU","Custom platforms • Integrations","TALK TO US","SCALABLE SYSTEMS","software.com"),
    ("Cloud","MOVE FASTER\nIN THE CLOUD","Migration • Security • Optimisation","BOOK A REVIEW","CLOUD CONSULTING","cloud.com"),
    ("Data Analytics","TURN DATA INTO\nDIRECTION","Dashboards • Insights • Forecasting","SEE WHAT'S POSSIBLE","DATA STRATEGY","analytics.com"),
    ("AI Solutions","PUT AI TO\nWORK","Automation • Intelligence • Scale","DISCOVER AI","AI FOR BUSINESS","aisolutions.com"),
    ("Startup","BUILD.\nLAUNCH.\nGROW.","Strategy • Product • Funding","START TODAY","FOUNDER SUPPORT","startup.com"),
    ("Co-working","WORK BETTER\nTOGETHER","Desks • Rooms • Community","BOOK A TOUR","FLEXIBLE MEMBERSHIP","cowork.com"),
    ("Freelance","YOUR NEXT\nCREATIVE PARTNER","Design • Content • Digital","LET'S WORK TOGETHER","AVAILABLE NOW","creativepro.com"),
    ("Wedding Services","YOUR DAY.\nBEAUTIFULLY DONE.","Planning • Styling • Coordination","BOOK A CONSULT","2027 DATES OPEN","weddings.com"),
    ("Event Planning","MEMORABLE EVENTS.\nMADE SIMPLE.","Concept • Styling • Production","PLAN YOUR EVENT","CORPORATE & SOCIAL","events.com"),
    ("Birthday Party","LET'S\nCELEBRATE","Fun • Food • Memories","RSVP TODAY","SATURDAY • 4PM","party.com"),
    ("Baby Shower","A LITTLE LOVE\nIS ON THE WAY","Join us for a beautiful celebration","RSVP","SUNDAY • 2PM","babyshower.com"),
    ("Graduation","THE NEXT\nCHAPTER STARTS","Celebrate the class of 2026","JOIN US","FRIDAY • 6PM","graduation.com"),
    ("Corporate Event","CONNECT.\nCELEBRATE.\nINSPIRE.","Premium corporate experiences","ENQUIRE NOW","FULL EVENT SERVICE","corporateevents.com"),
    ("Christmas Offer","MAKE IT A\nMAGICAL CHRISTMAS","Seasonal favourites • Limited time","SHOP CHRISTMAS","UP TO 30% OFF","christmas.com"),
    ("New Year","NEW YEAR.\nNEW ENERGY.","Celebrate in style","BOOK NOW","31 DEC • 8PM","newyear.com"),
    ("Valentine","LOVE LOOKS\nGOOD ON YOU","Something special for someone special","SHOP NOW","VALENTINE EDIT","valentine.com"),
    ("Mothers Day","FOR EVERYTHING\nSHE DOES","Thoughtful gifts • Beautiful moments","SHOP GIFTS","MOTHER'S DAY","mothersday.com"),
    ("Black Friday","BLACK\nFRIDAY","Biggest offers of the year","SHOP NOW","UP TO 60% OFF","blackfriday.com"),
    ("Mega Sale","MEGA\nSALE","Limited time • Major savings","SHOP THE SALE","SAVE UP TO 50%","megasale.com"),
    ("Special Offer","A SPECIAL\nOFFER FOR YOU","Selected favourites • Limited time","CLAIM OFFER","SAVE 25%","specialoffer.com"),
    ("Big Discount","BIG DEALS.\nSMALL PRICES.","Shop selected lines now","SHOP NOW","40% OFF","discount.com"),
    ("Super Sale","SUPER\nSALE","Prices dropped • Stock moving fast","SHOP TODAY","UP TO 70% OFF","supersale.com"),
    ("Weekend Offer","THIS WEEKEND\nONLY","Limited time savings","SHOP THE OFFER","ENDS SUNDAY","weekendoffer.com"),
    ("Limited Time","DON'T\nMISS OUT","A limited release at a special price","GET IT NOW","48 HOURS ONLY","limited.com"),
    ("Clearance","CLEARANCE\nEVENT","Final pieces • Final prices","SHOP CLEARANCE","LAST CHANCE","clearance.com"),
    ("Hot Deals","HOT\nDEALS","Fresh offers • Limited stock","SEE DEALS","THIS WEEK ONLY","hotdeals.com"),
    ("Retail","NEW IN\nSTORE","Fresh arrivals • New favourites","SHOP THE DROP","JUST LANDED","retail.com"),
    ("Architecture","DESIGN THAT\nSHAPES LIFE","Architecture • Planning • Interiors","VIEW PROJECTS","DESIGN STUDIO","architecture.com"),
    ("Luxury Living","LIVE\nBEAUTIFULLY","Premium spaces • Refined details","DISCOVER MORE","PRIVATE INSPECTIONS","luxuryliving.com"),
    ("Photography","STORIES,\nBEAUTIFULLY SEEN","Portrait • Brand • Event","BOOK A SHOOT","2027 BOOKINGS OPEN","photography.com"),
    ("Consulting","CLARITY FOR\nWHAT'S NEXT","Strategy • Operations • Growth","BOOK A SESSION","EXECUTIVE ADVISORY","consulting.com"),
    ("Recruitment","FIND PEOPLE\nWHO FIT","Permanent • Contract • Executive","TALK TO US","HIRING NOW","recruitment.com"),
    ("Logistics","MOVE SMARTER.\nDELIVER BETTER.","Freight • Warehousing • Fulfilment","GET A QUOTE","NATIONWIDE","logistics.com"),
    ("Construction","BUILT WITH\nCONFIDENCE","Commercial • Residential • Fitout","DISCUSS YOUR PROJECT","LICENSED BUILDERS","construction.com"),
    ("Solar","POWER YOUR\nFUTURE","Solar • Battery • Smart energy","GET A QUOTE","SAVE ON ENERGY","solar.com"),
    ("Sustainability","BETTER CHOICES.\nBETTER FUTURE.","Energy • Waste • Strategy","START TODAY","SUSTAINABILITY PLAN","sustainable.com"),
    ("Hotel","STAY\nSOMEWHERE SPECIAL","Rooms • Dining • Experiences","BOOK YOUR STAY","DIRECT BOOKING OFFER","hotel.com"),
    ("Spa","REST.\nRESET.\nRESTORE.","Massage • Skin • Wellness","BOOK YOUR ESCAPE","GIFT VOUCHERS","spa.com"),
    ("Wine Dinner","AN EVENING OF\nWINE & DINING","Curated menu • Matched wines","RESERVE YOUR SEAT","FRIDAY • 7PM","winedinner.com"),
    ("Community","TOGETHER,\nWE THRIVE","Local people • Local ideas • Local impact","GET INVOLVED","COMMUNITY DAY","community.com"),
    ("Charity","MAKE A\nDIFFERENCE","Support a cause that matters","DONATE TODAY","EVERY GIFT COUNTS","charity.org"),
    ("Workshop","LEARN BY\nDOING","Practical skills • Expert guidance","BOOK YOUR PLACE","LIMITED SEATS","workshop.com"),
    ("Premium Launch","INTRODUCING\nSOMETHING NEW","A refined launch • Designed to stand out","DISCOVER NOW","LAUNCH WEEK","premiumlaunch.com"),
]

FINISHES = ["Matte", "High-Gloss", "Soft-Touch", "Satin", "Foil Accent"]


# ---------------------------------------------------------------------------
# Shared flyer components
# ---------------------------------------------------------------------------

def add_footer(o, p, body_font, phone, web, *, dark=False, y=1010):
    fg = p["ink"] if not dark else p["bg"]
    line(o_x:=55, y1:=y-20, x2:=745, y2:=y-20, stroke=fg, sw=1, opacity=.28)
    o.append(textbox(phone, 55, y, 310, 17, fg, family=body_font, weight="600", name="Contact"))
    o.append(textbox(web, 435, y, 310, 17, fg, family=body_font, weight="600", align="right", name="Website"))


def add_cta(o, p, text, x, y, w=250, *, inverse=False, body_font="Inter"):
    fill = p["ink"] if not inverse else p["bg"]
    fg = p["bg"] if not inverse else p["ink"]
    o.append(rect(x, y, w, 54, fill, rx=27, ry=27, name="CTA button"))
    o.append(textbox(text, x+18, y+15, w-36, 16, fg, family=body_font, weight="700", align="center", name="CTA"))


def add_offer_badge(o, p, text, cx, cy, r=74, *, dark=False, body_font="Inter"):
    fill = p["accent"] if not dark else p["gold"]
    fg = p["bg"] if not dark else p["ink"]
    o.append(circle(cx, cy, r, fill, name="Offer badge"))
    o.append(circle(cx, cy, r-10, "none", stroke=fg, sw=1.5, opacity=.75, name="Offer ring"))
    o.append(textbox(text, cx-r+14, cy-24, (r-14)*2, 18, fg, family=body_font, weight="800", align="center", line_height=1.0, name="Offer"))


def add_micro_brand(o, p, body_font, x=55, y=55, dark=False):
    fg = p["bg"] if dark else p["ink"]
    o.append(rect(x, y, 34, 34, p["accent"], rx=7, ry=7, name="Logo mark"))
    o.append(textbox("ZENVIBE", x+46, y+6, 170, 16, fg, family=body_font, weight="800", char_spacing=80, name="Brand"))


# ---------------------------------------------------------------------------
# Hero / illustration systems
# Each is fully editable vector artwork, not a flattened image.
# ---------------------------------------------------------------------------

def hero_editorial(o,p,x,y,w,h,variant=0):
    o.append(rect(x,y,w,h,p["soft"],rx=12,ry=12,name="Hero field"))
    for i in range(5):
        yy=y+40+i*(h-80)/4
        o.append(line(x+30,yy,x+w-30,yy,p["accent2"],sw=1,opacity=.5,name="Editorial line"))
    o.append(rect(x+w*.58,y+30,w*.28,h-60,p["accent"],rx=8,ry=8,opacity=.9,name="Editorial panel"))
    o.append(circle(x+w*.72,y+h*.30,min(w,h)*.11,p["gold"],opacity=.9,name="Editorial disc"))
    o.append(rect(x+35,y+h*.64,w*.38,20,p["ink"],rx=10,ry=10,opacity=.9,name="Editorial bar"))
    o.append(rect(x+35,y+h*.73,w*.28,10,p["accent"],rx=5,ry=5,opacity=.75,name="Editorial bar small"))


def hero_product(o,p,x,y,w,h,variant=0):
    o.append(rect(x,y,w,h,p["soft"],rx=16,ry=16,name="Product stage"))
    o.append(ellipse(x+w*.52,y+h*.75,w*.34,h*.10,p["accent2"],opacity=.45,name="Product shadow"))
    o.append(rect(x+w*.29,y+h*.16,w*.42,h*.58,p["bg"],stroke=p["ink"],sw=2,rx=18,ry=18,name="Product pack"))
    o.append(rect(x+w*.35,y+h*.24,w*.30,h*.13,p["accent"],rx=5,ry=5,name="Product label"))
    o.append(circle(x+w*.50,y+h*.52,min(w,h)*.12,p["gold"],opacity=.9,name="Product seal"))
    o.append(line(x+w*.36,y+h*.62,x+w*.64,y+h*.62,p["ink"],sw=2,opacity=.55,name="Product line"))


def hero_architecture(o,p,x,y,w,h,variant=0):
    o.append(rect(x,y,w,h,p["soft"],name="Architecture field"))
    base=y+h*.78
    widths=[.12,.18,.10,.22,.13,.16]
    cur=x+w*.05
    for i,ww in enumerate(widths):
        bh=h*(.28 + ((i*3+variant)%5)*.07)
        o.append(rect(cur,base-bh,w*ww,bh,p["ink"] if i%2==0 else p["accent"],opacity=.9,name="Building"))
        for r in range(3):
            o.append(rect(cur+w*ww*.18,base-bh+30+r*42,w*ww*.18,18,p["bg"],opacity=.65,name="Window"))
        cur += w*(ww+.025)
    o.append(circle(x+w*.78,y+h*.20,min(w,h)*.11,p["gold"],opacity=.85,name="Sun"))
    o.append(line(x+w*.04,base,x+w*.96,base,p["ink"],sw=3,opacity=.8,name="Ground"))


def hero_botanical(o,p,x,y,w,h,variant=0):
    o.append(rect(x,y,w,h,p["soft"],rx=14,ry=14,name="Botanical field"))
    stems=[(.18,.78,.40,.18),(.42,.82,.58,.16),(.68,.82,.75,.22),(.82,.76,.63,.30)]
    for sx,sy,ex,ey in stems:
        x1=x+w*sx; y1=y+h*sy; x2=x+w*ex; y2=y+h*ey
        o.append(line(x1,y1,x2,y2,p["accent"],sw=3,opacity=.9,name="Stem"))
        for t in (.28,.52,.72):
            lx=x1+(x2-x1)*t; ly=y1+(y2-y1)*t
            o.append(ellipse(lx-16,ly-8,24,10,p["accent2"],angle=-25,name="Leaf"))
            o.append(ellipse(lx+17,ly+5,22,9,p["accent"],angle=25,name="Leaf"))
    o.append(circle(x+w*.58,y+h*.28,min(w,h)*.12,p["gold"],opacity=.88,name="Botanical focal"))
    for a in range(0,360,45):
        rad=math.radians(a)
        cx=x+w*.58+math.cos(rad)*min(w,h)*.15
        cy=y+h*.28+math.sin(rad)*min(w,h)*.15
        o.append(ellipse(cx,cy,22,9,p["accent"],angle=a,name="Petal"))


def hero_event(o,p,x,y,w,h,variant=0):
    o.append(rect(x,y,w,h,p["ink"],name="Event field"))
    for i in range(8):
        cx=x+w*(.10+.11*i)
        cy=y+h*(.18+(.12 if i%2 else 0))
        o.append(circle(cx,cy,12+(i%3)*8,p["accent"] if i%2 else p["accent2"],opacity=.85,name="Event light"))
        o.append(line(cx,cy+10,cx-25+(i%2)*50,y+h*.92,p["accent2"],sw=1,opacity=.35,name="Light beam"))
    o.append(circle(x+w*.50,y+h*.57,min(w,h)*.20,p["accent"],opacity=.18,name="Glow"))
    o.append(circle(x+w*.50,y+h*.57,min(w,h)*.12,p["gold"],opacity=.3,name="Glow core"))
    for i in range(6):
        o.append(rect(x+w*.16+i*w*.11,y+h*.74,w*.06,h*.18,p["accent"] if i%2 else p["gold"],opacity=.8,name="Equalizer"))


HERO_SYSTEMS = [hero_editorial, hero_product, hero_architecture, hero_botanical, hero_event]


# ---------------------------------------------------------------------------
# 20 real flyer layout architectures
# ---------------------------------------------------------------------------

def layout_01(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    add_micro_brand(o,p,body_font)
    o.append(textbox(sector.upper(),55,125,420,16,p["accent"],family=body_font,weight="800",char_spacing=120,name="Eyebrow"))
    o.append(textbox(headline,55,158,690,66,p["ink"],family=title_font,weight="700",line_height=.92,name="Headline"))
    o.append(textbox(sub,55,315,590,22,p["ink"],family=body_font,weight="500",name="Subheadline"))
    hero(o,p,55,390,690,410)
    add_cta(o,p,cta,55,840,275,body_font=body_font)
    o.append(textbox(phone,390,852,355,17,p["ink"],family=body_font,weight="700",align="right",name="Contact"))
    o.append(textbox(web,390,880,355,16,p["accent"],family=body_font,align="right",name="Website"))


def layout_02(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["ink"],name="Dark background"))
    hero(o,p,390,0,410,620)
    add_micro_brand(o,p,body_font,dark=True)
    o.append(textbox(sector.upper(),55,165,270,15,p["gold"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    o.append(textbox(headline,55,205,300,60,p["bg"],family=title_font,weight="700",line_height=.92,name="Headline"))
    o.append(textbox(sub,55,430,285,20,p["bg"],family=body_font,line_height=1.25,name="Subheadline"))
    add_cta(o,p,cta,55,515,255,inverse=True,body_font=body_font)
    o.append(rect(55,685,690,280,p["soft"],rx=14,ry=14,name="Info panel"))
    o.append(textbox("WHY CHOOSE US",85,725,250,15,p["accent"],family=body_font,weight="800",char_spacing=90,name="Section label"))
    for i,t in enumerate(["PREMIUM QUALITY","CLEAR PRICING","PERSONAL SERVICE"]):
        y=775+i*54
        o.append(circle(92,y+10,7,p["gold"],name="Bullet"))
        o.append(textbox(t,115,y,280,18,p["ink"],family=body_font,weight="700",name="Benefit"))
    o.append(textbox(phone+"\n"+web,455,770,240,18,p["ink"],family=body_font,weight="600",align="right",line_height=1.5,name="Contact"))


def layout_03(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    hero(o,p,0,0,W,520)
    o.append(rect(0,470,W,630,p["bg"],rx=34,ry=34,name="Lower card"))
    add_micro_brand(o,p,body_font,x=55,y=525)
    o.append(textbox(sector.upper(),55,615,690,15,p["accent"],family=body_font,weight="800",char_spacing=110,name="Eyebrow"))
    o.append(textbox(headline,55,652,690,58,p["ink"],family=title_font,weight="700",line_height=.94,name="Headline"))
    o.append(textbox(sub,55,805,620,20,p["ink"],family=body_font,name="Subheadline"))
    add_cta(o,p,cta,55,875,280,body_font=body_font)
    o.append(textbox(phone+"\n"+web,445,875,300,17,p["ink"],family=body_font,weight="600",align="right",line_height=1.45,name="Contact"))


def layout_04(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(polygon([(0,0),(800,0),(800,650),(0,900)],p["soft"],name="Diagonal field"))
    hero(o,p,335,85,410,390)
    add_micro_brand(o,p,body_font)
    o.append(textbox(headline,55,190,315,64,p["ink"],family=title_font,weight="700",line_height=.9,name="Headline"))
    o.append(textbox(sub,55,420,280,20,p["ink"],family=body_font,line_height=1.3,name="Subheadline"))
    add_offer_badge(o,p,c[4] if "%" in c[4] or "$" in c[4] else c[0].upper(),635,585,68,body_font=body_font)
    o.append(textbox("DESIGNED TO GET ATTENTION",55,760,530,19,p["accent"],family=body_font,weight="800",char_spacing=70,name="Promo line"))
    add_cta(o,p,cta,55,815,270,body_font=body_font)
    o.append(textbox(phone,55,930,300,18,p["ink"],family=body_font,weight="600",name="Contact"))
    o.append(textbox(web,430,930,315,18,p["ink"],family=body_font,weight="600",align="right",name="Website"))


def layout_05(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["ink"],name="Dark background"))
    o.append(rect(32,32,W-64,H-64,"none",stroke=p["gold"],sw=2,name="Gold frame"))
    add_micro_brand(o,p,body_font,x=65,y=70,dark=True)
    o.append(textbox(sector.upper(),65,150,670,15,p["gold"],family=body_font,weight="800",align="center",char_spacing=130,name="Eyebrow"))
    o.append(textbox(headline,80,195,640,64,p["bg"],family=title_font,weight="700",align="center",line_height=.92,name="Headline"))
    hero(o,p,125,395,550,330)
    o.append(textbox(sub,95,775,610,20,p["bg"],family=body_font,align="center",name="Subheadline"))
    add_cta(o,p,cta,260,840,280,inverse=True,body_font=body_font)
    o.append(textbox(phone+"   •   "+web,95,945,610,17,p["gold"],family=body_font,weight="600",align="center",name="Contact"))


def layout_06(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,235,H,p["ink"],name="Sidebar"))
    add_micro_brand(o,p,body_font,x=38,y=55,dark=True)
    o.append(textbox(sector.upper(),38,170,160,15,p["gold"],family=body_font,weight="800",char_spacing=80,name="Eyebrow"))
    o.append(textbox(headline,38,230,165,50,p["bg"],family=title_font,weight="700",line_height=.92,name="Headline"))
    o.append(textbox(sub,38,560,160,17,p["bg"],family=body_font,line_height=1.3,name="Subheadline"))
    o.append(textbox(phone+"\n"+web,38,905,160,16,p["gold"],family=body_font,weight="600",line_height=1.5,name="Contact"))
    hero(o,p,275,80,470,470)
    o.append(textbox("WHAT YOU GET",275,610,420,16,p["accent"],family=body_font,weight="800",char_spacing=100,name="Section label"))
    for i,t in enumerate(["Premium service","Clear next steps","A result that stands out"]):
        y=655+i*64
        o.append(rect(275,y,40,40,p["accent"],rx=12,ry=12,name="Feature icon"))
        o.append(textbox(t,335,y+7,355,19,p["ink"],family=body_font,weight="700",name="Feature"))
    add_cta(o,p,cta,275,875,280,body_font=body_font)


def layout_07(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    add_micro_brand(o,p,body_font,x=300,y=48)
    o.append(textbox(sector.upper(),80,125,640,15,p["accent"],family=body_font,weight="800",align="center",char_spacing=130,name="Eyebrow"))
    o.append(textbox(headline,85,170,630,68,p["ink"],family=title_font,weight="700",align="center",line_height=.9,name="Headline"))
    o.append(textbox(sub,120,340,560,20,p["ink"],family=body_font,align="center",name="Subheadline"))
    hero(o,p,95,410,610,350)
    add_offer_badge(o,p,c[4],640,725,58,body_font=body_font)
    add_cta(o,p,cta,260,810,280,body_font=body_font)
    o.append(textbox(phone+"   •   "+web,95,925,610,17,p["ink"],family=body_font,weight="600",align="center",name="Contact"))


def layout_08(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    hero(o,p,55,65,690,330)
    o.append(rect(55,425,330,475,p["ink"],rx=14,ry=14,name="Text card"))
    o.append(textbox(sector.upper(),85,465,270,14,p["gold"],family=body_font,weight="800",char_spacing=80,name="Eyebrow"))
    o.append(textbox(headline,85,510,265,54,p["bg"],family=title_font,weight="700",line_height=.92,name="Headline"))
    o.append(textbox(sub,85,705,255,18,p["bg"],family=body_font,line_height=1.3,name="Subheadline"))
    add_cta(o,p,cta,85,800,245,inverse=True,body_font=body_font)
    o.append(rect(415,425,330,475,p["soft"],rx=14,ry=14,name="Offer card"))
    o.append(textbox("FEATURED",455,470,250,15,p["accent"],family=body_font,weight="800",char_spacing=100,name="Section label"))
    o.append(textbox(c[4],455,525,250,42,p["ink"],family=title_font,weight="700",line_height=.95,name="Offer"))
    o.append(line(455,650,690,650,p["ink"],sw=1,opacity=.3,name="Divider"))
    o.append(textbox(phone+"\n"+web,455,690,240,18,p["ink"],family=body_font,weight="600",line_height=1.5,name="Contact"))


def layout_09(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,270,p["accent"],name="Top colour band"))
    add_micro_brand(o,p,body_font,x=55,y=55,dark=True)
    o.append(textbox(headline,55,130,690,62,p["bg"],family=title_font,weight="800",line_height=.9,name="Headline"))
    hero(o,p,55,320,690,390)
    o.append(textbox(sector.upper(),55,755,260,15,p["accent"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    o.append(textbox(sub,55,795,480,22,p["ink"],family=body_font,name="Subheadline"))
    add_cta(o,p,cta,55,865,275,body_font=body_font)
    add_offer_badge(o,p,c[4],650,875,70,body_font=body_font)
    o.append(textbox(web,430,980,315,17,p["ink"],family=body_font,weight="600",align="right",name="Website"))


def layout_10(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    add_micro_brand(o,p,body_font)
    o.append(textbox("01",55,145,100,90,p["accent2"],family=title_font,weight="700",name="Big index"))
    o.append(textbox(sector.upper(),175,165,400,15,p["accent"],family=body_font,weight="800",char_spacing=110,name="Eyebrow"))
    o.append(textbox(headline,175,210,570,58,p["ink"],family=title_font,weight="700",line_height=.9,name="Headline"))
    hero(o,p,55,420,690,300)
    o.append(textbox(sub,55,770,460,20,p["ink"],family=body_font,name="Subheadline"))
    add_cta(o,p,cta,55,840,280,body_font=body_font)
    o.append(textbox(phone+"\n"+web,455,835,290,17,p["ink"],family=body_font,weight="600",align="right",line_height=1.5,name="Contact"))


def layout_11(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["soft"],name="Soft background"))
    hero(o,p,0,0,480,H)
    o.append(rect(420,0,380,H,p["bg"],name="Right panel"))
    add_micro_brand(o,p,body_font,x=500,y=70)
    o.append(textbox(sector.upper(),500,180,245,14,p["accent"],family=body_font,weight="800",char_spacing=90,name="Eyebrow"))
    o.append(textbox(headline,500,220,245,55,p["ink"],family=title_font,weight="700",line_height=.9,name="Headline"))
    o.append(textbox(sub,500,535,235,18,p["ink"],family=body_font,line_height=1.35,name="Subheadline"))
    add_cta(o,p,cta,500,655,235,body_font=body_font)
    o.append(line(500,760,735,760,p["ink"],sw=1,opacity=.25,name="Divider"))
    o.append(textbox(c[4],500,800,235,24,p["accent"],family=body_font,weight="800",name="Offer"))
    o.append(textbox(phone+"\n"+web,500,900,235,16,p["ink"],family=body_font,weight="600",line_height=1.5,name="Contact"))


def layout_12(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["ink"],name="Dark background"))
    for i in range(8):
        o.append(circle(85+i*95,90+(i%2)*50,18+(i%3)*8,p["accent"] if i%2 else p["gold"],opacity=.65,name="Top accent"))
    o.append(textbox(sector.upper(),60,170,680,15,p["gold"],family=body_font,weight="800",align="center",char_spacing=120,name="Eyebrow"))
    o.append(textbox(headline,70,215,660,76,p["bg"],family=title_font,weight="800",align="center",line_height=.86,name="Headline"))
    hero(o,p,100,455,600,300)
    o.append(textbox(c[4],100,790,600,34,p["accent"],family=body_font,weight="800",align="center",name="Event detail"))
    add_cta(o,p,cta,260,855,280,inverse=True,body_font=body_font)
    o.append(textbox(phone+"   •   "+web,100,965,600,16,p["gold"],family=body_font,weight="600",align="center",name="Contact"))


def layout_13(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    add_micro_brand(o,p,body_font)
    o.append(rect(55,145,690,180,p["ink"],rx=14,ry=14,name="Headline card"))
    o.append(textbox(headline,85,180,630,58,p["bg"],family=title_font,weight="700",line_height=.92,name="Headline"))
    o.append(textbox(sector.upper(),85,270,500,14,p["gold"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    hero(o,p,55,360,690,330)
    o.append(textbox(sub,55,735,690,20,p["ink"],family=body_font,align="center",name="Subheadline"))
    o.append(rect(55,805,210,120,p["soft"],rx=14,ry=14,name="Info block"))
    o.append(rect(295,805,210,120,p["soft"],rx=14,ry=14,name="Info block"))
    o.append(rect(535,805,210,120,p["soft"],rx=14,ry=14,name="Info block"))
    o.append(textbox(c[4],70,840,180,18,p["accent"],family=body_font,weight="800",align="center",name="Offer"))
    o.append(textbox(phone,310,840,180,18,p["ink"],family=body_font,weight="700",align="center",name="Phone"))
    o.append(textbox(web,550,840,180,18,p["ink"],family=body_font,weight="700",align="center",name="Web"))
    add_cta(o,p,cta,260,955,280,body_font=body_font)


def layout_14(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["bg"],name="Background"))
    o.append(polygon([(0,0),(800,0),(560,1100),(0,1100)],p["ink"],name="Angled half"))
    add_micro_brand(o,p,body_font,x=55,y=55,dark=True)
    o.append(textbox(sector.upper(),55,170,340,15,p["gold"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    o.append(textbox(headline,55,220,365,62,p["bg"],family=title_font,weight="700",line_height=.9,name="Headline"))
    o.append(textbox(sub,55,505,320,18,p["bg"],family=body_font,line_height=1.35,name="Subheadline"))
    add_cta(o,p,cta,55,620,250,inverse=True,body_font=body_font)
    hero(o,p,430,160,315,450)
    add_offer_badge(o,p,c[4],605,730,82,body_font=body_font)
    o.append(textbox(phone+"\n"+web,430,865,315,18,p["ink"],family=body_font,weight="600",align="right",line_height=1.5,name="Contact"))


def layout_15(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    add_micro_brand(o,p,body_font)
    o.append(textbox(sector.upper(),55,135,690,15,p["accent"],family=body_font,weight="800",char_spacing=120,name="Eyebrow"))
    o.append(textbox(headline,55,175,690,66,p["ink"],family=title_font,weight="700",line_height=.9,name="Headline"))
    hero(o,p,55,360,440,430)
    o.append(rect(525,360,220,430,p["soft"],rx=14,ry=14,name="Offer panel"))
    o.append(textbox("SPECIAL",555,405,160,14,p["accent"],family=body_font,weight="800",align="center",char_spacing=90,name="Offer label"))
    o.append(textbox(c[4],550,470,170,42,p["ink"],family=title_font,weight="700",align="center",line_height=.9,name="Offer"))
    o.append(textbox(sub,555,615,160,17,p["ink"],family=body_font,align="center",line_height=1.35,name="Subheadline"))
    add_cta(o,p,cta,535,705,200,body_font=body_font)
    o.append(textbox(phone,55,845,320,18,p["ink"],family=body_font,weight="700",name="Phone"))
    o.append(textbox(web,425,845,320,18,p["ink"],family=body_font,weight="700",align="right",name="Website"))


def layout_16(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    hero(o,p,0,0,W,H)
    o.append(rect(0,0,W,H,p["ink"],opacity=.45,name="Overlay"))
    o.append(rect(55,105,690,790,p["bg"],opacity=.92,rx=18,ry=18,name="Glass card"))
    add_micro_brand(o,p,body_font,x=85,y=145)
    o.append(textbox(sector.upper(),85,245,630,14,p["accent"],family=body_font,weight="800",align="center",char_spacing=110,name="Eyebrow"))
    o.append(textbox(headline,100,300,600,66,p["ink"],family=title_font,weight="700",align="center",line_height=.9,name="Headline"))
    o.append(textbox(sub,120,520,560,20,p["ink"],family=body_font,align="center",name="Subheadline"))
    o.append(textbox(c[4],120,590,560,28,p["accent"],family=body_font,weight="800",align="center",name="Offer"))
    add_cta(o,p,cta,260,670,280,body_font=body_font)
    o.append(textbox(phone+"   •   "+web,120,790,560,17,p["ink"],family=body_font,weight="600",align="center",name="Contact"))


def layout_17(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["soft"],name="Background"))
    hero(o,p,45,45,710,360)
    o.append(rect(45,435,710,620,p["bg"],rx=14,ry=14,name="Content card"))
    add_micro_brand(o,p,body_font,x=80,y=475)
    o.append(textbox(sector.upper(),80,555,610,14,p["accent"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    o.append(textbox(headline,80,595,610,54,p["ink"],family=title_font,weight="700",line_height=.92,name="Headline"))
    o.append(textbox(sub,80,745,430,18,p["ink"],family=body_font,name="Subheadline"))
    o.append(rect(540,740,170,90,p["accent"],rx=12,ry=12,name="Offer tile"))
    o.append(textbox(c[4],555,765,140,18,p["bg"],family=body_font,weight="800",align="center",name="Offer"))
    add_cta(o,p,cta,80,855,275,body_font=body_font)
    o.append(textbox(phone+"\n"+web,425,855,285,17,p["ink"],family=body_font,weight="600",align="right",line_height=1.45,name="Contact"))


def layout_18(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    add_micro_brand(o,p,body_font)
    o.append(textbox(headline,55,145,690,72,p["ink"],family=title_font,weight="800",line_height=.86,name="Headline"))
    o.append(rect(55,340,690,4,p["accent"],name="Accent rule"))
    o.append(textbox(sub,55,380,440,20,p["ink"],family=body_font,name="Subheadline"))
    o.append(textbox(c[4],535,375,210,24,p["accent"],family=body_font,weight="800",align="right",name="Offer"))
    hero(o,p,55,455,690,365)
    o.append(textbox(sector.upper(),55,870,260,14,p["accent"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    add_cta(o,p,cta,55,915,270,body_font=body_font)
    o.append(textbox(phone+" • "+web,365,930,380,16,p["ink"],family=body_font,weight="600",align="right",name="Contact"))


def layout_19(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["ink"],name="Dark background"))
    o.append(textbox(sector.upper(),55,70,690,15,p["gold"],family=body_font,weight="800",char_spacing=120,name="Eyebrow"))
    o.append(textbox(headline,55,120,690,74,p["bg"],family=title_font,weight="800",line_height=.85,name="Headline"))
    o.append(textbox(sub,55,315,470,19,p["bg"],family=body_font,name="Subheadline"))
    add_offer_badge(o,p,c[4],650,345,78,dark=True,body_font=body_font)
    hero(o,p,55,455,690,365)
    add_cta(o,p,cta,55,870,275,inverse=True,body_font=body_font)
    o.append(textbox(phone,390,885,355,17,p["gold"],family=body_font,weight="700",align="right",name="Phone"))
    o.append(textbox(web,390,915,355,16,p["bg"],family=body_font,align="right",name="Website"))


def layout_20(o,p,W,H,c,hero,title_font,body_font):
    sector,headline,sub,cta,phone,web=c
    o.append(rect(0,0,W,H,p["bg"],name="Background"))
    for i in range(5):
        o.append(rect(55+i*140,45,110,8,p["accent"] if i%2==0 else p["gold"],rx=4,ry=4,name="Top rhythm"))
    add_micro_brand(o,p,body_font,x=55,y=90)
    hero(o,p,420,160,325,330)
    o.append(textbox(sector.upper(),55,195,300,14,p["accent"],family=body_font,weight="800",char_spacing=100,name="Eyebrow"))
    o.append(textbox(headline,55,235,320,58,p["ink"],family=title_font,weight="700",line_height=.9,name="Headline"))
    o.append(textbox(sub,55,500,690,20,p["ink"],family=body_font,name="Subheadline"))
    o.append(rect(55,575,690,245,p["soft"],rx=14,ry=14,name="Details panel"))
    o.append(textbox("01",85,610,70,44,p["accent"],family=title_font,weight="700",name="Step"))
    o.append(textbox("Premium presentation",165,615,240,19,p["ink"],family=body_font,weight="700",name="Detail"))
    o.append(textbox("02",85,680,70,44,p["accent"],family=title_font,weight="700",name="Step"))
    o.append(textbox("Clear information hierarchy",165,685,300,19,p["ink"],family=body_font,weight="700",name="Detail"))
    o.append(textbox("03",85,750,70,44,p["accent"],family=title_font,weight="700",name="Step"))
    o.append(textbox(c[4],165,755,300,19,p["ink"],family=body_font,weight="700",name="Offer"))
    add_cta(o,p,cta,55,865,275,body_font=body_font)
    o.append(textbox(phone+"\n"+web,455,860,290,17,p["ink"],family=body_font,weight="600",align="right",line_height=1.5,name="Contact"))


LAYOUTS = [
    layout_01, layout_02, layout_03, layout_04, layout_05,
    layout_06, layout_07, layout_08, layout_09, layout_10,
    layout_11, layout_12, layout_13, layout_14, layout_15,
    layout_16, layout_17, layout_18, layout_19, layout_20,
]


# ---------------------------------------------------------------------------
# SVG preview
# ---------------------------------------------------------------------------

def esc(v):
    return html.escape(str(v), quote=True)


def object_to_svg(o):
    t=o.get("type")
    opacity=o.get("opacity",1)
    if t=="rect":
        return (
            f'<rect x="{o.get("left",0)}" y="{o.get("top",0)}" width="{o.get("width",0)}" '
            f'height="{o.get("height",0)}" rx="{o.get("rx",0)}" ry="{o.get("ry",0)}" '
            f'fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" '
            f'stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}"/>'
        )
    if t=="circle":
        r=o.get("radius",0)
        return (
            f'<circle cx="{o.get("left",0)+r}" cy="{o.get("top",0)+r}" r="{r}" '
            f'fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" '
            f'stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}"/>'
        )
    if t=="ellipse":
        rx=o.get("rx",0); ry=o.get("ry",0)
        cx=o.get("left",0)+rx; cy=o.get("top",0)+ry
        return (
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
            f'fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" '
            f'stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}" '
            f'transform="rotate({o.get("angle",0)} {cx} {cy})"/>'
        )
    if t=="line":
        return (
            f'<line x1="{o.get("x1",0)}" y1="{o.get("y1",0)}" '
            f'x2="{o.get("x2",0)}" y2="{o.get("y2",0)}" '
            f'stroke="{o.get("stroke","#000")}" stroke-width="{o.get("strokeWidth",1)}" '
            f'opacity="{opacity}"/>'
        )
    if t=="polygon":
        pts=" ".join(f'{p["x"]},{p["y"]}' for p in o.get("points",[]))
        return (
            f'<polygon points="{pts}" fill="{o.get("fill","none")}" '
            f'stroke="{o.get("stroke","none") or "none"}" '
            f'stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}"/>'
        )
    if t in {"text","textbox","i-text"}:
        x=o.get("left",0); y=o.get("top",0); w=o.get("width",300)
        size=o.get("fontSize",24); fill=o.get("fill","#000")
        fam=esc(o.get("fontFamily","Arial")); weight=esc(o.get("fontWeight","400"))
        align=o.get("textAlign","left")
        anchor={"left":"start","center":"middle","right":"end"}.get(align,"start")
        tx=x if align=="left" else (x+w/2 if align=="center" else x+w)
        lh=size*o.get("lineHeight",1.05)
        tspans=[]
        for i,txt in enumerate(str(o.get("text","")).split("\n")):
            dy=0 if i==0 else lh
            tspans.append(f'<tspan x="{tx}" dy="{dy}">{esc(txt)}</tspan>')
        return (
            f'<text x="{tx}" y="{y+size}" fill="{fill}" font-family="{fam}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'opacity="{opacity}">{"".join(tspans)}</text>'
        )
    return ""


def svg_for_page(page,W,H):
    body="\n".join(object_to_svg(o) for o in page["objects"] if isinstance(o,dict))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n{body}\n</svg>'


# ---------------------------------------------------------------------------
# Validation / uniqueness
# ---------------------------------------------------------------------------

def structural_signature(objects):
    slim=[]
    for o in objects:
        if not isinstance(o,dict):
            continue
        typ=o.get("type")
        entry={"type":typ}
        for k in (
            "left","top","width","height","radius","rx","ry","angle",
            "fontSize","textAlign","strokeWidth","x1","y1","x2","y2"
        ):
            if k in o:
                v=o[k]
                if isinstance(v,float):
                    v=round(v,2)
                entry[k]=v
        if typ=="polygon":
            entry["points"]=[(round(p["x"],1),round(p["y"],1)) for p in o.get("points",[])]
        slim.append(entry)
    raw=json.dumps(slim,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_template(data):
    if data.get("templateType") != "editable-master":
        raise ValueError("Template is not editable-master JSON.")
    pages=data.get("pages")
    if not isinstance(pages,list) or not pages:
        raise ValueError("Template has no pages.")
    objects=pages[0].get("objects")
    if not isinstance(objects,list) or not objects:
        raise ValueError("Template page has no objects.")
    if any(not isinstance(x,dict) for x in objects):
        raise ValueError("Non-dict object found in page objects.")
    supported={"rect","circle","ellipse","line","polygon","text","textbox","i-text"}
    unknown=sorted({o.get("type") for o in objects if o.get("type") not in supported})
    if unknown:
        raise ValueError(f"Unsupported editor object types: {unknown}")
    editable_text=[
        o for o in objects
        if o.get("type") in {"text","textbox","i-text"}
        and o.get("customerEditable") is True
        and not o.get("locked")
    ]
    if len(editable_text) < 5:
        raise ValueError("Template needs at least 5 editable text fields.")


def build_template(index):
    global _counter
    _counter = index * 10000

    # 20 architecture families × 5 hero systems = 100 materially different structures
    layout_idx=(index-1)//5
    hero_idx=(index-1)%5

    layout=LAYOUTS[layout_idx]
    hero=HERO_SYSTEMS[hero_idx]
    content=SECTORS[index-1]

    p=deepcopy(PALETTES[(index*7 + layout_idx*3 + hero_idx) % len(PALETTES)])
    title_font,body_font=FONT_PAIRS[(layout_idx + hero_idx*2) % len(FONT_PAIRS)]

    objects=[]
    layout(objects,p,SOURCE_W,SOURCE_H,content,hero,title_font,body_font)

    # Tiny layout-specific signature details, not recolour-only variants.
    # These alter geometry, so duplicate checking sees them.
    sig_x=60 + (layout_idx % 5)*8
    sig_y=1040 - (hero_idx*6)
    objects.append(rect(sig_x,sig_y,20+hero_idx*5,4+layout_idx%3,p["gold"],rx=2,ry=2,name="Composition signature"))

    page={
        "name":"Flyer",
        "label":"Flyer",
        "objects":objects,
        "width":SOURCE_W,
        "height":SOURCE_H,
    }
    sig=structural_signature(objects)
    finish=FINISHES[(index-1)%len(FINISHES)]
    sector=content[0]

    data={
        "version":2,
        "generator":GENERATOR_ID,
        "templateType":"editable-master",
        "reconstructed":True,
        "editable":True,
        LIBRARY_FLAG:True,
        LIBRARY_KEY:LIBRARY_VERSION,
        "flyer_code":f"zv-flyer-v2-{index:03d}",
        "document":{"width":SOURCE_W,"height":SOURCE_H},
        "canvas":{"width":SOURCE_W,"height":SOURCE_H},
        "pages":[page],
        "adminPages":[deepcopy(page)],
        "meta":{
            "sector":sector,
            "layout_architecture":layout.__name__,
            "hero_system":hero.__name__,
            "finish":finish,
            "palette":p["name"],
            "structural_signature":sig,
            "composition_key":f"layout-{layout_idx+1:02d}-hero-{hero_idx+1:02d}",
            "uniqueness_rule":"A recolour, copy change or finish change is not counted as a new composition.",
            "source_canvas":"800x1100 portrait",
        }
    }

    name=f"{PREFIX} {index:03d} · {sector} · {finish}"
    return name,data,svg_for_page(page,SOURCE_W,SOURCE_H),sig


# ---------------------------------------------------------------------------
# Django command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Create 100 professional editable flyer templates (20 layouts × 5 hero systems)."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--replace-generated", action="store_true")

    def handle(self,*args,**opts):
        product_id=opts["product_id"]
        count=opts["count"]
        dry=opts["dry_run"]
        replace=opts["replace_generated"]

        if count < 1 or count > 100:
            raise CommandError("--count must be between 1 and 100.")

        try:
            product=Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise CommandError(f"Product {product_id} does not exist.")

        product_w=int(getattr(product,"width",0) or 0)
        product_h=int(getattr(product,"height",0) or 0)
        if product_w and product_h and product_w >= product_h:
            self.stdout.write(self.style.WARNING(
                f"Product {product.id} internal canvas is {product_w}×{product_h} landscape. "
                f"V2 flyer source is {SOURCE_W}×{SOURCE_H} portrait. Configure the product editor "
                "canvas to portrait to avoid non-uniform rescaling in the editor."
            ))

        built=[]
        signatures=set()
        composition_keys=set()

        for i in range(1,count+1):
            name,data,svg,sig=build_template(i)
            validate_template(data)

            key=data["meta"]["composition_key"]
            if key in composition_keys:
                raise CommandError(f"Composition-key duplicate at template {i}: {key}")
            composition_keys.add(key)

            if sig in signatures:
                raise CommandError(f"Structural duplicate detected at template {i}: {name}")
            signatures.add(sig)

            built.append((name,data,svg))
            self.stdout.write(f"{i:03d}: {name} [{key}]")

        self.stdout.write(self.style.SUCCESS(
            f"Validated {len(built)} flyer templates; "
            f"unique composition keys: {len(composition_keys)}; "
            f"unique structural signatures: {len(signatures)}"
        ))
        self.stdout.write(
            "V2 composition system: 20 promotional flyer architectures × 5 editable hero/art systems."
        )
        self.stdout.write(
            "Master: editable JSON Fabric primitives. SVG: preview only. "
            "Colours, literal text and finish labels do not define uniqueness."
        )

        if dry:
            self.stdout.write(self.style.SUCCESS("Dry run complete; database unchanged."))
            return

        with transaction.atomic():
            if replace:
                old=DesignTemplate.objects.filter(
                    product=product,
                    json_data__flyer_library=True,
                ).filter(
                    json_data__flyer_library_version__in=[1,2]
                )
                old_count=old.count()
                old.delete()
                self.stdout.write(f"Removed {old_count} generated Flyer V1/V2 templates for this product.")

            created=0
            updated=0

            for i,(name,data,svg) in enumerate(built,1):
                existing=DesignTemplate.objects.filter(
                    product=product,
                    json_data__flyer_code=data["flyer_code"],
                ).first()

                if existing:
                    existing.name=name
                    existing.json_data=data
                    existing.is_active=True
                    existing.preview.save(
                        f"flyer_v2_{i:03d}.svg",
                        ContentFile(svg.encode("utf-8")),
                        save=False,
                    )
                    existing.save()
                    updated+=1
                else:
                    obj=DesignTemplate(
                        product=product,
                        name=name,
                        json_data=data,
                        is_active=True,
                    )
                    obj.preview.save(
                        f"flyer_v2_{i:03d}.svg",
                        ContentFile(svg.encode("utf-8")),
                        save=False,
                    )
                    obj.save()
                    created+=1

        self.stdout.write(self.style.SUCCESS(
            f"Complete. Created: {created}; Updated: {updated}; "
            f"Product: {product.id} · {product.name}"
        ))
