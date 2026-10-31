"""ONE PASS: audit + install the remaining premium 100-template categories.

The protected lists are intentional. This command NEVER touches Canopy,
Business Cards, Calendars, Invitations, Coasters, Awards, Umbrellas, or
previously completed shape-specialist libraries such as Full Back Wall.

    python manage.py install_remaining_premium_100 --dry-run
    python manage.py install_remaining_premium_100 --apply

Import/report is per product, never an all-or-nothing gallery rewrite.
Existing generated master IDs are preserved and backed up; custom masters
are skipped. Unsupported shapes and missing Admin measurements are reported.
No changes to storefront templates, product settings or product prices.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command, get_commands
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from designer.models import Product, DesignTemplate
from designer.management.commands.rebuild_remaining_premium_100 import (
    TARGET, GENERATOR, family_for, protected, configured_pages,
    _existing_status, PROTECTED_GENERATOR_PARTS,
)

class Command(BaseCommand):
    help="Complete missing/non-approved 100-template product libraries; never change approved categories."

    def add_arguments(self,p):
        mode=p.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run",action="store_true")
        mode.add_argument("--apply",action="store_true")
        p.add_argument("--product-ids",default="",
                       help="Optional comma-separated product IDs; omitted = all active products")
        p.add_argument("--photo-dir",default="",
                       help="Optional 20 properly licensed industry photos 01.jpg..20.jpg")
        p.add_argument("--only-missing",action="store_true",
                       help="Leave all existing populated galleries alone, regardless of generator")
        p.add_argument("--strict",action="store_true",
                       help="Stop processing after the first failed eligible product")

    def handle(self,*args,**opts):
        selected=opts["product_ids"].strip()
        ids=None
        if selected:
            try:
                ids={int(v.strip()) for v in selected.split(",") if v.strip()}
                if not ids or min(ids)<=0:raise ValueError
            except ValueError:
                raise CommandError("--product-ids must be positive integers separated by commas")

        products=Product.objects.filter(is_active=True).select_related(
            "category","category__parent").order_by("pk")
        if ids is not None:
            products=products.filter(pk__in=ids)
        products=list(products)
        if not products:
            raise CommandError("No matching active products")

        counts=dict(
            DesignTemplate.objects.filter(product__in=products,is_active=True)
            .order_by().values("product_id").annotate(n=Count("id"))
            .values_list("product_id","n")
        )

        # Preflight before running any generator. An unsupported product is
        # not "INSTALLED" and an approved library is not included in jobs.
        records=[]
        for p in products:
            n=counts.get(p.pk,0)
            label="SKIPPED"
            reason=""
            family=""
            if protected(p):
                label="PROTECTED"
                reason=protected(p)
            elif not (family:=family_for(p)):
                reason="Non-100-template category, cut-shape without verified dieline, or hardware-only product"
            elif n and opts["only_missing"]:
                reason="Existing gallery explicitly preserved by --only-missing"
            else:
                try:
                    if family!="doorhanger":
                        configured_pages(p,family)
                        _existing_status(p)
                    else:
                        # Doorhanger V7 does its own protected-master and
                        # front/back Admin checks before touching database.
                        from designer.management.commands.rebuild_doorhanger_photo_v7 import (
                            GENERATOR as DOORHANGER_GENERATOR,
                            LEGACY_GENERATORS as DOORHANGER_LEGACY,
                        )
                        existing=list(DesignTemplate.objects.filter(product=p).only(
                            "pk","name","json_data","is_active"))
                        import re,json
                        if len(existing)>100:
                            raise CommandError("More than 100 door hanger masters; duplicate review required")
                        for t in existing:
                            if not re.match(r"^ZV Door Hanger\s+\d{1,3}\b",t.name):
                                raise CommandError("Non-generated door hanger templates retained")
                            data=t.json_data
                            if isinstance(data,str):
                                data=json.loads(data)
                            if not isinstance(data,dict) or str(data.get("generator","")) not in (
                                DOORHANGER_LEGACY | {DOORHANGER_GENERATOR}
                            ):
                                raise CommandError("Unknown generated door hanger library retained")
                    label="PLANNED"
                    reason="100 unique professionally composed layouts"
                except (CommandError,ValueError,TypeError,KeyError) as exc:
                    reason=str(exc)
            records.append({
                "product":p,"previous":n,"family":family,
                "status":label,"reason":reason,"after":n
            })

        jobs=[r for r in records if r["status"]=="PLANNED"]
        self.stdout.write(
            "%d active products; %d planned; %d protected; %d skipped."%(
                len(records),len(jobs),
                sum(r["status"]=="PROTECTED" for r in records),
                sum(r["status"]=="SKIPPED" for r in records),
            )
        )
        commands=get_commands()
        for row in jobs:
            command=("rebuild_doorhanger_photo_v7"
                     if row["family"]=="doorhanger" else
                     "rebuild_remaining_premium_100")
            if command not in commands:
                row["status"]="FAILED"
                row["reason"]="Missing management command %s"%command

        if opts["apply"]:
            for i,row in enumerate(jobs,1):
                if row["status"]!="PLANNED":
                    continue
                p=row["product"]
                command=("rebuild_doorhanger_photo_v7"
                         if row["family"]=="doorhanger" else
                         "rebuild_remaining_premium_100")
                params={"product_id":p.pk,"apply":True}
                if opts["photo_dir"]:
                    params["photo_dir"]=opts["photo_dir"]
                capture=io.StringIO()
                try:
                    # The per-product installer prepares all 100 layouts,
                    # generates all previews, makes a versioned backup, then
                    # runs a single database transaction for that product.
                    call_command(command,stdout=capture,**params)
                    final=DesignTemplate.objects.filter(
                        product=p,is_active=True).count()
                    row["after"]=final
                    row["status"]="INSTALLED" if final==TARGET else "INCOMPLETE"
                    row["reason"]=(
                        "100 editable premium designs; previews rendered from their objects"
                        if final==TARGET else
                        "After installation, %s active templates (expected 100)"%final
                    )
                except Exception as exc:
                    row["status"]="FAILED"
                    row["reason"]="%s: %s"%(type(exc).__name__,exc)
                self.stdout.write(
                    "[%s/%s] #%s %s — %s: %s"%(
                        i,len(jobs),p.pk,p.name,
                        row["status"],row["reason"]
                    )
                )
                if row["status"]=="FAILED" and opts["strict"]:
                    break
        elif opts["dry_run"]:
            for row in jobs:
                if row["status"]=="PLANNED":
                    self.stdout.write(
                        "#%s %s — %s"%(row["product"].pk,
                                        row["family"],row["reason"])
                    )

        folder=Path(settings.BASE_DIR)/"template_reports"
        folder.mkdir(parents=True,exist_ok=True)
        name="premium100_%s_%s.csv"%(
            "apply" if opts["apply"] else "plan",
            datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        )
        report=folder/name
        with report.open("w",newline="",encoding="utf-8-sig") as f:
            writer=csv.writer(f)
            writer.writerow([
                "product_id","product","category","family","previous_active",
                "after_active","status","reason"
            ])
            for row in records:
                p=row["product"]
                writer.writerow([
                    p.pk,p.name,p.category.name,row["family"],
                    row["previous"],row["after"],row["status"],row["reason"]
                ])
        statuses={key:sum(r["status"]==key for r in records)
                  for key in ("INSTALLED","PLANNED","PROTECTED","SKIPPED","FAILED","INCOMPLETE")}
        self.stdout.write("Report: %s"%report)
        self.stdout.write("Summary: "+", ".join("%s %d"%(k,v) for k,v in statuses.items() if v))
        if statuses["FAILED"] or statuses["INCOMPLETE"]:
            raise CommandError(
                "Some eligible product libraries failed; protected products remain unchanged. "
                "See CSV for exact causes."
            )
        self.stdout.write(self.style.SUCCESS(
            "No approved/locked product libraries were changed."
            if opts["apply"] else
            "Catalogue preflight complete. No product/media/database changes."
        ))
