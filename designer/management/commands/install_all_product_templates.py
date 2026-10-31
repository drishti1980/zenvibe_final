"""One-command batch installer for Zenvibe's existing editable template libraries.

  python manage.py install_all_product_templates --dry-run
  python manage.py install_all_product_templates --apply
  python manage.py install_all_product_templates --apply --refresh-existing
  python manage.py install_all_product_templates --dry-run --product-ids 89,62,170

Unlike the legacy --replace commands this NEVER deletes templates and NEVER
deletes customers' saved designs. It installs only supported product libraries,
skips unknown families, backs up any existing source rows on apply, and writes
a per-product CSV report. Unsupported products must not be marked complete.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command, get_commands
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from designer.design_profiles import _ancestry
from designer.models import DesignTemplate, Product
from designer.management.commands.seed_promotional_product_templates import (
    CANONICAL_PRODUCT_NAMES,
    LEGACY_PRODUCT_IDS,
    GENERATOR as PROMOTIONAL_GENERATOR,
    physical as promotional_physical,
)
from designer.management.commands.seed_notebook_templates import (
    GENERATOR as NOTEBOOK_GENERATOR,
)


@dataclass
class Task:
    product: object
    group: str
    target: int
    count: int
    command: str = ""
    params: dict = field(default_factory=dict)
    reason: str = ""
    refreshable: bool = False
    # Some legacy seeders ALWAYS INSERT; never call them on an occupied product.
    insert_only: bool = False

    @property
    def action(self):
        return "INSTALL" if self.command else "SKIP"


def match(name, *needles):
    text = re.sub(r"[\s_-]+", " ", name.lower())
    return any(needle in text for needle in needles)


def ancestry(product):
    slugs, names = _ancestry(product)
    return set(slugs), set(names)


def choose(product, count, refresh=False):
    name = (product.name or "").lower()
    slugs, categories = ancestry(product)
    root_marketing = "marketing-materials" in slugs or "marketing materials" in categories
    root_banners = "banners-displays" in slugs or "banners & displays" in categories
    root_promo = "promotional-products" in slugs or "promotional products" in categories
    root_notebook = "custom-notebooks" in slugs or "custom notebooks" in categories
    if root_marketing:
        group = "Marketing Materials"
    elif root_banners:
        group = "Banners & Displays"
    elif root_promo:
        group = "Promotional Products"
    elif root_notebook:
        group = "Notebooks"
    else:
        group = "Other"

    def plan(target=100, cmd="", params=None, reason="", refreshable=False, insert_only=False):
        # The existing gallery takes precedence. Never create a second 100-row
        # set merely because the earlier generator's tag differs.
        if count >= target:
            if not (refresh and refreshable):
                return Task(product, group, target, count, reason="Already has %d active templates" % count)
            # Refreshing a differently named generated library would add a
            # second 100-template set. Only the backed-up teardrop updater may
            # safely migrate legacy templates in place.
            if cmd != "install_luxury_teardrop_flags":
                return Task(product, group, target, count,
                            reason="Existing %d templates retained; batch refresh does not replace older libraries" % count)
        if count and cmd in ("seed_flyer_templates_v2",
                              "seed_100_trifold_brochure_templates"):
            # Partial legacy libraries cannot be assumed to use the same
            # composition keys. Do not create duplicates over them.
            from designer.management.commands.seed_flyer_templates_v2 import GENERATOR_ID as FLYER_GENERATOR
            from designer.management.commands.seed_100_trifold_brochure_templates import GENERATOR_ID as TRIFOLD_GENERATOR
            expected=(FLYER_GENERATOR if cmd=="seed_flyer_templates_v2" else TRIFOLD_GENERATOR)
            recognizable=DesignTemplate.objects.filter(
                product_id=product.pk,is_active=True,json_data__generator=expected
            ).count()
            if recognizable != count:
                return Task(product, group, target, count,
                            reason="Existing templates use a different generator; protect against duplicated gallery rows")
        if count and insert_only:
            return Task(product, group, target, count,
                        reason="Legacy generator inserts duplicates; %d existing templates retained" % count)
        return Task(product, group, target, count, cmd, params or {}, reason,
                    refreshable, insert_only)

    # Named product routes take priority over broad category matches.
    # Teardrop is the ONLY flag for which a die-cut-safe dedicated installer
    # is available. Other flags are reported rather than faked as rectangles.
    if ("teardrop" in name or "tear drop" in name) and "flag" in name:
        return plan(cmd="install_luxury_teardrop_flags",
                    params={"product_id": product.pk, "apply": True},
                    refreshable=True)

    if root_marketing or match(name, "flyer", "brochure", "door hanger", "ticket", "business card"):
        if match(name, "flyer"):
            return plan(cmd="seed_flyer_templates_v2", params={"product_id": product.pk, "count": 100},
                        refreshable=False)
        if match(name, "tri fold", "trifold"):
            return plan(cmd="seed_100_trifold_brochure_templates",
                        params={"product_id": product.pk, "count": 100}, refreshable=False)
        if match(name, "bi fold", "bifold"):
            if int(product.width or 0) <= int(product.height or 0):
                return plan(reason="Bi-fold requires landscape canvas dimensions")

            if count and refresh:
                return Task(product,group,100,count,"refresh_marketing_previews",
                            {"product_id":product.pk,"apply":True},
                            "Refresh complete gallery previews without overwriting edited templates",True)
            return plan(cmd="seed_100_marketing_material_templates",
                        params={"product_id": product.pk, "kind": "bifold", "count": 100},
                        insert_only=True)
        if match(name, "door hanger", "doorhanger"):
            if int(product.height or 0) <= int(product.width or 0):
                return plan(reason="Door hanger requires portrait canvas dimensions")

            if count and refresh:
                return Task(product,group,100,count,"refresh_marketing_previews",
                            {"product_id":product.pk,"apply":True},
                            "Refresh complete gallery previews without overwriting edited templates",True)
            return plan(cmd="seed_100_marketing_material_templates",
                        params={"product_id": product.pk, "kind": "doorhanger", "count": 100},
                        insert_only=True)
        if match(name, "ticket"):
            if int(product.width or 0) <= int(product.height or 0):
                return plan(reason="Ticket requires landscape canvas dimensions")

            if count and refresh:
                return Task(product,group,100,count,"refresh_marketing_previews",
                            {"product_id":product.pk,"apply":True},
                            "Refresh complete gallery previews without overwriting edited templates",True)
            return plan(cmd="seed_100_marketing_material_templates",
                        params={"product_id": product.pk, "kind": "ticket", "count": 100},
                        insert_only=True)
        if match(name, "business card"):
            return plan(reason="Shared business card v5 builder deletes previous generated rows; excluded for safety")
        if root_marketing:
            return plan(reason="No verified product-specific marketing generator")

    if root_banners or match(name, "canopy", "back wall", "banner", "flag", "umbrella"):
        if match(name, "full back wall", "back wall") and "canopy" in name:
            surfaces=list(product.print_surfaces.filter(is_active=True))
            if len(surfaces)!=2 or any(not x.print_width_in or not x.print_height_in for x in surfaces):
                return plan(reason="Full back wall requires two valid Admin print surfaces")
            return plan(cmd="rebuild_full_back_wall_100",
                        params={"product_id": product.pk, "count": 100},
                        refreshable=True)
        if "canopy" in name and ("tent" in name or "10x" in name) and not match(
                name, "replacement", "side wall", "frame only", "aluminum frame"):
            surfaces=list(product.print_surfaces.filter(is_active=True))
            if len(surfaces) != 7 or any(
                not s.print_width_in or not s.print_height_in for s in surfaces
            ):
                return plan(reason="Canopy requires seven configured Admin print surfaces; found %d" % len(surfaces))
            return plan(cmd="rebuild_canopy_100_unique_v5",
                        params={"product_id": product.pk}, refreshable=True)
        # Roll-ups, rectangular flags and tablecovers are NOT teardrops and
        # must not receive the teardrop mask.
        if root_banners:
            return plan(reason="No verified shape-specific banner/display generator")

    if "umbrella" in name and (root_promo or group == "Other"):
        surface=product.print_surfaces.filter(is_active=True).order_by("sort_order","id").first()
        wi=(surface.print_width_in if surface else product.print_width_in)
        hi=(surface.print_height_in if surface else product.print_height_in)
        if not wi or not hi:
            return plan(reason="Umbrella requires real Admin print width and height")
        return plan(cmd="seed_umbrella_luxury_templates",
                    params={"product_id": product.pk, "count": 100}, refreshable=True)

    if root_promo:
        if product.pk in LEGACY_PRODUCT_IDS:
            return plan(reason="Legacy duplicate product explicitly excluded from promotional library")
        if product.name not in CANONICAL_PRODUCT_NAMES or product.category.slug != "promotional-products":
            return plan(reason="Product not in supported canonical promotional library")
        # The promo generator counts only its own rows. Subtract legacy rows
        # so the entire gallery does not silently grow past 100.
        if not promotional_physical(product) and not (
                product.pk==231 or "paper wristband" in name or
                "mouse pad" in name or "lanyard" in name or
                "aluminum bottle opener" in name):
            return plan(reason="Missing physical print dimensions; no guessed rectangular artwork")
        tagged=DesignTemplate.objects.filter(
            product_id=product.pk, is_active=True,
            json_data__generator=PROMOTIONAL_GENERATOR
        ).count()
        legacy=max(0,count-tagged)
        target_generator=max(0,100-legacy)
        if tagged>=target_generator:
            return plan(reason="Already has 100 or more active promotional templates")
        return plan(cmd="seed_promotional_product_templates",
                    params={"product_id":product.pk,"count":target_generator})

    if root_notebook:
        if product.category.slug != "custom-notebooks":
            return plan(target=20,reason="Notebook category is not the direct supported category")
        if not all([product.workspace_width_in,product.workspace_height_in,
                    product.print_width_in,product.print_height_in]):
            return plan(target=20,reason="Notebook physical dimensions not configured")
        tagged=DesignTemplate.objects.filter(
            product_id=product.pk, is_active=True,
            json_data__generator=NOTEBOOK_GENERATOR
        ).count()
        legacy=max(0,count-tagged)
        target_generator=max(0,20-legacy)
        if tagged>=target_generator:
            return plan(target=20,reason="Notebook library already populated")
        return plan(target=20,cmd="seed_notebook_templates",
                    params={"product_id":product.pk,"count":target_generator})

    # Other standalone product libraries (awards, drinkware, apparel etc.)
    # require their dedicated print-face generator. Never force 100 flyers
    # onto a non-flat object just to hit a number.
    return Task(product, group, 0, count,
                reason="No verified dedicated template generator for this product")


def backup(rows, path):
    """Streaming gzip JSONL; safe for JSONFields containing large SVG/photo URIs."""
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for task in rows:
            qs=DesignTemplate.objects.filter(product_id=task.product.pk).order_by("pk")
            for item in qs.iterator(chunk_size=50):
                record={"id":item.pk,"product_id":item.product_id,"name":item.name,
                        "is_active":item.is_active,"json_data":item.json_data,
                        "preview_name":item.preview.name if item.preview else ""}
                stream.write(json.dumps(record,ensure_ascii=False,default=str)+"\n")


class Command(BaseCommand):
    help="Batch-install available editable template libraries; report unsupported products without inventing artwork."

    def add_arguments(self, parser):
        mode=parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--apply",action="store_true")
        parser.add_argument("--product-ids",default="",
                            help="Optional comma-separated product IDs; default scans entire active catalogue.")
        parser.add_argument("--refresh-existing",action="store_true",
                            help="Refresh only safe, idempotent libraries (including flagged teardrop).")
        parser.add_argument("--strict",action="store_true",
                            help="Stop when one supported generator fails; default records errors and continues.")

    def handle(self,*args,**opts):
        selected=opts["product_ids"].strip()
        ids=None
        if selected:
            try:
                ids={int(x.strip()) for x in selected.split(",") if x.strip()}
                if not ids or min(ids)<=0: raise ValueError()
            except ValueError:
                raise CommandError("--product-ids must contain positive integers separated by commas")

        q=Product.objects.filter(is_active=True).select_related("category","category__parent").order_by("id")
        if ids is not None:
            q=q.filter(pk__in=ids)
        products=list(q)
        if not products:
            raise CommandError("No matching active products found. Check --product-ids.")

        counts=dict(
            DesignTemplate.objects.filter(product__in=products,is_active=True)
            .values("product_id").order_by()
            .annotate(total=Count("id"))
            .values_list("product_id","total")
        )
        jobs=[choose(p,counts.get(p.pk,0),opts["refresh_existing"]) for p in products]
        registered=get_commands()
        for job in jobs:
            if job.command and job.command not in registered:
                job.reason="Missing Django management command: "+job.command
                job.command=""

        now=datetime.now().strftime("%Y%m%d-%H%M%S")
        report_dir=Path(settings.BASE_DIR)/"template_reports"
        report_dir.mkdir(parents=True,exist_ok=True)
        report=report_dir/("all_templates_%s_%s.csv"%("apply" if opts["apply"] else "plan",now))
        queued=[j for j in jobs if j.command]
        self.stdout.write("%d active products; %d eligible generator jobs; %d skipped / unsupported."%(
            len(jobs),len(queued),len(jobs)-len(queued)))

        result_rows=[]
        errors=0
        if opts["apply"] and queued:
            backup_dir=Path(settings.BASE_DIR)/"template_backups"
            backup_dir.mkdir(parents=True,exist_ok=True)
            backup_path=backup_dir/("all-templates-before-%s.jsonl.gz"%now)
            backup(queued,backup_path)
            self.stdout.write("Backup of existing source rows: "+str(backup_path))

        for number,job in enumerate(jobs,1):
            status="PLANNED" if job.command else "SKIPPED"
            message=job.reason
            final_count=job.count
            if opts["apply"] and job.command:
                capture=io.StringIO()
                try:
                    # Each product gets its own transaction. A failed generator
                    # does not roll back successful, unrelated product libraries.
                    with transaction.atomic():
                        call_command(job.command,stdout=capture,**job.params)
                        if job.command=="seed_100_marketing_material_templates":
                            call_command("refresh_marketing_previews",
                                         product_id=job.product.pk,apply=True,
                                         stdout=capture)
                    final_count=DesignTemplate.objects.filter(
                        product_id=job.product.pk,is_active=True
                    ).count()
                    status="INSTALLED" if final_count>=job.target else "INCOMPLETE"
                    if final_count>job.target:
                        message="Gallery has %d active templates, exceeds target %d; review duplicates"%(final_count,job.target)
                    elif final_count<job.target:
                        message="Only %d/%d templates found after generator"%(final_count,job.target)
                    else:
                        message="Generated library installed; visual print QA still required"
                    if status!="INSTALLED": errors+=1
                except Exception as exc:
                    status="FAILED"
                    message=str(exc)
                    errors+=1
                    if opts["strict"]:
                        result_rows.append((job,status,final_count,message))
                        break

            result_rows.append((job,status,final_count,message))
            if job.command or (number<=8 and not opts["apply"]):
                self.stdout.write("[%d/%d] #%s %s — %s: %s"%(number,len(jobs),
                    job.product.pk,job.product.name,status,message or job.command))

        with report.open("w",encoding="utf-8-sig",newline="") as f:
            writer=csv.writer(f)
            writer.writerow(["product_id","product","category","previous_active",
                             "target","generator","status","final_active","note"])
            for job,status,total,msg in result_rows:
                writer.writerow([job.product.pk,job.product.name,job.group,
                                 job.count,job.target,job.command,status,total,msg])

        self.stdout.write("Per-product CSV report: "+str(report))
        self.stdout.write("Installed: %d | Failed/incomplete: %d | Skipped: %d"%(
            sum(1 for _,status,_,_ in result_rows if status=="INSTALLED"),
            errors,sum(1 for _,status,_,_ in result_rows if status=="SKIPPED")))
        if errors:
            raise CommandError("Some product batches failed or are incomplete. Inspect the report; reruns are safe.")
        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run complete. Database unchanged."))
        else:
            self.stdout.write(self.style.SUCCESS("Completed supported template installations. Unsupported products are listed in the report."))
