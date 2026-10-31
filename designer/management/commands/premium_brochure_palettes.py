"""100 individually coordinated brochure colourways with contrast guarantees.

The former brochure seeders used only five BASES repeatedly: every 5th
template recycled paper, ink and muted colours, and the same twenty accents
cycled too. A valid brochure colourway is not just a random palette or a
recolour of the same layout. This module separates palette generation from
artwork geometry and gives each numbered design its own premium colour story.

Hue positions use golden-angle spacing, varied light/dark treatments and
a genre offset. Pairwise palette identities are deterministic for index 0..99.
All text combinations meet WCAG AA 4.5:1 contrast and CTA foregrounds meet
the same threshold. Colour/print fidelity still requires CMYK proofing.
No I/O, product changes or external services.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class BrochurePalette:
    paper: str
    ink: str
    muted: str
    accent: str
    on_accent: str
    family: str
    identity: str


# Alternate softly coloured stock, jewel tones, almost-black luxury shades,
# chalky pastel and saturated rich stock. Every gallery row has a recognisably
# different temperature and brightness: not 20 ivory + gold combinations.
TREATMENTS = (
    (0.32, 0.86),  # heritage coloured paper
    (0.35, 0.21),  # deep jewel
    (0.40, 0.73),  # warm muted editorial
    (0.53, 0.34),  # saturated luxury
    (0.34, 0.90),  # airy botanical
    (0.23, 0.14),  # blackened gemstone
    (0.32, 0.67),  # dusty ceramic
    (0.54, 0.27),  # velvet-colour statement
    (0.29, 0.83),  # gentle museum
    (0.26, 0.18),  # midnight classic
)
ROLES = {
    "cover": 0, "back": 1, "flap": 2, "intro": 3,
    "offer": 4, "contact": 5, "story": 6, "services": 7,
    "outside": 0, "inside": 3,
}


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def _hex_hsl(hue, saturation, lightness):
    r,g,b=colorsys.hls_to_rgb(
        (float(hue)%360)/360,
        _clamp(lightness),
        _clamp(saturation),
    )
    return "#%02X%02X%02X"%tuple(round(c*255) for c in (r,g,b))


def _rgb(color):
    token=str(color).lstrip("#")
    return tuple(int(token[i:i+2],16)/255 for i in (0,2,4))


def _luminance(color):
    channels=tuple((v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)
                   for v in _rgb(color))
    return sum(v*w for v,w in zip(channels,(.2126,.7152,.0722)))


def contrast(a,b):
    """WCAG 2.2 relative contrast; >=4.5 for ordinary brochure labels."""
    x,y=sorted((_luminance(a),_luminance(b)),reverse=True)
    return (x+.05)/(y+.05)


def text_for(background, subdued=False):
    dark=("#26333D" if subdued else "#13252E")
    light=("#E9E5DC" if subdued else "#FFFAF2")
    best=max((dark,light),key=lambda candidate:contrast(candidate,background))
    if contrast(best,background)<4.5:
        raise ValueError("Unprintable foreground/background contrast")
    return best


def _base(index,family):
    if not 0<=index<100:
        raise ValueError("Template index must be between 0 and 99")
    if family not in ("bifold","trifold"):
        raise ValueError("Only bi-fold and tri-fold palettes are supported")
    seed=0.0 if family=="bifold" else 29.4
    hue=(23.0+seed+index*137.50776405003785)%360
    sat,lum=TREATMENTS[index%len(TREATMENTS)]
    # Stable per-design hue and luminance. 100 unique paper shades and 100
    # unique accent combinations in each category, not 5/20 recycled keys.
    paper=_hex_hsl(hue,sat,lum)
    accent_hue=(hue+134+(index//10)*17)%360
    accent_sat=0.55+(index%4)*0.035
    accent_lum=(0.68 if lum<0.45 else 0.39)+(index%3)*0.025
    accent=_hex_hsl(accent_hue,accent_sat,accent_lum)
    return hue,sat,lum,paper,accent


@lru_cache(maxsize=1600)
def palette_for(index,family,role="cover"):
    """Return a matching, legible, role-specific premium colourway.

    The exact COVER paper and foil colours are never reused between design
    indices. Other brochure panels are coordinated variations of that one
    design's palette, not copies of a global fixed beige or green.
    """
    index=int(index)
    hue,sat,lum,base_paper,accent=_base(index,family)
    role_key=str(role).lower()
    depth=ROLES.get(role_key,0)
    if depth==0:
        paper=base_paper
    else:
        # Distinct but harmonious panel colours, still driven by this unique
        # index. No hardcoded ivory/green inside-page fallback.
        shift=(-1 if depth%2 else 1)*(.045+.009*(depth%3))
        panel_lum=_clamp(lum+shift,.12,.93)
        panel_sat=_clamp(sat+(.07 if depth%3==0 else -.055),.14,.65)
        paper=_hex_hsl(hue+(depth-3)*5.5,panel_sat,panel_lum)
    ink=text_for(paper)
    muted=text_for(paper,subdued=True)
    on_accent=text_for(accent)
    if contrast(ink,paper)<4.5 or contrast(muted,paper)<4.5:
        raise ValueError("Text contrast below WCAG AA")
    if contrast(on_accent,accent)<4.5:
        raise ValueError("CTA text contrast below WCAG AA")
    return BrochurePalette(
        paper=paper,ink=ink,muted=muted,
        accent=accent,on_accent=on_accent,
        family=family,
        identity=f"{family}-{index+1:03d}-{role_key}",
    )


def palette_signatures(family):
    return [
        (palette_for(i,family).paper,palette_for(i,family).accent)
        for i in range(100)
    ]


def validate_100_palettes(family):
    signatures=palette_signatures(family)
    if len(signatures)!=100 or len(set(signatures))!=100:
        raise ValueError("Repeated paper/accent palette")
    papers=[p for p,_ in signatures]
    if len(set(papers))!=100:
        raise ValueError("Repeated brochure background colour")
    accents=[a for _,a in signatures]
    if len(set(accents))!=100:
        raise ValueError("Repeated brochure accent colour")
    for i in range(100):
        color=palette_for(i,family)
        if contrast(color.paper,color.ink)<4.5:
            raise ValueError("Template %03d has unreadable headline"%(i+1))
        if contrast(color.accent,color.on_accent)<4.5:
            raise ValueError("Template %03d has unreadable CTA"%(i+1))
    return True
