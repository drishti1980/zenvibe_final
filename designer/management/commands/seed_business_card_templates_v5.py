from __future__ import annotations

import hashlib
import json
import math
from html import escape

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from designer.models import DesignTemplate, Product


# ZenVibe business-card editor logical canvas. 3.5 x 2.0 inch landscape ratio.
W, H = 1050, 600
VERSION = 13
PREFIX_STANDARD = "ZV13 Standard"
PREFIX_PREMIUM = "ZV13 Premium"


STANDARD_PALETTES = [
    ("Electric Cobalt", "#101828", "#F8FAFF", "#2563EB", "#60A5FA", "#DCEBFF"),
    ("Aqua Punch", "#073B4C", "#F5FFFF", "#00B8A9", "#6FFFE9", "#D8FFFB"),
    ("Coral Studio", "#321B1B", "#FFF8F6", "#FF5A5F", "#FF9B85", "#FFE1DA"),
    ("Violet Pop", "#21133A", "#FCF8FF", "#7C3AED", "#C084FC", "#EEDCFF"),
    ("Citrus Navy", "#0D1B2A", "#FFFDF2", "#F4B400", "#FFE066", "#FFF3B0"),
    ("Mint Graphite", "#20252B", "#F7FFFB", "#19C37D", "#6EE7B7", "#D6F9E8"),
    ("Hot Pink Ink", "#27131E", "#FFF8FC", "#EC4899", "#FB7185", "#FCE7F3"),
    ("Orange Tech", "#172033", "#FFFAF5", "#F97316", "#FDBA74", "#FFEDD5"),
    ("Turquoise Cream", "#103C3F", "#FFFDF7", "#14B8A6", "#5EEAD4", "#CCFBF1"),
    ("Royal Lime", "#1D2A21", "#FAFFF5", "#84CC16", "#BEF264", "#ECFCCB"),
    ("Red Signal", "#281515", "#FFF9F9", "#E11D48", "#FB7185", "#FFE4E6"),
    ("Sky Indigo", "#172554", "#F8FBFF", "#0EA5E9", "#818CF8", "#DBEAFE"),
    ("Purple Tangerine", "#24152E", "#FFFAF7", "#9333EA", "#FB923C", "#F3E8FF"),
    ("Teal Lemon", "#083344", "#FFFFF3", "#0D9488", "#FACC15", "#CCFBF1"),
    ("Magenta Blue", "#251335", "#FFF8FD", "#D946EF", "#3B82F6", "#F5D0FE"),
    ("Forest Coral", "#173025", "#FCFFF9", "#16A34A", "#FB7185", "#DCFCE7"),
    ("Cerulean Sand", "#17324D", "#FFF9EF", "#0284C7", "#F59E0B", "#E0F2FE"),
    ("Plum Mint", "#321B36", "#FCFAFF", "#A21CAF", "#34D399", "#FAE8FF"),
    ("Black Neon", "#090B10", "#F9FAFB", "#22D3EE", "#A3E635", "#CFFAFE"),
    ("Blue Raspberry", "#151E3F", "#FAFAFF", "#4F46E5", "#F43F5E", "#E0E7FF"),
]

PREMIUM_PALETTES = [
    ("Obsidian Gold", "#070707", "#FBF8F1", "#D4AF37", "#F2D27A", "#2A2520"),
    ("Emerald Champagne", "#052D26", "#FFF9EE", "#C8A55A", "#EED59A", "#16463C"),
    ("Burgundy Rose Gold", "#3A0B18", "#FFF8F5", "#C9877C", "#F0B7AA", "#5B1729"),
    ("Midnight Sapphire", "#071B35", "#FFFBF4", "#D8B968", "#F1DB9E", "#122E52"),
    ("Royal Aubergine", "#261333", "#FFF9F1", "#D3AF64", "#EBD49A", "#42204F"),
    ("Teal Brass", "#08383B", "#FBF8F0", "#C6A15B", "#E9CF95", "#14565A"),
    ("Espresso Copper", "#23140D", "#FFF8F0", "#C47A4A", "#EAB38D", "#432619"),
    ("Pearl Black", "#101010", "#F8F6F0", "#D6D0C4", "#FFFFFF", "#292929"),
    ("Ruby Champagne", "#4A071A", "#FFF7EF", "#DAB46D", "#F3D89A", "#67132B"),
    ("Navy Platinum", "#0A1728", "#FAFAF7", "#B9C2CC", "#E4E9EE", "#182A43"),
    ("Jade Gold", "#0A3B30", "#FFF9EF", "#D1AB58", "#F1D48A", "#1C5748"),
    ("Black Fuchsia Gold", "#0B0A0D", "#FFF8FC", "#D8AF55", "#E63AAE", "#231A24"),
    ("Cobalt Gold", "#071E4A", "#FFF9EF", "#D6B356", "#F1D98B", "#123B7A"),
    ("Violet Champagne", "#26123B", "#FFF8F0", "#D4B16B", "#E7CFF7", "#432160"),
    ("Forest Antique Gold", "#132D20", "#FFF9EE", "#B9944A", "#E4C67E", "#294C38"),
    ("Scarlet Gold", "#4A0B0B", "#FFF8F0", "#D4A74F", "#F0CB78", "#711B1B"),
    ("Petrol Champagne", "#0B3037", "#FFFAF2", "#D2AE69", "#F0D69D", "#174B55"),
    ("Mocha Pearl", "#2F231E", "#FAF7F2", "#C8B7A3", "#E7D9C8", "#4B3930"),
    ("Onyx Cyan Foil", "#090C10", "#F8FBFC", "#84E8F5", "#D7F8FC", "#17232A"),
    ("Graphite Rose", "#1A1A1F", "#FFF9FA", "#D98D9E", "#F4C2CC", "#303038"),
]

INDUSTRIES = [
    ("Creative Studio", "MAYA REED", "CREATIVE DIRECTOR", "AURELIA STUDIO"),
    ("Architecture", "NOAH WILSON", "ARCHITECT", "FORM / SPACE"),
    ("Real Estate", "SOPHIA MIRANDA", "PROPERTY ADVISER", "MERIDIAN REALTY"),
    ("Technology", "ETHAN COLE", "PRODUCT LEAD", "NEXORA DIGITAL"),
    ("Finance", "MIA BENNETT", "FINANCIAL ADVISER", "CRESTLINE"),
    ("Legal", "OLIVIA PARKER", "PRINCIPAL LAWYER", "PARKER LEGAL"),
    ("Beauty", "AVA ROSE", "FOUNDER", "MAISON AVA"),
    ("Fashion", "ISABELLE LANE", "CREATIVE FOUNDER", "ATELIER LANE"),
    ("Photography", "LUCAS REED", "PHOTOGRAPHER", "REED STUDIO"),
    ("Hospitality", "LIAM BROWN", "GENERAL MANAGER", "THE HARTFORD"),
    ("Medical", "DR EMMA KING", "MEDICAL DIRECTOR", "VERA HEALTH"),
    ("Construction", "RYAN COOPER", "PROJECT DIRECTOR", "AXIS BUILD"),
    ("Interior", "AMELIA SCOTT", "INTERIOR DESIGNER", "STUDIO SCOTT"),
    ("Marketing", "CHARLOTTE EVANS", "BRAND STRATEGIST", "BRIGHTLAB"),
    ("Automotive", "JACK HARRIS", "DIRECTOR", "MOTORHAUS"),
    ("Jewellery", "ELLA MARTIN", "DESIGNER", "ORIEL JEWELS"),
    ("Fitness", "JAMES WALKER", "HEAD COACH", "KINETIC CLUB"),
    ("Food", "HENRY THOMAS", "EXECUTIVE CHEF", "EMBER & SALT"),
    ("Events", "GRACE LEE", "EVENT DIRECTOR", "MONARCH EVENTS"),
    ("Consulting", "JOHN MARTINEZ", "BUSINESS CONSULTANT", "MARTINEZ & CO."),
]

FONT_PAIRS = [
    ("Montserrat", "DM Sans"), ("Poppins", "Inter"), ("League Spartan", "DM Sans"),
    ("Playfair Display", "Montserrat"), ("Cormorant Garamond", "DM Sans"),
    ("Cinzel", "Montserrat"), ("Libre Baskerville", "Inter"), ("Bodoni Moda", "DM Sans"),
    ("Raleway", "Inter"), ("Josefin Sans", "DM Sans"), ("Abril Fatface", "Montserrat"),
    ("Merriweather", "Inter"), ("Oswald", "DM Sans"), ("Lora", "Montserrat"),
    ("Manrope", "Inter"), ("Prata", "DM Sans"), ("DM Serif Display", "Montserrat"),
    ("Urbanist", "Inter"), ("Space Grotesk", "DM Sans"), ("Italiana", "Montserrat"),
]

PREMIUM_FONT_PAIRS = [
    ("Cinzel", "Montserrat"),
    ("Cormorant Garamond", "DM Sans"),
    ("Playfair Display", "Montserrat"),
    ("Bodoni Moda", "DM Sans"),
    ("Prata", "Inter"),
    ("DM Serif Display", "Montserrat"),
    ("Italiana", "DM Sans"),
    ("Libre Baskerville", "Inter"),
]

