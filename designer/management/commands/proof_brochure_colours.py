"""Produce visual colour proof for 100 Bi-Fold or 100 Tri-Fold templates.

No database writes, image downloads, media changes or calls to any external
website. A fast way to inspect that no cover/background/accent is recycled.
The swatches are from the SAME generator used for actual editable artwork.

    python manage.py proof_brochure_colours --family bifold
    python manage.py proof_brochure_colours --family trifold
    python manage.py proof_brochure_colours --family both
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageDraw, ImageFont

from designer.management.commands.premium_brochure_palettes import (
    palette_for, validate_100_palettes, ROLES,
)


def _font(size,bold=False):
    names=("DejaVuSans-Bold.ttf","LiberationSans-Bold.ttf","arialbd.ttf") if bold else (
        "DejaVuSans.ttf","LiberationSans-Regular.ttf","arial.ttf"
    )
    for name in names:
        try:
            return ImageFont.truetype(name,size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_palette_proof(family, role="cover"):
    validate_100_palettes(family)
    cols,rows=10,10
    cw,ch=270,160
    image=Image.new("RGB",(cols*cw,rows*ch),"#FFFFFF")
    draw=ImageDraw.Draw(image)
    title_font=_font(22,True)
    info_font=_font(15)
    for i in range(100):
        colors=palette_for(i,family,role)
        x=(i%cols)*cw
        y=(i//cols)*ch
        draw.rectangle((x,y,x+cw-1,y+ch-1),fill=colors.paper)
        draw.rectangle((x+15,y+14,x+cw-16,y+18),fill=colors.accent)
        draw.text((x+16,y+29),f"{family.upper()} {i+1:03d}",
                  font=title_font,fill=colors.ink)
        draw.text((x+16,y+67),f"PAPER  {colors.paper}",
                  font=info_font,fill=colors.muted)
        draw.text((x+16,y+88),f"FOIL   {colors.accent}",
                  font=info_font,fill=colors.muted)
        draw.rounded_rectangle((x+15,y+117,x+cw-16,y+149),
                               radius=8,fill=colors.accent)
        draw.text((x+28,y+123),"EDITABLE CALL TO ACTION",
                  font=info_font,fill=colors.on_accent)
    return image


class Command(BaseCommand):
    help="Create 100-colour palette proof sheets for premium bi-/tri-fold brochures."

    def add_arguments(self,parser):
        parser.add_argument(
            "--family",required=True,choices=("bifold","trifold","both"),
        )
        parser.add_argument(
            "--role",default="cover",choices=tuple(ROLES),
            help="Choose the brochure panel to inspect; defaults to front cover",
        )

    def handle(self,*args,**options):
        families=("bifold","trifold") if options["family"]=="both" else (options["family"],)
        folder=Path(settings.BASE_DIR)/"template_reports"
        folder.mkdir(parents=True,exist_ok=True)
        for family in families:
            image=make_palette_proof(family,options["role"])
            stamp=datetime.now().strftime("%Y%m%d-%H%M%S")
            path=folder/f"{family}_{options['role']}_100_distinct_colours_{stamp}.png"
            image.save(path,format="PNG",optimize=True)
            self.stdout.write(self.style.SUCCESS(
                f"{family} ({options['role']}): verified 100 distinct paper colours and 100 distinct "
                f"foil accents; visual proof: {path}"
            ))
