"""Install the 100 individually selected coaster artworks from the supplied pack.

Copy the pack's coaster_artworks/ folder into your Django project root, then:
python manage.py install_coaster_catalog_100 --product-id 415 --dry-run
python manage.py install_coaster_catalog_100 --product-id 415 --apply

These are image-based templates: backgrounds are replaceable, not vector-editable.
"""
import base64
import copy
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate

class Command(BaseCommand):
    help="Apply 100 distinct supplied coaster images to existing active templates."
    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)
        parser.add_argument("--assets-dir", default="")
        parser.add_argument("--shape", choices=["circle","square"], default="circle")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
    def handle(self, *args, **o):
        if o["dry_run"] == o["apply"]:
            raise CommandError("Choose exactly one of --dry-run or --apply")
        root=Path(o["assets_dir"]) if o["assets_dir"] else Path(settings.BASE_DIR)/"coaster_artworks"
        names_path=root.parent/"design_names.json"
        if not names_path.exists(): raise CommandError(f"Missing {names_path}")
        names=json.loads(names_path.read_text(encoding="utf-8"))
        if len(names)!=100:raise CommandError("Expected 100 names")
        templates=list(DesignTemplate.objects.filter(product_id=o["product_id"],is_active=True).order_by("pk"))
        if len(templates)!=100:raise CommandError(f"Expected 100 active templates; found {len(templates)}")
        missing=[str(root/f"{i:03d}.png") for i in range(1,101) if not (root/f"{i:03d}.png").exists()]
        if missing:raise CommandError(f"Missing {len(missing)} artwork images, e.g. {missing[0]}")
        self.stdout.write(f"100 unique artworks found. Shape: {o['shape']}. Existing template IDs retained.")
        if o["dry_run"]:return
        with transaction.atomic():
            for i,t in enumerate(templates,1):
                with Image.open(root/f"{i:03d}.png") as im:
                    artwork=im.convert("RGBA").resize((1000,1000),Image.Resampling.LANCZOS)
                # For square products the complete square artwork remains visible.
                # For circular products clip the image to the circle, not the text layer.
                if o["shape"]=="circle":
                    mask=Image.new("L",(1000,1000),0)
                    ImageDraw.Draw(mask).ellipse((0,0,999,999),fill=255)
                    artwork.putalpha(mask)
                b=io.BytesIO();artwork.save(b,"PNG")
                encoded=base64.b64encode(b.getvalue()).decode("ascii")
                image={"id":"catalog-artwork","type":"image","left":0,"top":0,
                       "width":1000,"height":1000,"scaleX":1,"scaleY":1,
                       "src":"data:image/png;base64,"+encoded,
                       "selectable":True,"evented":True,"customerEditable":True}
                data=copy.deepcopy(t.json_data or {})
                data.update({"width":1000,"height":1000,"generator":"zenvibe-curated-catalog-100",
                             "artworkCategory":names[i-1],"artworkComposition":i,
                             "constrainToPrintArea":True})
                # Do not add unrelated prewritten headings over these illustrated artworks.
                # Customers can add editable text in the editor.
                page={"width":1000,"height":1000,"objects":[image]}
                data["pages"]=[page]
                data["adminPages"]=[copy.deepcopy(page)]
                t.name=f"{i:03d} | {names[i-1]}"
                t.json_data=data
                t.preview.save(f"coaster-catalog-{i:03d}-{t.pk}.png",ContentFile(b.getvalue()),save=False)
                t.save(update_fields=["name","json_data","preview"])
        self.stdout.write(self.style.SUCCESS("Updated 100 templates; preserved IDs."))
