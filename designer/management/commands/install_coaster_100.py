"""Install 100 coaster templates on product 415, preserving existing records.

24 reference images must be present in designer/coaster_reference_tiles/001.jpg
through 024.jpg. The remaining 76 editable vector designs use the checked-in
coaster_artwork_v2 generator. Preview and artwork are updated together.
"""
from __future__ import annotations
import copy
import io
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product
from .coaster_artwork_v2 import artwork
from .coaster_curated_svg import _parse_svg
from .rebuild_coaster_previews import render

class Command(BaseCommand):
    help = "Install 24 luxury photo references and 76 vector coaster designs."
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--shape", choices=("circle", "square"), default="circle")
    def handle(self, *args, **opts):
        if opts["dry_run"] == opts["apply"]:
            raise CommandError("Choose exactly one of --dry-run or --apply.")
        product = Product.objects.filter(pk=415).first()
        if product is None or "coaster" not in product.name.lower():
            raise CommandError("Product 415 must exist and be a coaster.")
        templates = list(DesignTemplate.objects.filter(product_id=415,is_active=True).order_by("id"))
        if len(templates) != 100:
            raise CommandError(f"Expected 100 active templates, found {len(templates)}.")
        folder = Path(settings.BASE_DIR) / "designer" / "coaster_reference_tiles"
        references = [folder / f"{i:03d}.jpg" for i in range(1,25)]
        missing = [p.name for p in references if not p.is_file()]
        if missing:
            raise CommandError(f"Missing {len(missing)} reference JPG files in {folder}; first: {missing[:5]}. Extract the previously supplied ZIP first.")
        for template in templates:
            if not isinstance(template.json_data,dict) or not template.json_data.get("pages"):
                raise CommandError(f"Template {template.pk} missing editable pages.")
        generated = Path(settings.BASE_DIR) / "designer" / "coaster_original_svg"
        generated.mkdir(parents=True,exist_ok=True)
        staged=[]
        for index,template in enumerate(templates):
            if index < 24:
                raw=references[index].read_bytes()
                if not raw.startswith(bytes((0xFF, 0xD8))):
                    raise CommandError(f"Not a JPEG: {references[index].name}")
                staged.append((template,index,raw,None))
            else:
                path=generated / f"{index+1:03d}.svg"
                path.write_text(artwork(index),encoding="utf-8")
                objects=_parse_svg(path,index)
                output=io.BytesIO()
                render(objects,opts["shape"]).save(output,format="PNG")
                staged.append((template,index,output.getvalue(),objects))
        self.stdout.write(f"Validated 24 reference images and 76 editable vector designs.")
        if opts["dry_run"]:
            self.stdout.write("Dry run complete: database and media unchanged.")
            return
        folder_backup=Path(settings.BASE_DIR)/"coaster_template_backups"
        folder_backup.mkdir(parents=True,exist_ok=True)
        backup=folder_backup/f"coasters_100_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        backup.write_text(json.dumps([{"id":t.pk,"name":t.name,"json_data":t.json_data,"preview":t.preview.name if t.preview else ""} for t in templates],ensure_ascii=False,indent=2,default=str),encoding="utf-8")
        if len(json.loads(backup.read_text(encoding="utf-8")))!=100:
            raise CommandError("Backup verification failed.")
        with transaction.atomic():
            attrs=copy.deepcopy(product.source_attributes or {})
            attrs["Shape"]=["Circle","Square"]
            product.source_attributes=attrs
            product.save(update_fields=["source_attributes"])
            for template,index,preview,objects in staged:
                ext="jpg" if index<24 else "png"
                template.preview.save(f"coaster-{template.pk}-v100.{ext}",ContentFile(preview),save=False)
                if objects is None:
                    # Original reference art is flattened; its image layer is replaceable.
                    objects=[dict(id=f"reference_{index+1:03d}",name="Replaceable reference artwork",
                        type="image",src=template.preview.url,left=0,top=0,width=1000,
                        height=1000,scaleX=1,scaleY=1,angle=0,opacity=1,
                        selectable=True,evented=True,customerEditable=True,replaceable=True)]
                data=copy.deepcopy(template.json_data)
                for key in ("pages","adminPages"):
                    for page in data.get(key,[]):
                        if isinstance(page,dict):
                            page["objects"]=copy.deepcopy(objects)
                data.update(availableShapes=["Circle","Square"],shapeIndependentArtwork=True,
                    constrainToPrintArea=True,coasterArtworkIndex=index,
                    coasterArtworkSource="reference-raster" if index<24 else "generated-svg")
                template.json_data=data
                template.save(update_fields=["json_data","preview"])
        self.stdout.write(self.style.SUCCESS(f"Installed 100 coaster templates; backup: {backup}"))
