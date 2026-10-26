"""Rebuild coaster template collection from scratch, without touching other products.

Backs up all existing coaster rows. Referenced templates are retired instead
of deleted so SavedDesign.source_template foreign keys remain intact.
"""
import copy
import io
import json
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from designer.models import DesignTemplate, Product, SavedDesign
from .install_coaster_reference_100 import make_artwork, align_text_objects
from .rebuild_coaster_previews import render

class Command(BaseCommand):
    help="Back up, retire/remove old coaster templates, create 100 new editable designs."
    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, default=415)
        parser.add_argument("--shape", choices=("circle","square"), default="circle")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--apply", action="store_true")
    def handle(self,*args,**opts):
        if opts["dry_run"]==opts["apply"]:
            raise CommandError("Specify exactly one of --dry-run or --apply")
        pid=opts["product_id"]
        product=Product.objects.filter(pk=pid).first()
        if not product:
            raise CommandError(f"Product {pid} does not exist")
        # Prepare and render before touching the database.
        prepared=[]
        for i in range(100):
            objects,category=make_artwork(i)
            align_text_objects(objects)
            data={"version":"5.3.0","width":1000,"height":1000,
                  "pages":[{"width":1000,"height":1000,"objects":copy.deepcopy(objects)}],
                  "generator":"zenvibe-coaster-fresh-v1",
                  "artworkCategory":category,"artworkReferenceIndex":i%24+1,
                  "constrainToPrintArea":True}
            img=render(objects,opts["shape"])
            if opts["shape"]=="circle":
                rgba=img.convert("RGBA")
                mask=Image.new("L",rgba.size,0)
                ImageDraw.Draw(mask).ellipse((1,1,rgba.width-2,rgba.height-2),fill=255)
                rgba.putalpha(mask)
                img=rgba
            buffer=io.BytesIO()
            img.save(buffer,format="PNG",optimize=True)
            prepared.append((category,data,buffer.getvalue()))
        existing=list(DesignTemplate.objects.filter(product_id=pid).order_by("pk"))
        referenced_ids=set(SavedDesign.objects.filter(
            source_template_id__in=[t.pk for t in existing]
        ).values_list("source_template_id",flat=True))
        self.stdout.write(f"Product: {pid} ({product.name})")
        self.stdout.write(f"Existing: {len(existing)}; referenced by saved designs: {len(referenced_ids)}")
        self.stdout.write(f"Will create 100 new templates, retire {len(referenced_ids)} referenced rows, "
                          f"delete {len(existing)-len(referenced_ids)} unreferenced rows")
        if opts["dry_run"]:
            self.stdout.write("Dry run only; nothing changed")
            return
        backup_dir=Path(settings.BASE_DIR)/"coaster_template_backups"
        backup_dir.mkdir(parents=True,exist_ok=True)
        backup=backup_dir/("coaster-before-recreate-%s.json"%datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        backup.write_text(json.dumps([
            {"id":t.pk,"name":t.name,"is_active":t.is_active,
             "preview":t.preview.name if t.preview else None,"json_data":t.json_data}
            for t in existing],indent=2,default=str),encoding="utf-8")
        # Database rollback protects the original rows if creation fails.
        with transaction.atomic():
            DesignTemplate.objects.filter(pk__in=referenced_ids).update(is_active=False)
            DesignTemplate.objects.filter(product_id=pid).exclude(pk__in=referenced_ids).delete()
            for i,(category,data,png) in enumerate(prepared):
                t=DesignTemplate(product_id=pid,name=("%03d | %s"%(i+1,category))[:140],
                                 json_data=data,is_active=True)
                t.preview.save("coaster-fresh-%s-%03d.png"%(pid,i+1),ContentFile(png),save=False)
                t.save()
        self.stdout.write(self.style.SUCCESS(
            f"Recreated 100 active coaster templates. Backup: {backup}"))
