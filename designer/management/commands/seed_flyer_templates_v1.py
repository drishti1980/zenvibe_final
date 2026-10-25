# designer/management/commands/seed_flyer_templates_v1.py
#
# Creates 100 materially distinct editable flyer templates.
# Master = JSON Fabric-style objects. SVG = preview/sidecar.
#
# Usage:
#   python manage.py seed_flyer_templates_v1 --product-id <FLYER_PRODUCT_ID> --dry-run
#   python manage.py seed_flyer_templates_v1 --product-id <FLYER_PRODUCT_ID> --replace-generated

import hashlib
import json
import math
from copy import deepcopy

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import DesignTemplate, Product


LIBRARY_VERSION = 1
LIBRARY_KEY = "flyer_library_version"
PREFIX = "ZV Flyer"

DEFAULT_W = 800
DEFAULT_H = 1100

_counter = 0


def oid(prefix="obj"):
    global _counter
    _counter += 1
    return f"{prefix}-{_counter:07d}"


def rect(x, y, w, h, fill, *, stroke=None, sw=0, rx=0, ry=0, opacity=1, name="Rectangle"):
    return {
        "id": oid("rect"), "name": name, "type": "rect",
        "left": x, "top": y, "width": w, "height": h,
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "rx": rx, "ry": ry, "opacity": opacity,
        "angle": 0, "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def circle(cx, cy, r, fill, *, stroke=None, sw=0, opacity=1, name="Circle"):
    return {
        "id": oid("circle"), "name": name, "type": "circle",
        "left": cx-r, "top": cy-r, "radius": r,
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "angle": 0,
        "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def ellipse(cx, cy, rx, ry, fill, *, stroke=None, sw=0, opacity=1, angle=0, name="Ellipse"):
    return {
        "id": oid("ellipse"), "name": name, "type": "ellipse",
        "left": cx-rx, "top": cy-ry, "rx": rx, "ry": ry,
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "angle": angle,
        "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def line(x1, y1, x2, y2, stroke, *, sw=2, opacity=1, name="Line"):
    return {
        "id": oid("line"), "name": name, "type": "line",
        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
        "left": min(x1, x2), "top": min(y1, y2),
        "stroke": stroke, "strokeWidth": sw, "opacity": opacity,
        "fill": None, "angle": 0,
        "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def polygon(points, fill, *, stroke=None, sw=0, opacity=1, name="Polygon"):
    return {
        "id": oid("poly"), "name": name, "type": "polygon",
        "points": [{"x": float(x), "y": float(y)} for x, y in points],
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "left": 0, "top": 0, "angle": 0,
        "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def path(d, *, fill="none", stroke="#000000", sw=2, opacity=1, name="Path"):
    return {
        "id": oid("path"), "name": name, "type": "path",
        "path": d, "left": 0, "top": 0,
        "fill": fill, "stroke": stroke, "strokeWidth": sw,
        "opacity": opacity, "angle": 0,
        "scaleX": 1, "scaleY": 1,
        "selectable": True, "evented": True, "locked": False,
    }


def textbox(text, x, y, w, size, fill, *, family="Inter", weight="400",
            align="left", line_height=1.05, name="Text", editable=True,
            char_spacing=0, style="normal", angle=0):
    return {
        "id": oid("text"), "name": name, "type": "textbox",
        "text": text, "left": x, "top": y, "width": w,
        "fontSize": size, "fill": fill,
        "fontFamily": family, "font": family,
        "fontWeight": weight, "fontStyle": style,
        "textAlign": align, "lineHeight": line_height,
        "charSpacing": char_spacing,
        "scaleX": 1, "scaleY": 1, "angle": angle,
        "opacity": 1,
        "customerEditable": editable,
        "selectable": True, "evented": True, "locked": False,
        "fieldType": "flyer-text",
    }


PALETTES = [
    {"name":"Ivory Navy","bg":"#F8F5EF","ink":"#10223A","accent":"#3867D6","accent2":"#9FB8E8","gold":"#C6A15B"},
    {"name":"Obsidian Gold","bg":"#0D0D0F","ink":"#F5F1E8","accent":"#C9A45C","accent2":"#6F5733","gold":"#E0BD73"},
    {"name":"Emerald Cream","bg":"#F3F0E7","ink":"#173F35","accent":"#2E6A56","accent2":"#8FB8A1","gold":"#B89555"},
    {"name":"Pearl Blue","bg":"#F6F8FB","ink":"#152B45","accent":"#2D7DD2","accent2":"#BBD7F3","gold":"#C8A463"},
    {"name":"Black Neon","bg":"#0B0D12","ink":"#F5F7FA","accent":"#24D3EE","accent2":"#865CFF","gold":"#D6B35A"},
    {"name":"Terracotta","bg":"#F3E8DF","ink":"#4A2B22","accent":"#B75C3F","accent2":"#DFAD92","gold":"#B98A4C"},
    {"name":"Blush Wine","bg":"#F8EDEF","ink":"#5A1E37","accent":"#B73C6C","accent2":"#E7B5C5","gold":"#C7A25D"},
    {"name":"Cobalt White","bg":"#F4F6FA","ink":"#0B2C63","accent":"#1746D1","accent2":"#94B3FF","gold":"#C8A055"},
    {"name":"Sage Sand","bg":"#F4F1E8","ink":"#34463D","accent":"#7C967F","accent2":"#C5CFBA","gold":"#B89A62"},
    {"name":"Ruby Champagne","bg":"#2A0F17","ink":"#FFF7EF","accent":"#A52E4C","accent2":"#D996AA","gold":"#E0B76A"},
]

FONT_PAIRS = [
    ("Bodoni Moda","Inter"), ("Playfair Display","Inter"),
    ("Cormorant Garamond","Montserrat"), ("DM Serif Display","Inter"),
    ("Libre Baskerville","Montserrat"), ("Poppins","Inter"),
    ("Montserrat","Inter"), ("Oswald","Inter"), ("Raleway","Inter"),
    ("Cinzel","Montserrat"),
]

SECTORS = [
    ("Business Solutions", "SMARTER BUSINESS.\nSTRONGER RESULTS.", "Strategy â€¢ Systems â€¢ Growth", "BOOK A CONSULTATION"),
    ("Luxury Branding", "WE BUILD\nICONIC BRANDS", "Identity â€¢ Direction â€¢ Digital", "DISCOVER THE STUDIO"),
    ("Digital Marketing", "GROW FASTER\nONLINE", "SEO â€¢ Social â€¢ Performance", "START YOUR CAMPAIGN"),
    ("Creative Agency", "IDEAS THAT\nMOVE PEOPLE", "Brand â€¢ Content â€¢ Experience", "LET'S CREATE"),
    ("Real Estate", "FIND A PLACE\nTO CALL HOME", "Premium properties. Personal service.", "VIEW PROPERTIES"),
    ("Interior Design", "DESIGNED FOR\nBETTER LIVING", "Interiors â€¢ Styling â€¢ Space Planning", "BOOK A CONSULT"),
    ("Restaurant", "TASTE SOMETHING\nUNFORGETTABLE", "Seasonal menu â€¢ Local produce", "RESERVE A TABLE"),
    ("Cafe", "GOOD COFFEE.\nGOOD DAYS.", "Roasted daily â€¢ Made with care", "VISIT TODAY"),
    ("Bakery", "FRESHLY BAKED\nEVERY MORNING", "Pastries â€¢ Cakes â€¢ Artisan bread", "ORDER NOW"),
    ("Healthy Food", "EAT BRIGHT.\nFEEL BETTER.", "Fresh bowls â€¢ Honest ingredients", "VIEW MENU"),
    ("Fitness", "BUILD YOUR\nSTRONGEST SELF", "Strength â€¢ Conditioning â€¢ Coaching", "JOIN TODAY"),
    ("Yoga", "MOVE. BREATHE.\nRESET.", "Yoga â€¢ Pilates â€¢ Mindfulness", "BOOK A CLASS"),
    ("Wellness", "YOUR WELLNESS\nMATTERS", "Holistic care for modern life", "LEARN MORE"),
    ("Beauty", "GLOW WITH\nCONFIDENCE", "Skin â€¢ Beauty â€¢ Self-care", "BOOK NOW"),
    ("Hair Studio", "YOUR HAIR.\nYOUR SIGNATURE.", "Cut â€¢ Colour â€¢ Styling", "BOOK AN APPOINTMENT"),
    ("Fashion", "THE NEW\nCOLLECTION", "Modern essentials â€¢ Limited release", "SHOP NOW"),
    ("Jewellery", "MADE TO\nBE REMEMBERED", "Fine jewellery â€¢ Timeless design", "EXPLORE"),
    ("Watches", "TIME, REFINED.", "Precision â€¢ Craft â€¢ Character", "DISCOVER"),
    ("Travel", "GO SOMEWHERE\nBEAUTIFUL", "Curated escapes â€¢ Tailored journeys", "PLAN YOUR TRIP"),
    ("Adventure", "ADVENTURE\nAWAITS", "Explore beyond the ordinary", "START EXPLORING"),
    ("Conference", "BUSINESS\nCONFERENCE 2026", "Ideas â€¢ Leaders â€¢ Opportunity", "REGISTER NOW"),
    ("Annual Summit", "THE FUTURE\nSTARTS HERE", "Connect â€¢ Learn â€¢ Lead", "GET TICKETS"),
    ("Education", "LEARN TODAY.\nLEAD TOMORROW.", "Programs for ambitious minds", "APPLY NOW"),
    ("Online Course", "LEARN FROM\nANYWHERE", "Flexible â€¢ Practical â€¢ Career-ready", "ENROL TODAY"),
    ("Music Festival", "LIVE LOUD.\nFEEL EVERYTHING.", "One night â€¢ Multiple stages", "GET TICKETS"),
    ("Night Party", "AFTER DARK", "Music â€¢ Lights â€¢ Late-night energy", "RSVP NOW"),
    ("Live Concert", "LIVE IN\nCONCERT", "One stage. One unforgettable night.", "GET TICKETS"),
    ("Art Exhibition", "NEW\nPERSPECTIVES", "Contemporary art exhibition", "VIEW EXHIBITION"),
    ("Theatre", "THE NIGHT\nBEGINS HERE", "A new live production", "BOOK SEATS"),
    ("Book Fair", "READ.\nDISCOVER.\nCONNECT.", "Authors â€¢ Talks â€¢ New releases", "JOIN US"),
    ("Science Expo", "IMAGINE\nWHAT'S NEXT", "Science â€¢ Robotics â€¢ Discovery", "REGISTER"),
    ("Technology", "BUILD THE\nFUTURE", "Cloud â€¢ AI â€¢ Digital transformation", "TALK TO US"),
    ("Car Expo", "ENGINEERED\nTO EXCITE", "Performance â€¢ Design â€¢ Innovation", "SEE THE RANGE"),
    ("Auto Service", "DRIVE WITH\nCONFIDENCE", "Service â€¢ Repairs â€¢ Diagnostics", "BOOK SERVICE"),
    ("Car Rental", "YOUR ROAD.\nYOUR WAY.", "Flexible rental â€¢ Easy booking", "BOOK A CAR"),
    ("Investment", "BUILD WEALTH\nWITH CLARITY", "Property â€¢ Strategy â€¢ Growth", "SPEAK TO US"),
    ("Financial Planning", "PLAN WITH\nCONFIDENCE", "Goals â€¢ Advice â€¢ Future", "BOOK A MEETING"),
    ("Insurance", "PROTECTION FOR\nWHAT MATTERS", "Personal â€¢ Family â€¢ Business", "GET A QUOTE"),
    ("Law", "CLEAR ADVICE.\nSTRONG ADVOCACY.", "Commercial â€¢ Property â€¢ Disputes", "CONTACT US"),
    ("Medical", "CARE YOU\nCAN TRUST", "Professional care â€¢ Modern facilities", "BOOK NOW"),
    ("Dental", "SMILE WITH\nCONFIDENCE", "General â€¢ Cosmetic â€¢ Preventive", "BOOK A VISIT"),
    ("Pet Care", "HAPPY PETS.\nHAPPY HOMES.", "Grooming â€¢ Wellness â€¢ Care", "BOOK TODAY"),
    ("Veterinary", "COMPASSIONATE\nPET CARE", "Health â€¢ Prevention â€¢ Support", "BOOK A VISIT"),
    ("Pharmacy", "HEALTHCARE,\nCLOSE TO HOME", "Advice â€¢ Essentials â€¢ Wellness", "VISIT US"),
    ("Home Cleaning", "A CLEANER\nHOME AWAITS", "Reliable â€¢ Detailed â€¢ Trusted", "GET A QUOTE"),
    ("Laundry", "FRESH. CLEAN.\nREADY.", "Wash â€¢ Fold â€¢ Dry cleaning", "BOOK PICKUP"),
    ("Moving", "MOVE WITHOUT\nTHE STRESS", "Local â€¢ Interstate â€¢ Packing", "GET A QUOTE"),
    ("Pest Control", "PESTS OUT.\nPEACE IN.", "Safe â€¢ Fast â€¢ Professional", "BOOK SERVICE"),
    ("Repair", "FIXED RIGHT.\nFIRST TIME.", "Home â€¢ Office â€¢ Maintenance", "CALL TODAY"),
    ("Electrical", "POWERING\nYOUR SPACE", "Residential â€¢ Commercial", "BOOK AN ELECTRICIAN"),
    ("Plumbing", "PLUMBING\nDONE RIGHT", "Repairs â€¢ Installations â€¢ Emergency", "CALL NOW"),
    ("Landscaping", "OUTDOORS,\nBEAUTIFULLY DONE", "Design â€¢ Build â€¢ Maintain", "GET A QUOTE"),
    ("IT Support", "TECH SUPPORT\nTHAT WORKS", "Support â€¢ Cloud â€¢ Security", "TALK TO US"),
    ("Cyber Security", "SECURE YOUR\nDIGITAL WORLD", "Protect â€¢ Detect â€¢ Respond", "GET SECURE"),
    ("Mobile App", "BUILD THE APP\nPEOPLE LOVE", "iOS â€¢ Android â€¢ Product design", "START A PROJECT"),
    ("UI UX", "DESIGN BETTER\nEXPERIENCES", "Research â€¢ UX â€¢ Product design", "WORK WITH US"),
    ("Web Development", "WEBSITES THAT\nWORK HARDER", "Design â€¢ Build â€¢ Optimise", "START A PROJECT"),
    ("Software", "SOFTWARE FOR\nREAL BUSINESS", "Platforms â€¢ Automation â€¢ APIs", "TALK TO US"),
    ("Cloud", "MOVE TO\nTHE CLOUD", "Modernise â€¢ Scale â€¢ Secure", "GET STARTED"),
    ("Data Analytics", "TURN DATA\nINTO ACTION", "Insights â€¢ Dashboards â€¢ Decisions", "SEE HOW"),
    ("AI Solutions", "AI FOR\nREAL WORK", "Automation â€¢ Intelligence â€¢ Scale", "EXPLORE AI"),
    ("Startup", "TURN THE IDEA\nINTO MOMENTUM", "Strategy â€¢ Product â€¢ Growth", "LET'S BUILD"),
    ("Co-working", "WORK BETTER.\nTOGETHER.", "Flexible desks â€¢ Meeting rooms", "BOOK A TOUR"),
    ("Freelance", "BUILD YOUR\nOWN PATH", "Creative services for growing brands", "LET'S WORK"),
    ("Wedding Services", "YOUR DAY,\nBEAUTIFULLY DONE", "Planning â€¢ Styling â€¢ Coordination", "ENQUIRE"),
    ("Event Planning", "MOMENTS MADE\nMEMORABLE", "Corporate â€¢ Social â€¢ Luxury events", "PLAN YOUR EVENT"),
    ("Birthday Party", "LET'S\nCELEBRATE", "Food â€¢ Music â€¢ Good times", "RSVP"),
    ("Baby Shower", "A LITTLE LOVE\nIS ON THE WAY", "Join us for a beautiful celebration", "RSVP"),
    ("Graduation", "CLASS OF 2026", "Celebrate the achievement", "JOIN THE CELEBRATION"),
    ("Corporate Event", "AN EVENING OF\nCONNECTION", "Clients â€¢ Team â€¢ Partners", "RSVP"),
    ("Christmas Offer", "SEASONAL\nSPECIAL", "Limited-time festive offer", "SHOP THE OFFER"),
    ("New Year", "HELLO 2027", "Celebrate â€¢ Connect â€¢ Begin again", "JOIN US"),
    ("Valentine", "MADE WITH\nLOVE", "A special offer for someone special", "SHOP NOW"),
    ("Mothers Day", "FOR SOMEONE\nEXTRAORDINARY", "Thoughtful gifts â€¢ Limited collection", "SHOP GIFTS"),
    ("Black Friday", "BLACK FRIDAY\nEVENT", "Our biggest offer of the season", "SHOP NOW"),
    ("Mega Sale", "THE BIG\nSALE", "Limited time â€¢ Selected lines", "SHOP SALE"),
    ("Special Offer", "SPECIAL\nOFFER", "Premium value â€¢ Limited availability", "CLAIM OFFER"),
    ("Big Discount", "SAVE MORE\nTODAY", "Selected products â€¢ While stocks last", "SHOP NOW"),
    ("Super Sale", "SUPER\nSALE", "Fresh offers â€¢ Limited time", "SHOP SALE"),
    ("Weekend Offer", "WEEKEND\nONLY", "A limited weekend release", "SHOP NOW"),
    ("Limited Time", "DON'T MISS\nOUT", "Available for a limited time", "GET THE OFFER"),
    ("Clearance", "FINAL\nCLEARANCE", "Last pieces â€¢ Final prices", "SHOP CLEARANCE"),
    ("Hot Deals", "HOT\nDEALS", "New deals â€¢ Limited quantities", "SHOP DEALS"),
    ("Retail", "NEW SEASON.\nNEW ENERGY.", "Fresh arrivals in store now", "SHOP NOW"),
    ("Architecture", "SPACES THAT\nSHAPE LIFE", "Architecture â€¢ Planning â€¢ Interiors", "VIEW PROJECTS"),
    ("Luxury Living", "LIVE\nBEAUTIFULLY", "Premium interiors â€¢ Refined living", "DISCOVER"),
    ("Photography", "STORIES IN\nEVERY FRAME", "Portrait â€¢ Event â€¢ Commercial", "BOOK A SHOOT"),
    ("Consulting", "CLARITY FOR\nWHAT'S NEXT", "Strategy â€¢ Transformation â€¢ Growth", "BOOK A CALL"),
    ("Recruitment", "FIND THE\nRIGHT PEOPLE", "Talent â€¢ Search â€¢ Workforce", "TALK TO US"),
    ("Logistics", "MOVE SMARTER.\nDELIVER FASTER.", "Freight â€¢ Warehousing â€¢ Fulfilment", "GET A QUOTE"),
    ("Construction", "BUILT WITH\nPURPOSE", "Commercial â€¢ Residential â€¢ Fitout", "START A PROJECT"),
    ("Solar", "POWER YOUR\nFUTURE", "Solar â€¢ Battery â€¢ Energy", "GET A QUOTE"),
    ("Sustainability", "BETTER FOR\nBUSINESS & PLANET", "Strategy â€¢ Reporting â€¢ Impact", "LEARN MORE"),
    ("Hotel", "STAY\nBEAUTIFULLY", "Rooms â€¢ Dining â€¢ Experiences", "BOOK YOUR STAY"),
    ("Spa", "TIME TO\nUNWIND", "Massage â€¢ Skin â€¢ Wellness", "BOOK YOUR ESCAPE"),
    ("Wine Dinner", "AN EVENING OF\nFINE TASTE", "Curated menu â€¢ Elegant atmosphere", "RESERVE"),
    ("Community", "COME\nTOGETHER", "Local people â€¢ Shared ideas", "JOIN US"),
    ("Charity", "MAKE AN\nIMPACT", "Support â€¢ Give â€¢ Change", "DONATE"),
    ("Workshop", "LEARN BY\nDOING", "Practical skills â€¢ Expert guidance", "BOOK YOUR PLACE"),
]

def leaf_branch(x, y, length, color, secondary, *, flip=1, density=7):
    out = [line(x, y, x + length * flip, y + length * 0.18, color, sw=3, opacity=.85, name="Editable stem")]
    for i in range(density):
        t = (i+1)/(density+1)
        px = x + length*t*flip
        py = y + length*.18*t
        side = -1 if i % 2 == 0 else 1
        out.append(ellipse(px, py + side*18, 18, 8, secondary, angle=side*32*flip, opacity=.92, name="Editable leaf"))
    return out


def skyline_art(x, y, w, h, p):
    out = []
    widths = [0.08,0.12,0.07,0.15,0.09,0.11]
    cx = x
    for i, fw in enumerate(widths):
        bw = w*fw
        bh = h*(.35 + (i%4)*.13)
        out.append(rect(cx, y+h-bh, bw, bh, p["accent"] if i%2==0 else p["ink"], opacity=.9, name="Editable building"))
        cx += bw + 8
    return out


def abstract_ribbons(x, y, w, h, p):
    return [
        polygon([(x,y+h*.15),(x+w*.65,y),(x+w,y+h*.32),(x+w*.38,y+h*.6)],p["accent"],opacity=.92,name="Editable ribbon"),
        polygon([(x+w*.15,y+h),(x+w*.48,y+h*.3),(x+w,y+h*.52),(x+w*.73,y+h)],p["accent2"],opacity=.62,name="Editable ribbon"),
        line(x+w*.08,y+h*.86,x+w*.9,y+h*.15,p["gold"],sw=3,opacity=.85,name="Gold accent"),
    ]


def botanical_art(x, y, w, h, p):
    out = []
    out += leaf_branch(x+w*.1,y+h*.1,w*.58,p["ink"],p["accent2"],flip=1,density=8)
    out += leaf_branch(x+w*.9,y+h*.7,w*.5,p["accent"],p["accent2"],flip=-1,density=7)
    out.append(circle(x+w*.2,y+h*.72,w*.11,p["accent"],opacity=.12,name="Soft botanical orb"))
    return out


def tech_orbits(x, y, w, h, p):
    out=[]
    cx,cy=x+w*.52,y+h*.48
    for rr in [w*.12,w*.2,w*.29]:
        out.append(ellipse(cx,cy,rr,rr*.55,"none",stroke=p["accent2"],sw=2,opacity=.8,name="Editable orbit"))
    for a in range(0,360,45):
        rad=math.radians(a)
        out.append(circle(cx+math.cos(rad)*w*.27,cy+math.sin(rad)*h*.15,7,p["accent"],name="Editable node"))
    out.append(circle(cx,cy,26,p["accent"],name="Editable core"))
    return out


def luxury_arch(x, y, w, h, p):
    out=[
        rect(x+16,y+16,w-32,h-32,"none",stroke=p["gold"],sw=2,name="Gold border"),
        path(f"M {x+w*.18} {y+h*.75} L {x+w*.18} {y+h*.3} Q {x+w*.5} {y-h*.02} {x+w*.82} {y+h*.3} L {x+w*.82} {y+h*.75}",
             fill="none",stroke=p["gold"],sw=3,name="Editable luxury arch")
    ]
    out += leaf_branch(x+w*.12,y+h*.12,w*.32,p["gold"],p["accent2"],flip=1,density=5)
    out += leaf_branch(x+w*.88,y+h*.72,w*.3,p["gold"],p["accent2"],flip=-1,density=5)
    return out


def product_spotlight(x,y,w,h,p):
    return [
        ellipse(x+w*.5,y+h*.76,w*.3,h*.06,p["ink"],opacity=.08,name="Editable shadow"),
        rect(x+w*.22,y+h*.2,w*.56,h*.52,p["accent2"],rx=24,ry=24,opacity=.42,name="Product backdrop"),
        rect(x+w*.34,y+h*.12,w*.32,h*.58,p["ink"],rx=26,ry=26,opacity=.92,name="Product silhouette"),
        line(x+w*.4,y+h*.22,x+w*.6,y+h*.22,p["gold"],sw=3,name="Product detail"),
    ]


def mountain_art(x,y,w,h,p):
    return [
        polygon([(x,y+h*.8),(x+w*.27,y+h*.22),(x+w*.44,y+h*.58),(x+w*.62,y+h*.12),(x+w,y+h*.8)],p["accent2"],opacity=.68,name="Editable mountains"),
        polygon([(x+w*.08,y+h*.8),(x+w*.36,y+h*.4),(x+w*.5,y+h*.72),(x+w*.78,y+h*.3),(x+w,y+h*.8)],p["accent"],opacity=.7,name="Editable foreground mountains"),
        circle(x+w*.8,y+h*.18,34,p["gold"],opacity=.88,name="Sun"),
    ]


def festival_art(x,y,w,h,p):
    out=[]
    for i in range(7):
        xx=x+w*(.08+i*.14)
        out.append(polygon([(xx,y+h),(xx+w*.06,y+h),(xx+w*.03,y+h*(.32+(i%3)*.12))],p["accent"] if i%2 else p["accent2"],opacity=.75,name="Editable light beam"))
    for i in range(18):
        xx=x+w*((i*37)%100)/100
        yy=y+h*((i*61)%65)/100
        out.append(circle(xx,yy,3+(i%4),p["gold"] if i%3==0 else p["accent2"],opacity=.8,name="Editable spark"))
    return out


def service_badges(x,y,w,h,p):
    out=[]
    for i in range(4):
        cx=x+w*(.16+i*.22); cy=y+h*.52
        out.append(circle(cx,cy,34,p["accent2"],opacity=.25,name="Editable service badge"))
        out.append(circle(cx,cy,17,p["accent"],opacity=.9,name="Editable service icon"))
        out.append(line(cx-10,cy,cx+10,cy,p["bg"],sw=2))
        out.append(line(cx,cy-10,cx,cy+10,p["bg"],sw=2))
    return out


def sale_burst(x,y,w,h,p):
    pts=[]
    cx,cy=x+w*.5,y+h*.45
    for i in range(24):
        a=math.radians(i*15-90)
        r=(w*.28 if i%2==0 else w*.19)
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r))
    out=[polygon(pts,p["accent"],opacity=.96,name="Editable sale burst")]
    for i in range(10):
        out.append(circle(x+w*((i*23)%100)/100,y+h*((i*41)%100)/100,5+(i%3)*2,p["gold"],opacity=.7,name="Editable confetti"))
    return out


ART_SYSTEMS = [skyline_art, abstract_ribbons, botanical_art, tech_orbits, luxury_arch, product_spotlight, mountain_art, festival_art, service_badges, sale_burst]


def add_footer(objects, p, W, H, cta):
    objects.append(line(60,H-98,W-60,H-98,p["accent2"],sw=1,opacity=.7))
    objects.append(textbox("zenvibe.example  â€¢  hello@example.com  â€¢  +61 400 000 000",60,H-74,W-120,15,p["ink"],family="Inter",weight="500",align="center",char_spacing=35,name="Editable footer"))
    objects.append(rect(W-260,H-145,210,54,p["accent"],rx=27,ry=27,name="Editable CTA button"))
    objects.append(textbox(cta, W-250,H-132,190,28,p["bg"],family="Inter",weight="700",align="center",name="Editable CTA"))


def layout_editorial(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects += art(430,60,320,520,p)
    objects.append(textbox("ZENVIBE STUDIO",60,60,300,18,p["accent"],family=body_font,weight="700",char_spacing=180,name="Eyebrow"))
    objects.append(textbox(headline,60,145,430,78,p["ink"],family=title_font,weight="700",line_height=.92,name="Headline"))
    objects.append(textbox(sub,62,390,360,24,p["ink"],family=body_font,line_height=1.35,name="Subheading"))
    objects.append(line(60,485,300,485,p["gold"],sw=3,name="Gold rule"))
    objects.append(textbox("Premium solutions, designed with clarity and purpose.",60,520,350,20,p["ink"],family=body_font,line_height=1.5,name="Body"))
    add_footer(objects,p,W,H,cta)


def layout_split(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(rect(W*.52,0,W*.48,H,p["ink"],name="Split panel"))
    objects += art(W*.5,0,W*.5,H*.68,{**p,"ink":p["bg"]})
    objects.append(textbox(headline,55,160,W*.42,66,p["ink"],family=title_font,weight="700",line_height=.95,name="Headline"))
    objects.append(textbox(sub,58,365,W*.38,22,p["ink"],family=body_font,name="Subheading"))
    objects.append(textbox("01",W*.72,745,100,92,p["gold"],family=title_font,weight="700",align="center",name="Edition number"))
    objects.append(textbox("MODERN\nEDITION",W*.64,845,230,22,p["bg"],family=body_font,weight="700",align="center",char_spacing=120,name="Edition label"))
    add_footer(objects,p,W,H,cta)


def layout_tophero(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(rect(0,0,W,500,p["ink"],name="Hero panel"))
    objects += art(40,40,W-80,410,{**p,"ink":p["bg"]})
    objects.append(textbox(headline,70,560,W-140,70,p["ink"],family=title_font,weight="700",align="center",line_height=.94,name="Headline"))
    objects.append(textbox(sub,130,745,W-260,23,p["ink"],family=body_font,align="center",name="Subheading"))
    objects.append(line(240,820,W-240,820,p["gold"],sw=3,name="Gold divider"))
    add_footer(objects,p,W,H,cta)


def layout_diagonal(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(polygon([(0,0),(W,0),(W,500),(0,720)],p["ink"],name="Diagonal panel"))
    objects += art(360,45,380,430,{**p,"ink":p["bg"]})
    objects.append(textbox(headline,60,120,460,72,p["bg"],family=title_font,weight="700",line_height=.94,name="Headline"))
    objects.append(textbox(sub,62,362,360,22,p["bg"],family=body_font,name="Subheading"))
    objects.append(textbox("DESIGNED\nFOR IMPACT",60,760,330,32,p["ink"],family=body_font,weight="700",char_spacing=60,name="Feature statement"))
    objects.append(line(60,875,350,875,p["accent"],sw=6,name="Accent bar"))
    add_footer(objects,p,W,H,cta)


def layout_frame(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(rect(34,34,W-68,H-68,"none",stroke=p["gold"],sw=2,name="Outer frame"))
    objects.append(rect(52,52,W-104,H-104,"none",stroke=p["accent2"],sw=1,name="Inner frame"))
    objects += art(120,70,W-240,360,p)
    objects.append(textbox(headline,90,470,W-180,68,p["ink"],family=title_font,weight="700",align="center",line_height=.95,name="Headline"))
    objects.append(textbox(sub,130,665,W-260,22,p["ink"],family=body_font,align="center",name="Subheading"))
    objects.append(textbox("EST. 2026",260,765,W-520,17,p["accent"],family=body_font,weight="700",align="center",char_spacing=180,name="Small label"))
    add_footer(objects,p,W,H,cta)


def layout_sidebar(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(rect(0,0,150,H,p["ink"],name="Side bar"))
    objects.append(textbox("ZENVIBE",35,820,80,24,p["bg"],family=body_font,weight="700",angle=-90,char_spacing=180,name="Vertical brand"))
    objects += art(205,70,W-255,400,p)
    objects.append(textbox(headline,205,535,W-260,70,p["ink"],family=title_font,weight="700",line_height=.94,name="Headline"))
    objects.append(textbox(sub,205,750,W-270,22,p["ink"],family=body_font,name="Subheading"))
    add_footer(objects,p,W,H,cta)


def layout_centered(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(circle(W*.5,290,215,p["accent2"],opacity=.16,name="Soft halo"))
    objects += art(180,90,W-360,390,p)
    objects.append(textbox(headline,85,520,W-170,74,p["ink"],family=title_font,weight="700",align="center",line_height=.93,name="Headline"))
    objects.append(textbox(sub,145,725,W-290,22,p["ink"],family=body_font,align="center",name="Subheading"))
    objects.append(line(280,805,W-280,805,p["gold"],sw=3,name="Gold rule"))
    add_footer(objects,p,W,H,cta)


def layout_cards(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(textbox(headline,55,65,W-110,68,p["ink"],family=title_font,weight="700",line_height=.94,name="Headline"))
    objects.append(textbox(sub,58,245,W-116,22,p["ink"],family=body_font,name="Subheading"))
    objects += art(400,35,340,250,p)
    for i,(lab,val) in enumerate([("01","PLAN"),("02","CREATE"),("03","GROW")]):
        xx=55+i*235
        objects.append(rect(xx,370,205,270,p["ink"] if i==1 else p["accent2"],rx=18,ry=18,opacity=.96 if i==1 else .55,name="Editable feature card"))
        objects.append(textbox(lab,xx+20,395,70,18,p["gold"] if i==1 else p["accent"],family=body_font,weight="700",name="Card number"))
        objects.append(textbox(val,xx+20,505,160,28,p["bg"] if i==1 else p["ink"],family=body_font,weight="700",name="Card label"))
    objects.append(textbox("A clean, modern framework built around your next move.",55,700,W-110,25,p["ink"],family=body_font,align="center",name="Body"))
    add_footer(objects,p,W,H,cta)


def layout_bigtype(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["ink"],name="Background"))
    objects += art(410,570,340,390,{**p,"bg":p["ink"],"ink":p["bg"]})
    words=headline.replace("\n"," ").split(" ")
    first=words[0]; rest=" ".join(words[1:])
    objects.append(textbox(first,45,75,W-90,128,p["accent"],family=title_font,weight="700",line_height=.85,name="Big word"))
    objects.append(textbox(rest,50,230,W-100,72,p["bg"],family=title_font,weight="700",line_height=.9,name="Headline"))
    objects.append(textbox(sub,55,470,420,23,p["bg"],family=body_font,name="Subheading"))
    objects.append(line(55,545,350,545,p["gold"],sw=4,name="Gold rule"))
    objects.append(rect(50,H-150,230,58,p["accent"],rx=29,ry=29,name="CTA button"))
    objects.append(textbox(cta,65,H-136,200,22,p["ink"],family=body_font,weight="700",align="center",name="CTA"))
    objects.append(textbox("zenvibe.example  â€¢  +61 400 000 000",340,H-132,390,16,p["bg"],family=body_font,align="right",name="Footer"))


def layout_luxury(objects,p,W,H,headline,sub,cta,art,title_font,body_font):
    objects.append(rect(0,0,W,H,p["bg"],name="Background"))
    objects.append(rect(0,0,W,185,p["ink"],name="Luxury header"))
    objects.append(textbox("PRIVATE EDITION",70,68,W-140,16,p["gold"],family=body_font,weight="700",align="center",char_spacing=240,name="Edition"))
    objects += art(145,220,W-290,390,p)
    objects.append(textbox(headline,80,620,W-160,66,p["ink"],family=title_font,weight="700",align="center",line_height=.94,name="Headline"))
    objects.append(textbox(sub,140,805,W-280,21,p["ink"],family=body_font,align="center",name="Subheading"))
    objects.append(line(250,870,W-250,870,p["gold"],sw=2,name="Gold rule"))
    add_footer(objects,p,W,H,cta)


LAYOUTS = [layout_editorial, layout_split, layout_tophero, layout_diagonal, layout_frame, layout_sidebar, layout_centered, layout_cards, layout_bigtype, layout_luxury]


def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def object_to_svg(o):
    t=o.get("type")
    opacity=o.get("opacity",1)
    if t=="rect":
        return f'<rect x="{o.get("left",0)}" y="{o.get("top",0)}" width="{o.get("width",0)}" height="{o.get("height",0)}" rx="{o.get("rx",0)}" ry="{o.get("ry",0)}" fill="{o.get("fill","none") or "none"}" stroke="{o.get("stroke","none") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}"/>'
    if t=="circle":
        r=o.get("radius",0); cx=o.get("left",0)+r; cy=o.get("top",0)+r
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}"/>'
    if t=="ellipse":
        rx=o.get("rx",0); ry=o.get("ry",0); cx=o.get("left",0)+rx; cy=o.get("top",0)+ry
        angle=o.get("angle",0)
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}" transform="rotate({angle} {cx} {cy})"/>'
    if t=="line":
        return f'<line x1="{o.get("x1",0)}" y1="{o.get("y1",0)}" x2="{o.get("x2",0)}" y2="{o.get("y2",0)}" stroke="{o.get("stroke","#000")}" stroke-width="{o.get("strokeWidth",1)}" opacity="{opacity}"/>'
    if t=="polygon":
        pts=" ".join(f'{p["x"]},{p["y"]}' for p in o.get("points",[]))
        return f'<polygon points="{pts}" fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" stroke-width="{o.get("strokeWidth",0)}" opacity="{opacity}"/>'
    if t=="path":
        return f'<path d="{esc(o.get("path",""))}" fill="{o.get("fill","none")}" stroke="{o.get("stroke","none") or "none"}" stroke-width="{o.get("strokeWidth",1)}" opacity="{opacity}"/>'
    if t in {"text","textbox","i-text"}:
        x=o.get("left",0); y=o.get("top",0); w=o.get("width",300)
        size=o.get("fontSize",24); fill=o.get("fill","#000"); fam=esc(o.get("fontFamily","Arial"))
        weight=esc(o.get("fontWeight","400")); align=o.get("textAlign","left")
        anchor={"left":"start","center":"middle","right":"end"}.get(align,"start")
        tx=x if align=="left" else (x+w/2 if align=="center" else x+w)
        chunks=[]
        lh=size*o.get("lineHeight",1.05)
        for i,txt in enumerate(str(o.get("text","")).split("\n")):
            chunks.append(f'<tspan x="{tx}" dy="{0 if i==0 else lh}">{esc(txt)}</tspan>')
        return f'<text x="{tx}" y="{y+size}" fill="{fill}" font-family="{fam}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" opacity="{opacity}">'+"".join(chunks)+"</text>"
    return ""


def svg_for_page(page,W,H):
    body="\n".join(object_to_svg(o) for o in page["objects"] if isinstance(o,dict))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n{body}\n</svg>'


def structural_signature(objects):
    slim=[]
    for o in objects:
        if not isinstance(o,dict):
            continue
        typ=o.get("type")
        entry={"type":typ}
        for k in ("left","top","width","height","radius","rx","ry","angle","fontSize","textAlign","strokeWidth","x1","y1","x2","y2"):
            if k in o:
                v=o[k]
                if isinstance(v,float):
                    v=round(v,2)
                entry[k]=v
        if typ=="polygon":
            entry["points"]=[(round(p["x"],1),round(p["y"],1)) for p in o.get("points",[])]
        if typ=="path":
            entry["path"]=o.get("path","")
        slim.append(entry)
    raw=json.dumps(slim,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_template(index,W,H):
    layout_idx=(index-1)//10
    art_idx=(index-1)%10
    layout=LAYOUTS[layout_idx]
    art=ART_SYSTEMS[art_idx]

    sector_name,headline,sub,cta = SECTORS[(index-1) % len(SECTORS)]
    p=deepcopy(PALETTES[(index*7 + layout_idx*3) % len(PALETTES)])
    title_font,body_font=FONT_PAIRS[(index*5 + art_idx) % len(FONT_PAIRS)]

    objects=[]
    layout(objects,p,W,H,headline,sub,cta,art,title_font,body_font)
    objects.append(textbox(f"{index:02d}",W-96,52,50,17,p["accent"],family=body_font,weight="700",align="right",name="Template number"))
    objects.append(circle(72,92,5,p["gold"],name="Editable detail"))

    finish=["Matte","High-Gloss","Soft-Touch","Satin","Foil Accent"][index%5]
    page={"name":"Flyer","label":"Flyer","objects":objects,"width":W,"height":H}
    sig=structural_signature(objects)

    data={
        "version": 1,
        "templateType": "editable-master",
        "reconstructed": True,
        "editable": True,
        "flyer_library": True,
        LIBRARY_KEY: LIBRARY_VERSION,
        "flyer_code": f"zv-flyer-v1-{index:03d}",
        "canvas": {"width":W,"height":H},
        "pages":[page],
        "adminPages":[deepcopy(page)],
        "meta":{
            "sector":sector_name,
            "layout_architecture":layout.__name__,
            "art_system":art.__name__,
            "finish":finish,
            "palette":p["name"],
            "structural_signature":sig,
            "uniqueness_rule":"Colour/text/finish changes do not count as a unique design.",
        }
    }
    name=f"{PREFIX} {index:03d} Â· {sector_name} Â· {finish}"
    return name,data,svg_for_page(page,W,H),sig


def validate_template(data):
    if data.get("templateType")!="editable-master" or not data.get("reconstructed"):
        raise ValueError("Template is not editor-native editable-master JSON.")
    pages=data.get("pages")
    if not isinstance(pages,list) or not pages:
        raise ValueError("Template has no pages.")
    objects=pages[0].get("objects")
    if not isinstance(objects,list) or not objects:
        raise ValueError("Template page has no objects.")
    bad=[x for x in objects if not isinstance(x,dict)]
    if bad:
        raise ValueError(f"Non-object entries found: {[repr(x)[:80] for x in bad[:5]]}")
    editable_text=[o for o in objects if o.get("type") in {"text","textbox","i-text"} and not o.get("locked")]
    if len(editable_text)<4:
        raise ValueError("Template does not contain enough editable text objects.")
    supported={"rect","circle","ellipse","line","polygon","path","text","textbox","i-text"}
    unknown=sorted({o.get("type") for o in objects if o.get("type") not in supported})
    if unknown:
        raise ValueError(f"Unsupported object types: {unknown}")


class Command(BaseCommand):
    help = "Create 100 materially distinct editable flyer templates (JSON master + SVG previews)."

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

        if count<1 or count>100:
            raise CommandError("--count must be between 1 and 100.")

        try:
            product=Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise CommandError(f"Product {product_id} does not exist.")

        W=int(getattr(product,"width",0) or DEFAULT_W)
        H=int(getattr(product,"height",0) or DEFAULT_H)

        if W >= H:
            self.stdout.write(self.style.WARNING(
                f"Product internal canvas is {W}Ã—{H}. Flyer templates are intended for portrait products. "
                "The command will preserve product dimensions rather than silently changing them."
            ))

        built=[]
        signatures=set()

        for i in range(1,count+1):
            name,data,svg,sig=build_template(i,W,H)
            validate_template(data)
            if sig in signatures:
                raise CommandError(f"Structural duplicate detected at template {i}: {name}")
            signatures.add(sig)
            built.append((name,data,svg))
            self.stdout.write(f"{i:03d}: {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Validated {len(built)} editable flyers; unique structural signatures: {len(signatures)}"
        ))
        self.stdout.write(
            "Uniqueness: 10 layout architectures Ã— 10 artwork systems; palette/text/finish changes are ignored by duplicate validation."
        )
        self.stdout.write("Master format: editable JSON Fabric primitives. SVG is preview/sidecar only.")

        if dry:
            self.stdout.write(self.style.SUCCESS("Dry run complete; database unchanged."))
            return

        with transaction.atomic():
            if replace:
                old=DesignTemplate.objects.filter(
                    product=product,
                    json_data__flyer_library=True,
                    json_data__flyer_library_version=LIBRARY_VERSION,
                )
                old_count=old.count()
                old.delete()
                self.stdout.write(f"Removed {old_count} existing V{LIBRARY_VERSION} generated flyer templates.")

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
                        f"flyer_v1_{i:03d}.svg",
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
                        f"flyer_v1_{i:03d}.svg",
                        ContentFile(svg.encode("utf-8")),
                        save=False,
                    )
                    obj.save()
                    created+=1

        self.stdout.write(self.style.SUCCESS(
            f"Complete. Created: {created}; Updated: {updated}; Product: {product.id} Â· {product.name}"
        ))