STYLE_NAMES_STANDARD = [
    "Electric Split", "Aqua Grid", "Coral Orbit", "Violet Ribbon", "Citrus Column",
    "Mint Capsule", "Hot Pink Editorial", "Orange Circuit", "Turquoise Wave", "Royal Lime Blocks",
    "Red Signal Frame", "Sky Indigo Halo", "Purple Tangerine Cut", "Teal Lemon Swiss", "Magenta Blue Portal",
    "Forest Coral Stack", "Cerulean Sand Arc", "Plum Mint Window", "Black Neon Rail", "Blue Raspberry Mosaic",
    "Cobalt Offset", "Aqua Diagonal", "Coral Monogram", "Violet Bauhaus", "Citrus Badge",
    "Mint Fold", "Hot Pink Capsule", "Orange Stripe", "Turquoise Orbit", "Royal Lime Corner",
    "Red Signal Editorial", "Sky Indigo Bands", "Purple Tangerine Arch", "Teal Lemon Card", "Magenta Blue Vertical",
    "Forest Coral Geometry", "Cerulean Sand Split", "Plum Mint Marker", "Black Neon Tech", "Blue Raspberry Linework",
    "Cobalt Swiss", "Aqua Poster", "Coral Frame", "Violet Sphere", "Citrus Check",
    "Mint Offset", "Hot Pink Wave", "Orange Monogram", "Turquoise Grid", "Royal Lime Ribbon",
    "Red Signal Cutout", "Sky Indigo Capsule", "Purple Tangerine Orbit", "Teal Lemon Blocks", "Magenta Blue Stripe",
    "Forest Coral Portal", "Cerulean Sand Rail", "Plum Mint Bands", "Black Neon Window", "Blue Raspberry Badge",
    "Cobalt Circuit", "Aqua Stack", "Coral Bauhaus", "Violet Arc", "Citrus Swiss",
    "Mint Mosaic", "Hot Pink Split", "Orange Halo", "Turquoise Editorial", "Royal Lime Diagonal",
    "Red Signal Column", "Sky Indigo Grid", "Purple Tangerine Frame", "Teal Lemon Wave", "Magenta Blue Offset",
    "Forest Coral Capsule", "Cerulean Sand Monogram", "Plum Mint Portal", "Black Neon Ribbon", "Blue Raspberry Corner",
    "Cobalt Bands", "Aqua Cut", "Coral Rail", "Violet Blocks", "Citrus Sphere",
    "Mint Arch", "Hot Pink Geometry", "Orange Card", "Turquoise Stripe", "Royal Lime Orbit",
    "Red Signal Mosaic", "Sky Indigo Window", "Purple Tangerine Swiss", "Teal Lemon Badge", "Magenta Blue Circuit",
    "Forest Coral Editorial", "Cerulean Sand Ribbon", "Plum Mint Grid", "Black Neon Halo", "Blue Raspberry Luxe Pop",
]

STYLE_NAMES_PREMIUM = [
    "Obsidian Signature", "Emerald Reserve", "Burgundy Atelier", "Midnight Crest", "Royal Aubergine House",
    "Teal Brass Gallery", "Espresso Copper Mark", "Pearl Black Monogram", "Ruby Champagne Frame", "Navy Platinum Line",
    "Jade Gold Arch", "Black Fuchsia Foil", "Cobalt Gold Estate", "Violet Champagne Seal", "Forest Antique Border",
    "Scarlet Gold Editorial", "Petrol Champagne Column", "Mocha Pearl Studio", "Onyx Cyan Foil", "Graphite Rose Salon",
    "Obsidian Art Deco", "Emerald Fine Line", "Burgundy Velvet", "Midnight Gilded", "Royal Aubergine Monogram",
    "Teal Brass Crest", "Espresso Copper Frame", "Pearl Black Editorial", "Ruby Champagne Arch", "Navy Platinum House",
    "Jade Gold Signature", "Black Fuchsia Gallery", "Cobalt Gold Seal", "Violet Champagne Border", "Forest Antique Column",
    "Scarlet Gold Estate", "Petrol Champagne Monogram", "Mocha Pearl Line", "Onyx Cyan Reserve", "Graphite Rose Atelier",
    "Obsidian Gallery", "Emerald Art Deco", "Burgundy Fine Line", "Midnight Velvet", "Royal Aubergine Gilded",
    "Teal Brass Monogram", "Espresso Copper Crest", "Pearl Black Frame", "Ruby Champagne Editorial", "Navy Platinum Arch",
    "Jade Gold House", "Black Fuchsia Signature", "Cobalt Gold Gallery", "Violet Champagne Seal", "Forest Antique Border II",
    "Scarlet Gold Column", "Petrol Champagne Estate", "Mocha Pearl Monogram", "Onyx Cyan Line", "Graphite Rose Reserve",
    "Obsidian Atelier", "Emerald Gallery", "Burgundy Art Deco", "Midnight Fine Line", "Royal Aubergine Velvet",
    "Teal Brass Gilded", "Espresso Copper Monogram", "Pearl Black Crest", "Ruby Champagne Frame", "Navy Platinum Editorial",
    "Jade Gold Arch II", "Black Fuchsia House", "Cobalt Gold Signature", "Violet Champagne Gallery", "Forest Antique Seal",
    "Scarlet Gold Border", "Petrol Champagne Column II", "Mocha Pearl Estate", "Onyx Cyan Monogram", "Graphite Rose Line",
    "Obsidian Reserve", "Emerald Atelier", "Burgundy Gallery", "Midnight Art Deco", "Royal Aubergine Fine Line",
    "Teal Brass Velvet", "Espresso Copper Gilded", "Pearl Black Monogram II", "Ruby Champagne Crest", "Navy Platinum Frame",
    "Jade Gold Editorial", "Black Fuchsia Arch", "Cobalt Gold House", "Violet Champagne Signature", "Forest Antique Gallery",
    "Scarlet Gold Seal", "Petrol Champagne Border", "Mocha Pearl Column", "Onyx Cyan Estate", "Graphite Rose Finale",
]


def rect(i, x, y, w, h, fill, opacity=1, angle=0, rx=0, stroke=None, sw=0, editable=True):
    d = {"id": i, "name": i.replace("_", " ").title(), "type": "rect", "left": round(x, 2), "top": round(y, 2),
         "width": round(w, 2), "height": round(h, 2), "fill": fill, "opacity": opacity, "angle": angle,
         "rx": rx, "ry": rx, "customerEditable": editable}
    if stroke:
        d.update(stroke=stroke, strokeWidth=sw or 2)
    return d


def circle(i, x, y, r, fill, opacity=1, stroke=None, sw=0):
    d = {"id": i, "name": i.replace("_", " ").title(), "type": "circle", "left": round(x-r, 2), "top": round(y-r, 2),
         "radius": round(r, 2), "fill": fill, "opacity": opacity, "customerEditable": True}
    if stroke:
        d.update(stroke=stroke, strokeWidth=sw or 2)
    return d


def line(i, x1, y1, x2, y2, stroke, sw=2, opacity=1):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "line", "left": 0, "top": 0,
            "points": [x1, y1, x2, y2], "stroke": stroke, "strokeWidth": sw, "fill": None,
            "opacity": opacity, "customerEditable": True}


def text(i, x, y, value, size, fill, font="Inter", weight=400, width=None, align="left", spacing=0, italic=False):
    d = {"id": i, "name": i.replace("_", " ").title(), "type": "textbox", "left": round(x, 2), "top": round(y, 2),
         "text": value, "fontSize": size, "font": font, "fontFamily": font, "fontWeight": weight, "fill": fill,
         "textAlign": align, "charSpacing": spacing, "lineHeight": 1.08, "originX": "left", "originY": "top", "selectable": True, "evented": True, "locked": False, "customerEditable": True}
    if width is not None:
        d["width"] = round(width, 2)
    if italic:
        d["fontStyle"] = "italic"
    return d


def polygon(i, pts, fill, opacity=1, stroke=None, sw=0):
    d = {"id": i, "name": i.replace("_", " ").title(), "type": "polygon", "left": 0, "top": 0,
         "points": [{"x": round(x, 2), "y": round(y, 2)} for x, y in pts], "fill": fill,
         "opacity": opacity, "customerEditable": True}
    if stroke:
        d.update(stroke=stroke, strokeWidth=sw or 2)
    return d


def path(i, d, fill="transparent", stroke="#111111", sw=2, opacity=1):
    return {"id": i, "name": i.replace("_", " ").title(), "type": "path", "left": 0, "top": 0,
            "path": d, "fill": fill, "stroke": stroke, "strokeWidth": sw, "opacity": opacity,
            "customerEditable": True}


def logo_mark(prefix, x, y, size, fg, bg, kind):
    o = []
    if kind == 0:
        o += [circle(prefix+"_ring", x, y, size/2, "transparent", 1, fg, 3), text(prefix+"_txt", x-size*.32, y-size*.26, "AM", size*.40, fg, "Cinzel", 700, size*.64, "center")]
    elif kind == 1:
        o += [rect(prefix+"_box", x-size/2, y-size/2, size, size, "transparent", 1, 10, 8, fg, 3), text(prefix+"_txt", x-size*.34, y-size*.24, "NS", size*.38, fg, "Montserrat", 800, size*.68, "center")]
    elif kind == 2:
        o += [polygon(prefix+"_diamond", [(x,y-size*.52),(x+size*.52,y),(x,y+size*.52),(x-size*.52,y)], "transparent", 1, fg, 3), text(prefix+"_txt", x-size*.30, y-size*.22, "NV", size*.34, fg, "DM Sans", 800, size*.60, "center")]
    elif kind == 3:
        o += [circle(prefix+"_disc", x, y, size/2, fg), text(prefix+"_txt", x-size*.32, y-size*.23, "AR", size*.36, bg, "Playfair Display", 700, size*.64, "center")]
    else:
        o += [line(prefix+"_l1", x-size*.42, y-size*.30, x+size*.42, y+size*.30, fg, 4), line(prefix+"_l2", x-size*.42, y+size*.30, x+size*.42, y-size*.30, fg, 4), circle(prefix+"_dot", x, y, size*.08, fg)]
    return o


