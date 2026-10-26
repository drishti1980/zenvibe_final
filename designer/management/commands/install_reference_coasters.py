"""Install 24 reference-image coaster templates without duplicating artwork.

Reference tile JPGs are replaceable Fabric image layers. The original artwork
and lettering are raster pixels, not editable vector/text components.
No changes to templates 25-100. Backups made before writing.
"""
from __future__ import annotations
import copy
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate

THEMES = [
    "Marble Luxury","Botanical","Watercolor","Tropical","Floral","Modern Gold",
    "Coastal Photography","Terrazzo","Olive Minimal","Coffee Photography",
    "Blue Porcelain","Wood Texture","Organic Abstract","Black Marble",
    "Pink Floral","Eucalyptus","Mountain Photography","Golden Leaves",
    "Earthy Abstract","Marble Botanical","Sunset Photography",
    "Gold Mandala","Blue Floral","Botanical Minimal",
]

class Command(BaseCommand):
    help = "Install the 24 provided reference designs as replaceable image layers."
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
    def handle(self, *args, **opts):
        if opts["dry_run"] == opts["apply"]:
            raise CommandError("Specify exactly one of --dry-run or --apply.")
        folder = Path(settings.BASE_DIR) / "designer" / "reference_coaster_tiles"
        files = [folder / f"{i:03d}.jpg" for i in range(1,25)]
        missing = [p.name for p in files if not p.is_file()]
        if missing:
            raise CommandError(f"Missing reference tile files in {folder}: {missing}")
        templates = list(DesignTemplate.objects.filter(product_id=415,is_active=True).order_by("id"))
        if len(templates) != 100:
            raise CommandError(f"Expected 100 active product 415 templates; got {len(templates)}")
        for template in templates[:24]:
            if not isinstance(template.json_data,dict) or not template.json_data.get("pages"):
                raise CommandError(f"Template {template.pk} missing editable pages")
        if opts["dry_run"]:
            self.stdout.write("Validated 24 source JPGs and 100 template records. No changes.")
            return
        backup_dir=Path(settings.BASE_DIR)/"coaster_template_backups"
        backup_dir.mkdir(parents=True,exist_ok=True)
        backup_path=backup_dir/f"reference_24_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        backup_path.write_text(json.dumps([
            {"id":t.pk,"name":t.name,"json_data":t.json_data,"preview":t.preview.name if t.preview else None}
            for t in templates[:24]
        ],ensure_ascii=False,indent=2,default=str),encoding="utf-8")
        with transaction.atomic():
            for i,(template,file) in enumerate(zip(templates[:24],files)):
                raw=file.read_bytes()
                # ImageField stores the source as a normal media URL usable by Fabric.
                template.preview.save(f"reference-coaster-{template.pk}.jpg",ContentFile(raw),save=False)
                url=template.preview.url
                image={
                    "id":f"reference_image_{i+1:03d}","name":f"Replaceable {THEMES[i]} artwork",
                    "type":"image","src":url,"left":0,"top":0,
                    "width":1000,"height":1000,"scaleX":1,"scaleY":1,"angle":0,
                    "opacity":1,"selectable":True,"evented":True,
                    "customerEditable":True,"replaceable":True,
                    "lockMovementX":False,"lockMovementY":False,
                }
                data=copy.deepcopy(template.json_data)
                for key in ("pages","adminPages"):
                    for page in data.get(key,[]):
                        if isinstance(page,dict):
                            page["objects"]=[copy.deepcopy(image)]
                data["availableShapes"]=["Circle","Square"]
                data["shapeIndependentArtwork"]=True
                data["constrainToPrintArea"]=True
                data["coasterArtworkSource"]="reference-photo-layer"
                data["rasterArtworkNotVectorEditable"]=True
                template.json_data=data
                template.name=f"{THEMES[i]} — Artwork {i+1:03d}"
                template.save(update_fields=["json_data","name","preview"])
        self.stdout.write(self.style.SUCCESS(
            "Updated first 24 coaster templates with reference-image layers and matching previews. "
            "Templates 25-100 unchanged."
        ))
