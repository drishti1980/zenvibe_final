"""Repair the actual rendered gallery previews for classic marketing libraries.

This command never deletes templates, changes their object layout, or
re-generates master JSON. It only builds an SVG thumbnail from existing
editable Fabric primitives. Windows does not need CairoSVG.

python manage.py refresh_marketing_previews --dry-run
python manage.py refresh_marketing_previews --apply
python manage.py refresh_marketing_previews --product-id 170 --apply
"""
import base64
import json
from html import escape

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from designer.models import DesignTemplate
from designer.management.commands.seed_100_marketing_material_templates import GENERATOR_ID


def original_background(objects, width, height):
    for obj in objects:
        if not isinstance(obj, dict) or not obj.get("backgroundAsset"):
            continue
        src = str(obj.get("src") or obj.get("baseSrc") or "")
        if src.startswith("data:image/svg+xml;base64,"):
            try:
                svg = base64.b64decode(src.split(",", 1)[1], validate=True).decode("utf-8")
                if "<svg" in svg and "</svg>" in svg:
                    return svg
            except (ValueError, UnicodeDecodeError):
                pass
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d"><rect width="100%%" height="100%%" '
        'fill="#FFFFFF"/></svg>'
    ) % (width, height, width, height)


def svg_preview(background, objects, width, height):
    """Render a complete SVG thumbnail without optional Django commands or Cairo.

    The original marketing seeder stores the background as an SVG data image
    and puts editable copy/photos in independent Fabric objects. Rebuilding the
    gallery from those same layers avoids the old background-only thumbnails.
    """
    prefix, sep, _ = background.rpartition("</svg>")
    if not sep:
        raise ValueError("Background image is not a complete SVG")
    rendered = [prefix]
    for obj in objects:
        if not isinstance(obj, dict) or obj.get("backgroundAsset") or obj.get("visible") is False:
            continue
        kind = obj.get("type")
        x = float(obj.get("left", 0))
        y = float(obj.get("top", 0))
        w = float(obj.get("width", 0))
        h = float(obj.get("height", 0))
        opacity = float(obj.get("opacity", 1))
        if kind == "image":
            src = str(obj.get("src") or obj.get("baseSrc") or "")
            if src.startswith(("data:image/jpeg;base64,", "data:image/png;base64,",
                               "data:image/svg+xml;base64,", "data:image/webp;base64,")):
                rendered.append(
                    '<image x="%g" y="%g" width="%g" height="%g" '
                    'href="%s" preserveAspectRatio="xMidYMid slice" opacity="%g"/>' %
                    (x, y, w, h, escape(src, quote=True), opacity)
                )
        elif kind == "rect":
            rendered.append(
                '<rect x="%g" y="%g" width="%g" height="%g" '
                'fill="%s" opacity="%g" />' %
                (x, y, w, h, escape(str(obj.get("fill") or "none"), quote=True), opacity)
            )
        elif kind in ("textbox", "text", "i-text"):
            size = max(1, float(obj.get("fontSize", 20)))
            align = obj.get("textAlign", "left")
            anchor = {"center": "middle", "right": "end"}.get(align, "start")
            tx = x + (w / 2 if align == "center" else w if align == "right" else 0)
            font = escape(str(obj.get("fontFamily") or obj.get("font") or "Arial"), quote=True)
            color = escape(str(obj.get("fill") or "#202020"), quote=True)
            weight = escape(str(obj.get("fontWeight") or "normal"), quote=True)
            line_height = max(0.7, float(obj.get("lineHeight") or 1.16))
            max_chars = max(7, int(max(w, size) / (size * .60)))
            lines = []
            for paragraph in str(obj.get("text") or "").split("\n"):
                line = ""
                for word in paragraph.split():
                    if line and len(line) + len(word) + 1 > max_chars:
                        lines.append(line)
                        line = word
                    else:
                        line = (line + " " + word).strip()
                lines.append(line)
            rendered.append(
                '<text x="%g" y="%g" font-size="%g" font-family="%s" '
                'font-weight="%s" text-anchor="%s" fill="%s" opacity="%g">' %
                (tx, y + size, size, font, weight, anchor, color, opacity)
            )
            for i, value in enumerate(lines):
                rendered.append(
                    '<tspan x="%g" dy="%g">%s</tspan>' %
                    (tx, 0 if i == 0 else size * line_height, escape(value))
                )
            rendered.append("</text>")
    rendered.append("</svg>")
    return "".join(rendered)



class Command(BaseCommand):
    help="Rebuild marketing previews from editable pages without touching template masters."

    def add_arguments(self, parser):
        modes=parser.add_mutually_exclusive_group(required=True)
        modes.add_argument("--dry-run",action="store_true")
        modes.add_argument("--apply",action="store_true")
        parser.add_argument("--product-id",type=int)
    
    def handle(self,*args,**opts):
        qs=DesignTemplate.objects.filter(is_active=True).order_by("pk")
        if opts["product_id"]:
            qs=qs.filter(product_id=opts["product_id"])
        count=0
        malformed=0
        # Materialize just PKs before updating rows; SQLite must not hold a
        # streaming SELECT cursor open while previews are saved.
        template_ids=list(qs.values_list("pk",flat=True))
        for pk in template_ids:
            template=DesignTemplate.objects.get(pk=pk)
            data=template.json_data
            if isinstance(data,str):
                try: data=json.loads(data)
                except (ValueError,TypeError):
                    malformed+=1
                    continue
            if not isinstance(data,dict):
                continue
            if data.get("generator")!=GENERATOR_ID or data.get("kind") not in (
                    "bifold","doorhanger","ticket","trifold"):
                continue
            pages=data.get("pages") or []
            if not isinstance(pages,list) or not pages or not isinstance(pages[0],dict):
                malformed+=1
                continue
            page=pages[0]
            objects=page.get("objects") or []
            if not isinstance(objects,list) or not objects:
                malformed+=1
                continue
            width=int(page.get("width") or data.get("width") or 0)
            height=int(page.get("height") or data.get("height") or 0)
            if width<=0 or height<=0:
                malformed+=1
                continue
            count+=1
            if opts["dry_run"]:
                continue
            bg=original_background(objects,width,height)
            full_svg=svg_preview(bg,objects,width,height)
            filename="marketing-complete-%s-%s.svg"%(template.product_id,template.pk)
            template.preview.save(filename,ContentFile(full_svg.encode("utf-8")),save=False)
            template.save(update_fields=["preview"])
        if malformed:
            self.stdout.write(self.style.WARNING(
                "%d invalid generated templates skipped." % malformed
            ))
        self.stdout.write(self.style.SUCCESS(
            "%s %d complete gallery previews; existing editable JSON untouched." %
            ("Would rebuild" if opts["dry_run"] else "Rebuilt", count)
        ))
        if malformed:
            raise CommandError("Some templates are malformed; repair them before marking this product complete.")