def contact_block(x, y, color, width=400, align="left", compact=False, vertical=True):
    fs = 17 if compact else 19
    if vertical:
        gap = 35 if compact else 40
        return [
            text("phone", x, y, "+61 423 456 789", fs, color, "DM Sans", 500, width, align),
            text("email", x, y+gap, "hello@company.com", fs, color, "DM Sans", 500, width, align),
            text("web", x, y+gap*2, "www.company.com", fs, color, "DM Sans", 500, width, align),
            text("addr", x, y+gap*3, "123 Collins Street · Melbourne", fs, color, "DM Sans", 500, width, align),
        ]
    return [text("contact", x, y, "+61 423 456 789   •   hello@company.com   •   company.com", fs, color, "DM Sans", 500, width, align)]


def motif_layers(kind, accent, accent2, soft, dark, light, seed):
    o = []
    s = seed
    if kind == 0:  # orbit
        o += [circle("m_orbit1", 905, 92, 155+s%30, "transparent", 1, accent, 5), circle("m_orbit2", 905, 92, 95+s%18, "transparent", 1, accent2, 2), circle("m_orbit3", 905, 92, 22, accent)]
    elif kind == 1:  # bauhaus
        o += [circle("m_b1", 890, 95, 115, accent, .92), rect("m_b2", 760, 375, 285, 180, accent2, .82, -8), circle("m_b3", 100, 520, 90, soft, .9)]
    elif kind == 2:  # wave
        o += [path("m_wave1", "M 0 470 Q 210 390 420 470 T 840 470 T 1100 470", "transparent", accent, 8, .9), path("m_wave2", "M 0 505 Q 210 425 420 505 T 840 505 T 1100 505", "transparent", accent2, 3, .7)]
    elif kind == 3:  # stripes
        for n in range(6):
            o.append(rect(f"m_stripe{n}", 720+n*48, -80, 24, 780, accent if n%2==0 else accent2, .88, 18))
    elif kind == 4:  # botanical line
        o += [path("m_stem", "M 910 550 C 860 430 870 250 930 90", "transparent", accent, 3, .85)]
        for n,(x,y,a) in enumerate([(895,440,-28),(930,370,34),(887,300,-30),(942,230,28),(910,160,-20)]):
            o.append(path(f"m_leaf{n}", f"M {x} {y} C {x+35} {y-20} {x+48} {y+6} {x+8} {y+25} Z", soft, accent, 2, .9))
    elif kind == 5:  # deco
        o += [line("m_deco1", 75, 55, 975, 55, accent, 3), line("m_deco2", 75, 545, 975, 545, accent, 3), polygon("m_deco3", [(525,35),(547,55),(525,75),(503,55)], accent), polygon("m_deco4", [(525,525),(547,545),(525,565),(503,545)], accent)]
    elif kind == 6:  # portal arch
        o += [rect("m_arch", 770, 65, 220, 470, "transparent", 1, 105, 105, accent, 4), rect("m_arch2", 792, 88, 176, 424, "transparent", 1, 86, 86, accent2, 2)]
    elif kind == 7:  # grid dots
        for r in range(5):
            for c in range(5):
                o.append(circle(f"m_dot_{r}_{c}", 820+c*38, 105+r*38, 4+(r+c)%3, accent if (r+c)%2==0 else accent2, .85))
    elif kind == 8:  # checker
        for r in range(4):
            for c in range(4):
                if (r+c)%2==0:
                    o.append(rect(f"m_check_{r}_{c}", 835+c*44, 370+r*44, 44, 44, accent, .85))
    elif kind == 9:  # corners
        o += [polygon("m_corner1", [(0,0),(350,0),(0,210)], accent, .95), polygon("m_corner2", [(1050,600),(700,600),(1050,390)], accent2, .92)]
    elif kind == 10:  # rings
        for n in range(4):
            o.append(circle(f"m_ring{n}", 900, 300, 65+n*38, "transparent", 1, accent if n%2==0 else accent2, 3))
    elif kind == 11:  # ribbons
        o += [rect("m_ribbon1", 760, -160, 95, 850, accent, .95, 24), rect("m_ribbon2", 860, -130, 45, 820, accent2, .85, 24)]
    elif kind == 12:  # glass capsule
        o += [rect("m_capsule", 705, 90, 290, 420, light, .11, 0, 145, accent, 2), circle("m_capsule_glow", 850, 300, 135, accent2, .11)]
    elif kind == 13:  # line fan
        for n in range(9):
            o.append(line(f"m_fan{n}", 845, 300, 1040, 60+n*60, accent if n%2==0 else accent2, 2, .75))
    elif kind == 14:  # offset blocks
        o += [rect("m_blk1", 760, 65, 240, 145, accent, .93, -4), rect("m_blk2", 810, 230, 210, 130, accent2, .80, 7), rect("m_blk3", 735, 385, 255, 130, soft, .85, -6)]
    elif kind == 15:  # halo
        o += [circle("m_halo1", 865, 300, 190, accent, .16), circle("m_halo2", 865, 300, 125, accent2, .13), circle("m_halo3", 865, 300, 64, accent, .84)]
    elif kind == 16:  # steps
        for n in range(6):
            o.append(rect(f"m_step{n}", 740+n*45, 420-n*55, 210-n*18, 36, accent if n%2==0 else accent2, .88))
    elif kind == 17:  # starburst
        for n in range(12):
            ang = math.radians(n*30)
            o.append(line(f"m_ray{n}", 900, 300, 900+190*math.cos(ang), 300+190*math.sin(ang), accent if n%2==0 else accent2, 3, .8))
        o.append(circle("m_ray_center", 900, 300, 28, light))
    elif kind == 18:  # tiled bars
        for n in range(8):
            o.append(rect(f"m_tile{n}", 710+(n%4)*85, 80+(n//4)*225, 65, 185, accent if n%3 else accent2, .82, (n%3-1)*5, 14))
    else:  # signature curves
        o += [path("m_curve1", "M 700 430 C 790 140 940 100 1040 250", "transparent", accent, 5, .85), path("m_curve2", "M 720 500 C 820 220 950 190 1050 340", "transparent", accent2, 3, .65)]
    return o


def finish_layers(finish, accent, accent2, dark, light, seed):
    # Visual simulation only. Standard cards stay visually normal/clean.
    if finish in ("standard", "normal", "none", None):
        return []
    if finish == "matte":
        return [rect("finish_matte", 0, 0, W, H, dark, .018), rect("finish_edge", 18, 18, W-36, H-36, "transparent", 1, 0, 12, light, 1)]
    if finish == "gloss":
        return [rect("finish_gloss", 560+(seed%5)*35, -110, 150, 820, "#FFFFFF", .06, 18+(seed%4)*5), circle("finish_glow", 920, 80, 230, "#FFFFFF", .035)]
    if finish == "soft-touch":
        return [rect("finish_soft", 0, 0, W, H, dark, .055), rect("finish_soft2", 0, 0, W, H, light, .012)]
    if finish == "foil":
        return [line("finish_foil_top", 45, 35, 1005, 35, accent, 3, .95), line("finish_foil_bottom", 45, 565, 1005, 565, accent, 3, .95), circle("finish_foil_dot", 525, 35, 4, accent2)]
    return [rect("finish_satin", 0, 0, W, H, light, .012), rect("finish_sheen", -120, 390, 1340, 70, "#FFFFFF", .035, -8)]




def unique_vector_art(spec, accent, accent2):
    """One editable vector signature per template. It changes geometry, not just colour."""
    i = spec["index"] + (137 if spec["tier"] == "premium" else 0)
    x0 = 680 + (i * 17) % 95
    y0 = 60 + (i * 23) % 85
    x1 = 840 + (i * 29) % 120
    y1 = 165 + (i * 31) % 130
    x2 = 770 + (i * 37) % 180
    y2 = 330 + (i * 19) % 150
    x3 = 990 - (i * 11) % 120
    y3 = 520 - (i * 13) % 100
    d1 = f"M {x0} {y0} C {x1} {y1} {x2} {y2} {x3} {y3}"
    d2 = f"M {x0+18} {y0+28} Q {(x1+x2)//2} {(y1+y2)//2} {x3-24} {y3-18}"
    sw1 = 2 + (i % 4)
    sw2 = 1 + ((i // 3) % 3)
    return [
        path("unique_vector_primary", d1, "transparent", accent, sw1, .55 if spec["tier"]=="standard" else .72),
        path("unique_vector_secondary", d2, "transparent", accent2, sw2, .42 if spec["tier"]=="standard" else .62),
    ]

def front_layout(spec):
    dark, light, accent, accent2, soft = spec["colors"]
    industry, person, role, company = spec["industry"]
    head_font, body_font = spec["fonts"]
    layout = spec["layout"]
    motif = spec["motif"]
    seed = spec["index"]
    variant = spec["variant"]
    dv = [0, 28, -22, 46, -38][variant]
    o = [rect("background", 0, 0, W, H, light)]

    # Ten fundamentally different information architectures.
    if layout == 0:  # left brand panel / right details
        o += [rect("brand_panel", 0, 0, 355+dv, H, dark), rect("accent_rail", 345+dv, 0, 18, H, accent)]
        o += logo_mark("logo", 178, 135, 112, accent2, dark, spec["logo_kind"])
        o += [text("company", 60, 260, company, 28, light, head_font, 700, 235, "center", 30), text("name", 430, 95, person, 45, dark, head_font, 750), text("role", 432, 155, role, 18, accent, body_font, 700, spacing=60)]
        o += contact_block(435, 250, dark, 430, "left", compact=True)
    elif layout == 1:  # full dark / glass detail card
        o[0] = rect("background", 0, 0, W, H, dark)
        o += [rect("glass_card", 400+dv/2, 70-variant*4, 580-dv/2, 460+variant*6, light, .10, variant-2, 24+variant*3, accent, 2)]
        o += logo_mark("logo", 150, 135, 118, accent2, dark, spec["logo_kind"])
        o += [text("company", 65, 245, company, 27, light, head_font, 700, 220, "center"), text("name", 460, 115, person, 43, light, head_font, 700), text("role", 462, 174, role, 18, accent2, body_font, 650, spacing=80)]
        o += contact_block(465, 265, light, 420, "left", compact=True)
    elif layout == 2:  # centered editorial
        o += logo_mark("logo", 525+dv, 95+variant*8, 82+variant*7, accent, light, spec["logo_kind"])
        o += [text("name", 150, 185, person, 48, dark, head_font, 700, 750, "center"), text("role", 200, 250, role, 17, accent, body_font, 700, 650, "center", 130), line("rule", 315, 300, 735, 300, accent, 2)]
        o += contact_block(185, 355, dark, 680, "center", compact=True, vertical=False)
        o += [text("company", 200, 455, company, 20, dark, body_font, 650, 650, "center", 100)]
    elif layout == 3:  # diagonal split
        o += [polygon("dark_diag", [(0,0),(650+dv,0),(430-dv,H),(0,H)], dark), polygon("accent_diag", [(620+dv,0),(675+dv,0),(455-dv,H),(400-dv,H)], accent)]
        o += logo_mark("logo", 165, 140, 105, accent2, dark, spec["logo_kind"])
        o += [text("company", 65, 260, company, 28, light, head_font, 700, 300), text("name", 590, 110, person, 41, dark, head_font, 750, 390), text("role", 593, 168, role, 17, accent, body_font, 700, 390)]
        o += contact_block(590, 260, dark, 360, "left", compact=True)
    elif layout == 4:  # top identity / bottom contacts
        o += [rect("top_field", 0, 0, W, 330+dv/2, dark), rect("accent_line", 0, 324+dv/2, W, 12, accent)]
        o += logo_mark("logo", 125, 135, 105, accent2, dark, spec["logo_kind"])
        o += [text("name", 245, 90, person, 46, light, head_font, 750), text("role", 248, 153, role, 18, accent2, body_font, 700, spacing=80), text("company", 248, 205, company, 22, light, body_font, 600)]
        o += contact_block(85, 415, dark, 880, "center", compact=True, vertical=False)
    elif layout == 5:  # vertical bar + spacious details
        o += [rect("vertical", 0, 0, 118+variant*9, H, accent), rect("vertical_dark", 118+variant*9, 0, 205+dv/2, H, dark)]
        o += logo_mark("logo", 220, 112, 90, accent2, dark, spec["logo_kind"])
        o += [text("company", 160, 225, company, 22, light, head_font, 700, 115, "center"), text("name", 410, 90, person, 47, dark, head_font, 750), text("role", 412, 154, role, 18, accent, body_font, 700, spacing=75)]
        o += contact_block(415, 260, dark, 430, "left", compact=True)
    elif layout == 6:  # framed luxury/editorial
        o += [rect("outer_frame", 38+variant*5, 38+variant*5, W-76-variant*10, H-76-variant*10, "transparent", 1, 0, 10+variant*2, accent, 3), rect("inner_frame", 57+variant*7, 57+variant*7, W-114-variant*14, H-114-variant*14, "transparent", 1, 0, 8+variant*2, accent2, 1)]
        o += logo_mark("logo", 155, 150, 95, accent, light, spec["logo_kind"])
        o += [text("name", 310, 115, person, 43, dark, head_font, 700), text("role", 313, 172, role, 17, accent, body_font, 700, spacing=100), line("rule", 310, 222, 860, 222, accent, 2)]
        o += contact_block(315, 275, dark, 490, "left", compact=True)
    elif layout == 7:  # two-column card
        o += [rect("left_col", 0, 0, 520+dv, H, dark), rect("mid_rule", 510+dv, 0, 20+variant*3, H, accent)]
        o += logo_mark("logo", 160, 128, 108, accent2, dark, spec["logo_kind"])
        o += [text("company", 60, 250, company, 30, light, head_font, 700, 300, "center"), text("name", 590, 90, person, 40, dark, head_font, 750, 390), text("role", 593, 148, role, 17, accent, body_font, 700, 390)]
        o += contact_block(595, 245, dark, 350, "left", compact=True)
    elif layout == 8:  # floating identity block
        o += [rect("identity_card", 70+variant*8, 70-variant*5, 550+dv, 460-variant*8, dark, 1, -2+variant, 22+variant*3), rect("identity_accent", 95+variant*8, 95-variant*5, 500+dv, 8+variant*2, accent)]
        o += logo_mark("logo", 175, 165, 100, accent2, dark, spec["logo_kind"])
        o += [text("name", 130, 270, person, 39, light, head_font, 750, 420, "center"), text("role", 145, 330, role, 17, accent2, body_font, 700, 390, "center", 70)]
        o += contact_block(690, 190, dark, 300, "left", compact=True)
    else:  # typographic poster
        o += [text("initial", 45+dv, -65+variant*6, person[0], 330+variant*18, soft, head_font, 800, 280, "center"), text("name", 330, 88, person, 49, dark, head_font, 750), text("role", 333, 155, role, 18, accent, body_font, 700, spacing=85), line("rule", 332, 212, 905, 212, accent, 4)]
        o += contact_block(335, 275, dark, 500, "left", compact=True)
        o += [text("company", 335, 475, company, 19, dark, body_font, 700, 500, "left", 120)]

    # IMPORTANT: decoration must sit BEHIND the editable information.
    # Older versions appended motif/finish after the text, which could wash out
    # names/contact details and made several previews look almost blank.
    base = []
    content = []
    for obj in o:
        oid = str(obj.get("id", ""))
        if oid == "background" or oid.startswith((
            "brand_panel", "accent_rail", "glass_card", "dark_diag", "accent_diag",
            "top_field", "accent_line", "vertical", "vertical_dark", "outer_frame",
            "inner_frame", "left_col", "mid_rule", "identity_card", "identity_accent",
            "initial", "rule"
        )):
            base.append(obj)
        else:
            content.append(obj)

    decor = motif_layers(motif, accent, accent2, soft, dark, light, seed)
    decor += unique_vector_art(spec, accent, accent2)
    decor += finish_layers(spec["finish"], accent, accent2, dark, light, seed)

    # Content is always last/top-most. Every text/logo/contact object therefore
    # remains visible and directly selectable in Fabric.
    o = base + decor + content
    return o



def distinctive_front_layout(spec):
    """V10 collision-safe Business Card front generator.

    Premium 001-020 use twenty deliberately different luxury information
    architectures. Standard cards use the earlier layout engine whose
    layout+motif pairs are unique across the retained 80 cards.
    Every visible item is still a Fabric primitive/textbox.
    """
    if spec["tier"] != "premium":
        return front_layout(spec)

    dark, light, accent, accent2, soft = spec["colors"]
    _, person, role, company = spec["industry"]
    head, body = spec["fonts"]
    i = spec["index"]
    family = i % 20

    # Premium contrast is intentionally conservative: ivory/white on dark,
    # near-black on ivory, metallic accent only for small labels/rules.
    ink = "#111318"
    ivory = "#FFF9EF"
    white = "#FFFFFF"
    muted_dark = "#D8D3C9"

    def T(oid, x, y, value, size, fill, font=None, weight=600, width=None,
          align="left", spacing=0, italic=False):
        return text(oid, x, y, value, size, fill, font or body, weight,
                    width, align, spacing, italic)

    def contacts(x, y, colour, width=390, align="left", gap=39):
        return [
            T("phone", x, y, "+61 423 456 789", 17, colour, body, 500, width, align),
            T("email", x, y+gap, "hello@company.com", 17, colour, body, 500, width, align),
            T("web", x, y+gap*2, "www.company.com", 17, colour, body, 500, width, align),
            T("addr", x, y+gap*3, "123 Collins Street · Melbourne", 16, colour, body, 500, width, align),
        ]

    o = []

    # 01 — Obsidian split signature
    if family == 0:
        o += [rect("background",0,0,W,H,ivory), rect("brand",0,0,350,H,dark),
              rect("gold_rail",350,0,14,H,accent), circle("seal",900,90,72,accent,.82)]
        o += logo_mark("logo",175,135,105,accent2,dark,spec["logo_kind"])
        o += [T("company",55,255,company.upper(),25,white,head,700,240,"center",45),
              T("name",425,92,person.upper(),43,ink,head,700,500),
              T("role",428,153,role.upper(),15,accent,body,700,500,"left",90),
              line("rule",425,205,930,205,accent,2)] + contacts(428,255,ink,455)

    # 02 — Emerald full-bleed reserve with inset panel
    elif family == 1:
        o += [rect("background",0,0,W,H,dark), rect("inset",390,55,610,490,"#0D3C34",1,0,26,accent,2),
              path("curve","M 0 485 C 210 390 285 545 430 455","transparent",accent,7,.9),
              path("curve2","M 0 525 C 205 430 300 565 455 485","transparent",accent2,2,.75)]
        o += logo_mark("logo",155,150,112,accent2,dark,spec["logo_kind"])
        o += [T("company",55,270,company.upper(),24,white,head,700,205,"center",35),
              T("name",445,105,person.upper(),42,white,head,700,500),
              T("role",448,166,role.upper(),15,accent2,body,700,500,"left",80),
              line("rule",448,215,920,215,accent,2)] + contacts(450,260,white,430)

    # 03 — Burgundy editorial centre
    elif family == 2:
        o += [rect("background",0,0,W,H,light), rect("top",0,0,W,105,dark), rect("bottom",0,520,W,80,dark),
              line("frame_l",70,145,70,470,accent,3), line("frame_r",980,145,980,470,accent,3)]
        o += logo_mark("logo",155,305,105,accent,dark,spec["logo_kind"])
        o += [T("name",280,160,person.upper(),48,ink,head,700,650,"center"),
              T("role",330,230,role.upper(),15,accent,body,700,550,"center",110),
              T("company",330,285,company.upper(),23,ink,head,700,550,"center",45),
              line("rule",370,340,840,340,accent,2),
              T("contact",300,390,"+61 423 456 789   •   hello@company.com   •   company.com",16,ink,body,500,620,"center")]

    # 04 — Midnight diagonal crest
    elif family == 3:
        o += [rect("background",0,0,W,H,ivory), polygon("navy",[(0,0),(610,0),(400,H),(0,H)],dark),
              polygon("gold",[(575,0),(645,0),(435,H),(365,H)],accent)]
        o += logo_mark("logo",150,135,105,accent2,dark,spec["logo_kind"])
        o += [T("company",55,255,company.upper(),25,white,head,700,260,"center",45),
              T("name",620,90,person.upper(),40,ink,head,700,365),
              T("role",622,150,role.upper(),15,accent,body,700,365,"left",80)] + contacts(625,245,ink,330)

    # 05 — Aubergine monogram poster
    elif family == 4:
        o += [rect("background",0,0,W,H,dark), T("giant_initial",55,-80,person[0],390,"#3A2148",head,800,330,"center"),
              rect("info",350,0,700,H,light), rect("accent_top",350,0,700,12,accent)]
        o += logo_mark("logo",175,450,90,accent2,dark,spec["logo_kind"])
        o += [T("company",70,515,company.upper(),19,white,head,700,215,"center",35),
              T("name",430,95,person.upper(),45,ink,head,700,530),
              T("role",432,160,role.upper(),15,accent,body,700,530,"left",90),
              line("rule",432,210,920,210,accent,2)] + contacts(435,260,ink,450)

    # 06 — Teal gallery, vertical title
    elif family == 5:
        o += [rect("background",0,0,W,H,light), rect("left",0,0,230,H,dark), rect("rail",230,0,18,H,accent),
              rect("gallery",720,55,275,490,"transparent",1,0,20,accent,3)]
        o += logo_mark("logo",115,120,95,accent2,dark,spec["logo_kind"])
        o += [T("company",45,240,company.upper(),22,white,head,700,140,"center",30),
              T("name",310,82,person.upper(),43,ink,head,700,385),
              T("role",312,145,role.upper(),15,accent,body,700,385,"left",75)] + contacts(315,245,ink,350)
        o += [line("art1",760,120,950,420,accent,5,.8), line("art2",950,120,760,420,accent2,2,.7)]

    # 07 — Espresso copper top/bottom architecture
    elif family == 6:
        o += [rect("background",0,0,W,H,light), rect("top",0,0,W,180,dark), rect("bottom",0,500,W,100,dark),
              rect("copper",0,174,W,8,accent)]
        o += logo_mark("logo",115,90,92,accent2,dark,spec["logo_kind"])
        o += [T("company",205,65,company.upper(),24,white,head,700,340,"left",45),
              T("name",110,235,person.upper(),47,ink,head,700,500),
              T("role",113,303,role.upper(),15,accent,body,700,500,"left",85),
              T("contact",110,390,"+61 423 456 789   •   hello@company.com   •   company.com",16,ink,body,500,790)]
        o += [circle("c1",900,310,105,"transparent",1,accent,5), circle("c2",900,310,62,"transparent",1,accent2,2)]

    # 08 — Pearl black minimal frame
    elif family == 7:
        o += [rect("background",0,0,W,H,dark), rect("frame",42,42,W-84,H-84,"transparent",1,0,8,accent,2),
              rect("inner",65,65,W-130,H-130,"transparent",1,0,6,accent2,1)]
        o += logo_mark("logo",525,125,90,accent2,dark,spec["logo_kind"])
        o += [T("name",180,215,person.upper(),46,white,head,700,690,"center"),
              T("role",250,282,role.upper(),15,accent,body,700,550,"center",120),
              T("company",250,338,company.upper(),20,white,head,600,550,"center",65),
              T("contact",205,420,"+61 423 456 789   •   hello@company.com   •   company.com",15,muted_dark,body,500,640,"center")]

    # 09 — Ruby side capsule
    elif family == 8:
        o += [rect("background",0,0,W,H,light), rect("ruby",0,0,420,H,dark),
              rect("capsule",70,70,280,460,"transparent",1,0,140,accent,3), circle("dot",210,300,52,accent)]
        o += logo_mark("logo",210,300,78,dark,accent,spec["logo_kind"])
        o += [T("name",500,95,person.upper(),43,ink,head,700,455),
              T("role",503,158,role.upper(),15,accent,body,700,455,"left",80),
              T("company",503,215,company.upper(),21,ink,head,700,455,"left",45)] + contacts(505,300,ink,410, gap=38)

    # 10 — Navy platinum asymmetric blocks
    elif family == 9:
        o += [rect("background",0,0,W,H,dark), rect("platinum",0,0,165,H,accent), rect("ivory",165,0,520,H,light),
              polygon("cut",[(685,0),(1050,0),(1050,600),(840,600)],"#122E52")]
        o += logo_mark("logo",825,135,100,accent2,dark,spec["logo_kind"])
        o += [T("name",225,95,person.upper(),40,ink,head,700,410),
              T("role",228,155,role.upper(),14,"#4A5565",body,700,410,"left",75),
              line("rule",228,205,595,205,"#7B8794",2)] + contacts(230,255,ink,365)
        o += [T("company",735,275,company.upper(),22,white,head,700,230,"center",35)]

    # 11 — Jade arch estate
    elif family == 10:
        o += [rect("background",0,0,W,H,light), rect("estate",0,0,390,H,dark),
              rect("arch",55,55,280,490,"transparent",1,140,140,accent,4),
              rect("arch2",80,80,230,440,"transparent",1,115,115,accent2,2)]
        o += logo_mark("logo",195,245,100,accent2,dark,spec["logo_kind"])
        o += [T("company",75,390,company.upper(),22,white,head,700,240,"center",40),
              T("name",465,90,person.upper(),43,ink,head,700,500),
              T("role",468,153,role.upper(),15,accent,body,700,500,"left",85)] + contacts(470,250,ink,430)

    # 12 — Black fuchsia foil, strong contrast
    elif family == 11:
        o += [rect("background",0,0,W,H,dark), polygon("foil1",[(0,0),(290,0),(120,H),(0,H)],accent),
              polygon("foil2",[(250,0),(335,0),(165,H),(80,H)],accent2,.92),
              rect("info",355,55,640,490,"#151217",1,0,20,accent,2)]
        o += logo_mark("logo",155,130,100,dark,accent,spec["logo_kind"])
        o += [T("company",55,250,company.upper(),22,white,head,700,220,"center",35),
              T("name",420,105,person.upper(),42,white,head,700,500),
              T("role",423,165,role.upper(),15,accent2,body,700,500,"left",85),
              line("rule",423,215,900,215,accent,2)] + contacts(425,260,white,430)

    # 13 — Cobalt gold estate, not pale-on-pale
    elif family == 12:
        o += [rect("background",0,0,W,H,dark), rect("estate",60,55,930,490,"transparent",1,0,18,accent,3),
              rect("content",430,55,560,490,light), polygon("corner",[(0,600),(0,360),(300,600)],accent,.9)]
        o += logo_mark("logo",215,175,115,accent2,dark,spec["logo_kind"])
        o += [T("company",75,310,company.upper(),24,white,head,700,285,"center",40),
              T("name",490,105,person.upper(),40,ink,head,700,440),
              T("role",492,164,role.upper(),15,accent,body,700,440,"left",80)] + contacts(495,250,ink,400)

    # 14 — Violet champagne seal / centred luxury
    elif family == 13:
        o += [rect("background",0,0,W,H,dark), circle("seal_outer",525,300,235,"transparent",1,accent,4),
              circle("seal_inner",525,300,205,"transparent",1,accent2,1)]
        o += logo_mark("logo",525,150,82,accent2,dark,spec["logo_kind"])
        o += [T("name",185,235,person.upper(),43,white,head,700,680,"center"),
              T("role",250,300,role.upper(),14,accent2,body,700,550,"center",120),
              T("company",250,352,company.upper(),19,white,head,600,550,"center",60),
              T("contact",215,425,"+61 423 456 789   •   hello@company.com   •   company.com",14,muted_dark,body,500,620,"center")]

    # 15 — Forest antique border / offset content
    elif family == 14:
        o += [rect("background",0,0,W,H,light), rect("forest",0,0,300,H,dark),
              rect("border",330,45,670,510,"transparent",1,0,4,accent,4),
              line("vline",365,80,365,520,accent2,2)]
        o += logo_mark("logo",150,135,100,accent2,dark,spec["logo_kind"])
        o += [T("company",45,255,company.upper(),22,white,head,700,210,"center",35),
              T("name",420,95,person.upper(),42,ink,head,700,500),
              T("role",423,155,role.upper(),15,accent,body,700,500,"left",80)] + contacts(425,250,ink,430)

    # 16 — Scarlet editorial with horizontal identity strip
    elif family == 15:
        o += [rect("background",0,0,W,H,light), rect("scarlet",0,0,W,220,dark),
              rect("gold",0,214,W,9,accent), rect("nameplate",95,270,860,245,"#FFFFFF",1,0,14,"#E6D6B5",2)]
        o += logo_mark("logo",120,110,88,accent2,dark,spec["logo_kind"])
        o += [T("company",205,80,company.upper(),25,white,head,700,500,"left",45),
              T("name",150,305,person.upper(),43,ink,head,700,420),
              T("role",153,365,role.upper(),15,accent,body,700,420,"left",85),
              T("contact",585,310,"+61 423 456 789\nhello@company.com\nwww.company.com\nMelbourne, Australia",16,ink,body,500,300)]

    # 17 — Petrol column architecture
    elif family == 16:
        o += [rect("background",0,0,W,H,dark), rect("column",100,0,125,H,accent), rect("column2",225,0,40,H,accent2,.75),
              rect("content",335,60,650,480,light,1,0,22)]
        o += logo_mark("logo",165,155,90,dark,accent,spec["logo_kind"])
        o += [T("company",90,300,company.upper(),20,white,head,700,185,"center",30),
              T("name",405,110,person.upper(),42,ink,head,700,500),
              T("role",408,170,role.upper(),15,accent,body,700,500,"left",80)] + contacts(410,260,ink,430)

    # 18 — Mocha pearl studio, warm but readable
    elif family == 17:
        o += [rect("background",0,0,W,H,"#F6F0E8"), rect("mocha",0,0,470,H,dark),
              circle("pearl",235,300,180,soft,.20), circle("ring",235,300,145,"transparent",1,accent,3)]
        o += logo_mark("logo",235,220,100,accent2,dark,spec["logo_kind"])
        o += [T("company",95,365,company.upper(),23,white,head,700,280,"center",40),
              T("name",545,90,person.upper(),41,ink,head,700,420),
              T("role",548,150,role.upper(),15,"#7B5D4C",body,700,420,"left",80),
              line("rule",548,200,935,200,accent,2)] + contacts(550,250,ink,390)

    # 19 — Onyx cyan foil tech-luxury
    elif family == 18:
        o += [rect("background",0,0,W,H,dark), polygon("cyan_cut",[(0,0),(290,0),(470,H),(180,H)],accent,.88),
              polygon("cyan_cut2",[(40,0),(120,0),(300,H),(220,H)],accent2,.50),
              rect("content",465,45,540,510,"#0F151A",1,0,16,accent,2)]
        o += logo_mark("logo",210,150,100,dark,accent,spec["logo_kind"])
        o += [T("company",85,285,company.upper(),22,white,head,700,245,"center",35),
              T("name",525,105,person.upper(),40,white,head,700,430),
              T("role",528,165,role.upper(),15,accent,body,700,430,"left",80)] + contacts(530,255,white,390)

    # 20 — Graphite rose salon / stepped editorial
    else:
        o += [rect("background",0,0,W,H,light), rect("graphite",0,0,315,H,dark),
              rect("step1",315,0,145,115,accent), rect("step2",315,115,95,115,accent2),
              rect("step3",315,230,55,115,soft), line("rose_rule",400,505,970,505,accent,4)]
        o += logo_mark("logo",155,145,100,accent2,dark,spec["logo_kind"])
        o += [T("company",55,270,company.upper(),22,white,head,700,210,"center",35),
              T("name",480,85,person.upper(),43,ink,head,700,470),
              T("role",483,148,role.upper(),15,accent,body,700,470,"left",85)] + contacts(485,245,ink,420)

    # Premium finish is visualised subtly and ALWAYS behind content.
    # Gloss = restrained sheen, Matte = no washout, Soft-touch = subtle depth,
    # Foil = metallic rules. This prevents text from becoming pale/invisible.
    finish = spec.get("finish", "gloss")
    finish_art = []
    if finish == "gloss":
        finish_art = [
            rect("premium_gloss", 760 + (i % 4)*35, -120, 105, 840, "#FFFFFF", .030, 18+(i%3)*4),
            circle("premium_gloss_glow", 930, 70, 170, "#FFFFFF", .018),
        ]
    elif finish == "matte":
        finish_art = [rect("premium_matte_depth", 0, 0, W, H, "#000000", .018)]
    elif finish == "soft-touch":
        finish_art = [rect("premium_soft_touch", 0, 0, W, H, "#000000", .026)]
    elif finish == "foil":
        finish_art = [
            line("premium_foil_top", 42, 32, W-42, 32, accent, 3, .92),
            line("premium_foil_bottom", 42, H-32, W-42, H-32, accent2, 2, .80),
        ]
    if o and finish_art:
        o = [o[0]] + finish_art + o[1:]
    return o

def back_layout(spec):
    dark, light, accent, accent2, soft = spec["colors"]
    _, _, _, company = spec["industry"]
    head_font, body_font = spec["fonts"]
    kind = spec["back_layout"]
    o = [rect("back_background", 0, 0, W, H, dark if spec["tier"] == "premium" else light)]
    fg = light if spec["tier"] == "premium" else dark

    if kind == 0:
        o += logo_mark("back_logo", 525, 250, 170, accent, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
        o += [text("back_company", 225, 390, company, 31, fg, head_font, 700, 600, "center", 80), text("back_web", 275, 455, "www.company.com", 18, accent2 if spec["tier"]=="premium" else accent, body_font, 600, 500, "center")]
    elif kind == 1:
        o += [rect("back_band", 0, 230, W, 140, accent)]
        o += logo_mark("back_logo", 525, 160, 120, accent2, dark, spec["logo_kind"])
        o += [text("back_company", 225, 275, company, 32, dark, head_font, 750, 600, "center")]
    elif kind == 2:
        o += [rect("back_frame", 50, 50, 950, 500, "transparent", 1, 0, 12, accent, 4)]
        o += logo_mark("back_logo", 525, 245, 150, accent2, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
        o += [text("back_web", 275, 405, "www.company.com", 19, fg, body_font, 600, 500, "center")]
    elif kind == 3:
        o += [polygon("back_diag", [(0,0),(610,0),(420,H),(0,H)], accent, .96)]
        o += logo_mark("back_logo", 210, 230, 150, dark, accent, spec["logo_kind"])
        o += [text("back_company", 565, 190, company, 34, fg, head_font, 750, 400), text("back_web", 568, 265, "company.com", 19, accent2, body_font, 600)]
    elif kind == 4:
        for n in range(7):
            o.append(rect(f"back_bar{n}", 0, n*90, W, 45, accent if n%2==0 else accent2, .18))
        o += logo_mark("back_logo", 525, 250, 160, accent, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
    elif kind == 5:
        o += [circle("back_halo", 525, 300, 230, accent, .18), circle("back_halo2", 525, 300, 165, "transparent", 1, accent2, 3)]
        o += logo_mark("back_logo", 525, 285, 145, accent2, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
        o += [text("back_company", 250, 420, company, 27, fg, head_font, 700, 550, "center")]
    elif kind == 6:
        o += [rect("back_left", 0, 0, 330, H, accent), rect("back_rail", 330, 0, 14, H, accent2)]
        o += logo_mark("back_logo", 165, 220, 145, dark, accent, spec["logo_kind"])
        o += [text("back_company", 430, 210, company, 36, fg, head_font, 750, 500), text("back_web", 433, 290, "www.company.com", 19, accent2, body_font, 600)]
    elif kind == 7:
        o += [rect("back_card", 110, 85, 830, 430, light, .08 if spec["tier"]=="premium" else .75, 0, 26, accent, 2)]
        o += logo_mark("back_logo", 525, 225, 140, accent, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
        o += [text("back_company", 240, 380, company, 30, fg, head_font, 700, 570, "center")]
    elif kind == 8:
        o += [rect("back_top", 0, 0, W, 120, accent), rect("back_bottom", 0, 480, W, 120, accent2, .8)]
        o += logo_mark("back_logo", 525, 260, 155, accent, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
        o += [text("back_web", 275, 385, "www.company.com", 19, fg, body_font, 600, 500, "center")]
    else:
        o += motif_layers((spec["motif"]+7)%20, accent, accent2, soft, dark, light, spec["index"]+71)
        o += logo_mark("back_logo", 210, 250, 145, accent2, dark if spec["tier"]=="premium" else light, spec["logo_kind"])
        o += [text("back_company", 430, 200, company, 34, fg, head_font, 750, 500), text("back_web", 433, 285, "www.company.com", 19, accent, body_font, 600)]

    # Finish artwork must never sit above text/logo/contact content.
    back_finish = finish_layers(spec["finish"], accent, accent2, dark, light, spec["index"]+13)
    if back_finish:
        o = [o[0]] + back_finish + o[1:]
    return o


def svg_preview(objects, background="#ffffff"):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="{escape(background)}"/>']
    for o in objects:
        typ = o.get("type")
        opacity = o.get("opacity", 1)
        if typ == "rect":
            x,y,w,h = o.get("left",0),o.get("top",0),o.get("width",0),o.get("height",0)
            fill = o.get("fill") or "none"; stroke=o.get("stroke") or "none"; sw=o.get("strokeWidth",0); rx=o.get("rx",0); ang=o.get("angle",0)
            tr = f' transform="rotate({ang} {x+w/2} {y+h/2})"' if ang else ""
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{escape(str(fill))}" stroke="{escape(str(stroke))}" stroke-width="{sw}" opacity="{opacity}"{tr}/>')
        elif typ == "circle":
            r=o.get("radius",0); cx=o.get("left",0)+r; cy=o.get("top",0)+r; fill=o.get("fill") or "none"; stroke=o.get("stroke") or "none"; sw=o.get("strokeWidth",0)
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{escape(str(fill))}" stroke="{escape(str(stroke))}" stroke-width="{sw}" opacity="{opacity}"/>')
        elif typ == "line":
            x1,y1,x2,y2=o.get("points",[0,0,0,0]); stroke=o.get("stroke") or "#000"; sw=o.get("strokeWidth",1)
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{escape(str(stroke))}" stroke-width="{sw}" opacity="{opacity}"/>')
        elif typ == "polygon":
            pts=" ".join(f'{p["x"]},{p["y"]}' for p in o.get("points",[])); fill=o.get("fill") or "none"; stroke=o.get("stroke") or "none"; sw=o.get("strokeWidth",0)
            out.append(f'<polygon points="{pts}" fill="{escape(str(fill))}" stroke="{escape(str(stroke))}" stroke-width="{sw}" opacity="{opacity}"/>')
        elif typ == "path":
            d=o.get("path",""); fill=o.get("fill") or "none"; stroke=o.get("stroke") or "none"; sw=o.get("strokeWidth",0)
            out.append(f'<path d="{escape(str(d))}" fill="{escape(str(fill))}" stroke="{escape(str(stroke))}" stroke-width="{sw}" opacity="{opacity}"/>')
        elif typ in ("text","i-text","textbox"):
            x,y=o.get("left",0),o.get("top",0)+o.get("fontSize",20); fill=o.get("fill") or "#111"; fs=o.get("fontSize",20); ff=o.get("font") or "Arial"; fw=o.get("fontWeight",400)
            out.append(f'<text x="{x}" y="{y}" fill="{escape(str(fill))}" font-size="{fs}" font-family="{escape(str(ff))}" font-weight="{fw}" opacity="{opacity}">{escape(str(o.get("text","")))}</text>')
    out.append('</svg>')
    return ''.join(out)


def structural_signature(objects):
    # Ignore colors and literal text; detect layouts that are structurally the same.
    rows=[]
    for o in objects:
        typ=o.get("type")
        row=[typ, round(float(o.get("left",0))/10), round(float(o.get("top",0))/10), round(float(o.get("angle",0))/5)]
        if typ=="rect": row += [round(float(o.get("width",0))/10), round(float(o.get("height",0))/10), round(float(o.get("rx",0))/5)]
        elif typ=="circle": row += [round(float(o.get("radius",0))/5)]
        elif typ=="line": row += [round(float(v)/10) for v in o.get("points",[0,0,0,0])]
        elif typ=="polygon":
            # Polygon geometry is part of the composition.  The old validator only
            # counted vertices, so completely different wedges/diagonals with the
            # same number of points were falsely reported as structural duplicates.
            pts = o.get("points", [])
            row += [len(pts)]
            for pt in pts:
                row += [
                    round(float(pt.get("x", 0)) / 10),
                    round(float(pt.get("y", 0)) / 10),
                ]
        elif typ=="path": row += [hashlib.sha1(str(o.get("path","")).encode()).hexdigest()[:8]]
        elif typ in ("text","i-text","textbox"): row += [round(float(o.get("fontSize",0))/2), o.get("textAlign","left")]
        rows.append(row)
    return hashlib.sha1(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def build_specs(tier):
    palettes = STANDARD_PALETTES if tier == "standard" else PREMIUM_PALETTES
    names = STYLE_NAMES_STANDARD if tier == "standard" else STYLE_NAMES_PREMIUM
    # Premium: deliberate luxury print-finish mix. Standard: predominantly normal/clean,
    # with only a small minority carrying a subtle matte/gloss label.
    premium_finishes = [
        "gloss", "gloss", "foil", "matte", "soft-touch",
        "gloss", "matte", "soft-touch", "foil", "gloss",
        "matte", "foil", "gloss", "soft-touch", "matte",
        "gloss", "soft-touch", "matte", "foil", "gloss",
    ]
    standard_finishes = ["standard"] * 10
    specs=[]

    # V8 uniqueness strategy:
    # The old coprime formula repeated the SAME (layout/motif/back/variant)
    # family every 20 Standard cards.  That is why Standard #21 collided
    # with Standard #1.  Build the axes from mixed-radix positions instead.
    # For the retained 80 Standard cards, (layout, motif) itself is unique,
    # so the FRONT composition cannot repeat. Premium 001-020 is unique too.
    for i in range(100):
        _, dark, light, accent, accent2, soft = palettes[(i*7 + (3 if tier=="premium" else 0)) % len(palettes)]

        layout = i % 10
        block = i // 10
        motif = (block * 2 + (i % 2) + (1 if tier == "premium" else 0)) % 20
        logo_kind = ((i // 2) + block + (2 if tier == "premium" else 0)) % 5
        back_layout = ((i * 3) + block + (6 if tier == "premium" else 1)) % 10
        variant = ((i // 10) + (i % 5)) % 5

        specs.append({
            "index": i,
            "tier": tier,
            "name": names[i],
            "colors": (dark, light, accent, accent2, soft),
            "industry": INDUSTRIES[(i*11 + (5 if tier=="premium" else 0)) % len(INDUSTRIES)],
            "fonts": (PREMIUM_FONT_PAIRS[i % len(PREMIUM_FONT_PAIRS)] if tier == "premium" else FONT_PAIRS[(i*13) % len(FONT_PAIRS)]),
            "layout": layout,
            "back_layout": back_layout,
            "motif": motif,
            "logo_kind": logo_kind,
            "finish": (premium_finishes[i % 20] if tier == "premium" else standard_finishes[i % len(standard_finishes)]),
            "variant": variant,
            "composition_key": f"{tier}-L{layout:02d}-M{motif:02d}-G{logo_kind:02d}-B{back_layout:02d}-V{variant}",
        })
    return specs


def _hex_rgb(value):
    value = str(value or "").strip()
    if not value.startswith("#"):
        return None
    h = value[1:]
    if len(h) == 3:
        h = "".join(c*2 for c in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[n:n+2], 16) for n in (0, 2, 4))
    except ValueError:
        return None


def _luminance(value):
    rgb = _hex_rgb(value)
    if not rgb:
        return None
    vals=[]
    for c in rgb:
        c=c/255.0
        vals.append(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4)
    return .2126*vals[0] + .7152*vals[1] + .0722*vals[2]


def _contrast(a, b):
    la, lb = _luminance(a), _luminance(b)
    if la is None or lb is None:
        return 99
    hi, lo = max(la, lb), min(la, lb)
    return (hi+.05)/(lo+.05)


def normalize_text_visibility(objects, dark, light):
    """V8: preserve the layout-selected text colour.

    front_layout/back_layout already know whether each text object is sitting on
    a dark or light panel.  The old x-position heuristic changed correct white
    text on full-dark/glass layouts to dark text, which caused the apparently
    missing names/details seen in Premium cards.  Keep those deliberate colours
    and only enforce editor-safe visibility/editability metadata.
    """
    for obj in objects:
        if obj.get("type") not in ("text", "i-text", "textbox"):
            continue
        obj["opacity"] = 1
        obj["visible"] = True
        obj["selectable"] = True
        obj["evented"] = True
        obj["customerEditable"] = True
        obj["locked"] = False
        obj["fontFamily"] = obj.get("fontFamily") or obj.get("font") or "Inter"
        obj["font"] = obj.get("font") or obj["fontFamily"]
    return objects



def finalize_editable_layers(objects):
    """Make the generated artwork behave like native editor content.

    No raster card image is placed over the design. Shapes, rules, logo marks and
    text remain separate Fabric objects. Text receives conservative dimensions so
    the catalogue preview and editor use the same wrapping/alignment.
    """
    for z, obj in enumerate(objects):
        obj["zIndex"] = z
        obj["visible"] = True
        obj["selectable"] = True
        obj["evented"] = True
        obj["customerEditable"] = True
        obj["editable"] = True
        obj["locked"] = False
        obj["excludeFromExport"] = False
        if obj.get("type") in ("text", "i-text", "textbox"):
            obj["opacity"] = 1
            obj["fontFamily"] = obj.get("fontFamily") or obj.get("font") or "Inter"
            obj["font"] = obj.get("font") or obj["fontFamily"]
            obj["lineHeight"] = max(1.05, float(obj.get("lineHeight", 1.15) or 1.15))
            obj["splitByGrapheme"] = False
            obj["textBackgroundColor"] = ""
    return objects


def validate_no_text_collisions(payload, label):
    """Reject obvious text-on-text collisions before database replacement.

    This intentionally checks text only. Decorative vector elements may overlap by
    design, while names/contact lines must not sit on top of each other.
    """
    for page in payload.get("pages", []):
        texts=[]
        for obj in page.get("objects", []):
            if obj.get("type") not in ("text", "i-text", "textbox"):
                continue
            x=float(obj.get("left",0)); y=float(obj.get("top",0))
            w=float(obj.get("width",0) or 0); fs=float(obj.get("fontSize",18) or 18)
            value=str(obj.get("text", ""))
            lines=max(1, value.count("\\n")+1)
            h=fs*float(obj.get("lineHeight",1.15) or 1.15)*lines
            # Use an inset box so nearby labels/rules are allowed, but actual
            # overprinting of readable text is rejected.
            texts.append((obj.get("id"), x+4, y+3, x+max(8,w)-4, y+max(8,h)-3))
        for i,a in enumerate(texts):
            for b in texts[i+1:]:
                if a[2] <= b[1] or b[2] <= a[1] or a[4] <= b[3] or b[4] <= a[3]:
                    continue
                # Contact block lines can be close but should still not overlap.
                raise CommandError(f"Text collision detected for {label}: {page.get('label')} / {a[0]} vs {b[0]}")
    return True


def enforce_canvas_alignment(objects):
    """Keep every editable object inside the 1050x600 print canvas.

    This is intentionally conservative: it does not redesign a composition; it
    only prevents text boxes from running outside the card and gives every text
    object an explicit width.  That makes the SVG preview and Fabric editor agree.
    """
    for obj in objects:
        typ = obj.get("type")
        if typ not in ("text", "i-text", "textbox"):
            continue
        x = max(18.0, min(float(obj.get("left", 18)), W - 48.0))
        y = max(18.0, min(float(obj.get("top", 18)), H - 48.0))
        fs = max(11.0, min(float(obj.get("fontSize", 18)), 58.0))
        obj["left"], obj["top"], obj["fontSize"] = round(x,2), round(y,2), round(fs,2)
        maxw = max(48.0, W - x - 24.0)
        requested = float(obj.get("width", maxw) or maxw)
        obj["width"] = round(min(requested, maxw), 2)
        obj["splitByGrapheme"] = False
        obj["minWidth"] = min(40, obj["width"])
    return objects


def validate_template_geometry(payload, label):
    """Fail the dry-run before DB changes if a generated card is unsafe."""
    for page in payload.get("pages", []):
        for obj in page.get("objects", []):
            if obj.get("type") not in ("text", "i-text", "textbox"):
                continue
            x=float(obj.get("left",0)); y=float(obj.get("top",0)); w=float(obj.get("width",0)); fs=float(obj.get("fontSize",0))
            if x < 0 or y < 0 or x+w > W+0.5 or y+fs*1.35 > H+0.5:
                raise CommandError(f"Alignment validation failed for {label}: {page.get('label')} / {obj.get('id')}")
            if not str(obj.get("text","")).strip():
                raise CommandError(f"Empty editable text detected for {label}: {page.get('label')} / {obj.get('id')}")
    return True

def build_payload(spec):
    dark, light, *_ = spec["colors"]
    front = finalize_editable_layers(enforce_canvas_alignment(normalize_text_visibility(distinctive_front_layout(spec), dark, light)))
    back = finalize_editable_layers(enforce_canvas_alignment(normalize_text_visibility(back_layout(spec), dark, light)))
    # Ensure exact structural duplicates are impossible.
    return {
        "version": 3,
        "templateType": "editable-master",
        "reconstructed": True,
        "reference_collection": "ZenVibe reference-inspired editable business cards",
        "raster_overlay": False,
        "business_card_library": True,
        "business_card_library_version": VERSION,
        "business_card_code": f"zv{VERSION}-{spec['tier']}-{spec['index']+1:03d}",
        "collection": "Premium Business Cards" if spec["tier"]=="premium" else "Standard Business Cards",
        "style_name": spec["name"],
        "finish_visual": (("luxury-" + spec["finish"]) if spec["tier"] == "premium" else "standard-clean"),
        "document": {"width": W, "height": H, "physical": {"width": 3.5, "height": 2.0, "unit": "in"}},
        "pages": [
            {"label": "Front", "background": next((x.get("fill") for x in front if x.get("id")=="background"), spec["colors"][1]), "objects": front, "svg": svg_preview(front, next((x.get("fill") for x in front if x.get("id")=="background"), spec["colors"][1]))},
            {"label": "Back", "background": next((x.get("fill") for x in back if x.get("id")=="background"), spec["colors"][0]), "objects": back, "svg": svg_preview(back, next((x.get("fill") for x in back if x.get("id")=="background"), spec["colors"][0]))},
        ],
        "editable": True,
        "design_signature": structural_signature(front),
        "composition_key": spec["composition_key"],
    }


class Command(BaseCommand):
    help = (
        "Create one shared 100-template editable Business Card library: "
        "20 Premium first, then 80 Standard. Both Business Card products use the same master library."
    )

    def add_arguments(self, parser):
        parser.add_argument("--standard-product-id", type=int, required=True)
        parser.add_argument("--premium-product-id", "--luxury-product-id",
                            dest="premium_product_id", type=int, required=True)
        parser.add_argument(
            "--master-product-id", type=int, default=None,
            help="Optional canonical product that stores all 100 templates. "
                 "Default: Standard product, matching the shared-library view logic."
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--replace-generated", action="store_true",
            help="Compatibility flag only. Generated Business Card libraries are always replaced "
                 "so the final library remains exactly 100 templates."
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        standard = Product.objects.select_related("category").filter(
            id=opts["standard_product_id"]
        ).first()
        premium = Product.objects.select_related("category").filter(
            id=opts["premium_product_id"]
        ).first()

        if not standard:
            raise CommandError(f"Standard product #{opts['standard_product_id']} not found.")
        if not premium:
            raise CommandError(f"Premium product #{opts['premium_product_id']} not found.")
        if standard.id == premium.id:
            raise CommandError("Standard and Premium product IDs must be different.")

        master_id = opts.get("master_product_id") or standard.id
        master = Product.objects.select_related("category").filter(id=master_id).first()
        if not master:
            raise CommandError(f"Master product #{master_id} not found.")
        if master.id not in (standard.id, premium.id):
            raise CommandError(
                "For safety the master product must be either the Standard or Premium Business Card product."
            )

        # Exact requested library:
        #   positions 001-020 = Premium designs 001-020
        #   positions 021-100 = Standard designs 001-080
        selected = []
        for spec in build_specs("premium")[:20]:
            selected.append(("premium", spec, build_payload(spec)))
        for spec in build_specs("standard")[:80]:
            selected.append(("standard", spec, build_payload(spec)))

        # Validate all retained designs before touching the DB.
        signatures = set()
        composition_keys = set()
        for tier, spec, payload in selected:
            sig = payload["design_signature"]
            key = payload["composition_key"]
            if key in composition_keys:
                raise CommandError(
                    f"Composition-family duplicate detected: {tier} #{spec['index']+1} {spec['name']}"
                )
            if sig in signatures:
                raise CommandError(
                    f"Structural duplicate detected: {tier} #{spec['index']+1} {spec['name']}"
                )
            composition_keys.add(key)
            signatures.add(sig)
            validate_template_geometry(payload, f"{tier} #{spec['index']+1} {spec['name']}")

            # Force explicit editable-master metadata on every retained template.
            payload["editable"] = True
            payload["templateType"] = "editable-master"
            payload["editorNative"] = True
            payload["editorSchema"] = "fabric-primitives-v1"
            payload["shared_business_card_library"] = True
            payload["shared_business_card_master_product_id"] = master.id

            # Preserve original tier while adding deterministic shared display order.
            # Premium 1-20 sort first; Standard 1-80 sort second.
            display_order = (
                spec["index"] + 1
                if tier == "premium"
                else 20 + spec["index"] + 1
            )
            payload["business_card_display_order"] = display_order
            payload["business_card_tier"] = tier
            payload["business_card_category"] = (
                "Premium Business Cards" if tier == "premium"
                else "Standard Business Cards"
            )

            # Ensure every existing visible layer remains customer editable.
            for page in payload.get("pages", []):
                for obj in page.get("objects", []):
                    obj["customerEditable"] = True
                    obj["editable"] = True
                    obj["locked"] = False
                    obj["selectable"] = True
                    obj["evented"] = True

        if opts["dry_run"]:
            for tier, spec, payload in selected:
                self.stdout.write(
                    f"DRY RUN {payload['business_card_display_order']:03d} "
                    f"{tier:8} source={spec['index']+1:03d} · "
                    f"{spec['name']} · {spec['finish']} · "
                    f"{payload['design_signature'][:10]}"
                )
            self.stdout.write(self.style.SUCCESS(
                "DRY RUN OK: 100 UNIQUE, aligned, shared editable Business Card templates "
                "(20 Premium first + 80 Standard); Front/Back preserved; database unchanged."
            ))
            transaction.set_rollback(True)
            return

        # Always remove previous generated Business Card batches before inserting
        # the new library. Re-running this command can therefore NEVER accumulate
        # another 100 templates.
        target_ids = {standard.id, premium.id, master.id}
        generated_q = (
            Q(json_data__business_card_library=True)
            | Q(json_data__shared_business_card_library=True)
            | Q(json_data__business_card_library_version__isnull=False)
            | Q(json_data__business_card_code__startswith="zv")
            | Q(json_data__reference_collection__icontains="business card")
        )
        old = DesignTemplate.objects.filter(
            product_id__in=target_ids
        ).filter(generated_q)

        old_count = old.count()
        self.stdout.write(
            f"Removing previous generated Business Card templates: {old_count}"
        )
        old.delete()

        for tier, spec, payload in selected:
            order = payload["business_card_display_order"]
            tier_label = "Premium" if tier == "premium" else "Standard"

            # Prefix with a zero-padded global order so ordinary name ordering also
            # gives Premium 001-020 followed by Standard 021-100.
            template_name = (
                f"BC {order:03d} · {tier_label} · "
                f"{spec['name']} · {spec['finish'].title()}"
            )

            # Store ALL 100 records on one canonical product only.
            obj = DesignTemplate.objects.filter(
                product=master,
                json_data__business_card_code=payload["business_card_code"],
            ).order_by("id").first()

            if obj is None:
                obj = DesignTemplate(product=master)

            obj.name = template_name
            obj.json_data = payload
            obj.is_active = True
            obj.preview.save(
                f"business_cards_shared/{order:03d}_{payload['business_card_code']}.svg",
                ContentFile(payload["pages"][0]["svg"].encode("utf-8")),
                save=False,
            )
            obj.save()

        # Exact-count protection.
        final_generated = DesignTemplate.objects.filter(
            product_id__in=target_ids
        ).filter(
            Q(json_data__business_card_library=True)
            | Q(json_data__shared_business_card_library=True)
        )
        final_count = final_generated.count()
        master_count = final_generated.filter(product=master).count()

        if final_count != 100 or master_count != 100:
            raise CommandError(
                f"Final library check failed: {final_count} generated Business Card "
                f"templates found; {master_count} on master product #{master.id}. "
                f"Expected exactly 100."
            )

        orders = list(
            final_generated.filter(product=master)
            .values_list("json_data__business_card_display_order", flat=True)
        )
        actual_orders = {int(x) for x in orders if x is not None}
        if len(orders) != 100 or actual_orders != set(range(1, 101)):
            raise CommandError(
                "Business Card display-order check failed. Expected exactly one "
                "template at each position 001-100."
            )

        # Both sellable products continue to use the universal editor and the
        # same 3.5 x 2.0 inch physical card geometry.
        for product in (standard, premium):
            product.customizer_mode = "editor"
            product.width = W
            product.height = H
            product.orientation = "landscape"
            if hasattr(product, "print_width_in"):
                product.print_width_in = 3.5
            if hasattr(product, "print_height_in"):
                product.print_height_in = 2.0
            product.save()

        self.stdout.write(self.style.SUCCESS(
            f"Created shared Business Card library on master product #{master.id}: "
            "100 total = 20 Premium + 80 Standard. "
            "Premium displays first. All 100 passed structural uniqueness and canvas-alignment validation; every template has editable Front/Back pages."
        ))
