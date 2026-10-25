import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import Product, ProductPrintArea, ProductPrintSurface



# Canonical Awards rows in the checked-in ZenVibe catalogue snapshot.
# These IDs are used ONLY to select source rows from the CSV; they are never
# assumed to be IDs in the current local database.
CANONICAL_AWARD_SOURCE_IDS = {
    494,495,499,502,504,507,508,509,511,512,513,514,515,516,517,518,519,520,
    521,524,526,527,528,529,530,534,535,536,537,538,541,573,581,586,589,595,
    601,608,619,626,656,657,658,659,660,661,662,663,664,
}

# Old local/import names that refer to a renamed canonical ZenVibe Award.
AWARD_NAME_ALIASES = {
    "certificatewithframe": "personalizedcertificatewithframe",
    "crystalawardtrophymarblebase": "premiumcrystalawardtrophywithmarblebase",
    "customcoppermetalcrowncrystalglassmedalswithribbon": "custommetalcrowncrystalglassmedalwithribbon",
    "customroundmetalglassmedalbronze": "roundmetalglassmedal",
    "customsquarewoodencertificateplaque": "customsquarewoodencertificateplaquewith16cmroundgoldplate",
    "customizedcreativecrystaltrophy": "customizedcreativecrystalawardpremiumengravedaward",
    "elegantgoldfinishedplasticaward31cm": "elegantgoldfinishedplastictrophy31cm",
    "metalchampioncuptrophydesign": "goldmetalchampioncuptrophy",
    "platedmetalgrandtrophycup": "goldplatedmetalgrandtrophycupforsportscompetitions",
    "goldenunityhandtrophy": "goldenunityhandtrophycanadaresincrystalleadershipaward",
    "golfplasticrecognitiontrophy31cm": "plasticrecognitiontrophy31cm",
    "moderngoldgolfswingtrophyoncrystalbase768x1024": "golfswingtrophyoncrystalbase",
    "personalizedstarborderglassmedalsbronze": "personalizedstarborderglassmedal",
    "ballinhand": "goldresinhandcrystalglobetrophypremiumaward",
    "3starresinwithcrystalbase": "customgoldstarresinawardpremiumengravedaward",
    "mirrorfinishingaward": "purplecrystalawardpremiumrecognitiontrophy",
    "roundcrystalcertificateofexcellenceawardwithgoldbasecanada": "roundcrystalcertificateofexcellenceawardelegantrecognitiontrophy",
    "premiumresintrophy": "premiumresintrophyuniquecustomaward",
    "silverplatedmetalchampionshiptrophy63cm": "silverplatedmetalchampionshiptrophy63cm",
}

class Command(BaseCommand):
    help = (
        "Repair Awards product mapping from the checked-in ZenVibe mapping CSV. "
        "This removes stale duplicate Award rows from the storefront and resets "
        "guessed editor geometry without touching DesignTemplate JSON."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Required for writes. Without this flag the command is report-only.",
        )

    def handle(self, *args, **opts):
        path = Path(settings.BASE_DIR) / "designer" / "management" / "commands" / "zenvibe_product_mapping.csv"
        if not path.exists():
            raise CommandError(f"Mapping file not found: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = [
                r for r in csv.DictReader(fh)
                if (r.get("type") or "").strip() == "product"
                and (r.get("status") or "").strip().upper() == "MATCHED"
                and "/product/" in (r.get("live_url") or "")
            ]

        # Awards are identified by products that already belong to an Awards category.
        award_products = list(
            Product.objects.filter(category__name__icontains="award")
            .select_related("category").order_by("id")
        )
        if not award_products:
            raise CommandError("No local Awards products found.")

        def norm(value):
            return "".join(ch for ch in (value or "").lower() if ch.isalnum())

        canonical_rows = []
        for r in rows:
            try:
                source_id = int(r.get("local_id") or 0)
            except (TypeError, ValueError):
                continue
            if source_id in CANONICAL_AWARD_SOURCE_IDS:
                canonical_rows.append(r)

        rows_by_name = {norm(r.get("local_name")): r for r in canonical_rows}
        rows_by_slug = {norm(r.get("local_slug")): r for r in canonical_rows}
        rows_by_url_slug = {
            norm((r.get("live_url") or "").rstrip("/").split("/")[-1]): r
            for r in canonical_rows
        }

        matched = {}
        used_source_ids = set()
        unmatched = []
        for p in award_products:
            attrs = p.source_attributes if isinstance(p.source_attributes, dict) else {}
            source_url = str(attrs.get("source_url") or attrs.get("live_url") or "")
            keys = [norm(p.name), norm(p.slug)]
            if source_url:
                keys.append(norm(source_url.rstrip("/").split("/")[-1]))
            alias = AWARD_NAME_ALIASES.get(norm(p.name))
            if alias:
                keys.insert(0, alias)

            candidate = None
            for key in keys:
                candidate = rows_by_name.get(key) or rows_by_slug.get(key) or rows_by_url_slug.get(key)
                if candidate:
                    break
            if candidate:
                sid = int(candidate["local_id"])
                # Keep the best/first local row; duplicate locals resolving to the
                # same canonical source are handled below.
                matched[p.id] = candidate
                used_source_ids.add(sid)
            else:
                unmatched.append(p)

        by_source = {}
        for pid, r in matched.items():
            by_source.setdefault(int(r["local_id"]), []).append(pid)
        stale_ids = set()
        for sid, ids in by_source.items():
            if len(ids) > 1:
                canonical_name = norm(next(r["local_name"] for r in canonical_rows if int(r["local_id"]) == sid))
                ranked = sorted(ids, key=lambda pid: (
                    norm(next(p.name for p in award_products if p.id == pid)) != canonical_name,
                    pid,
                ))
                stale_ids.update(ranked[1:])
        stale = [p for p in award_products if p.id in stale_ids]
        missing_rows = [r for r in canonical_rows if int(r["local_id"]) not in used_source_ids]

        self.stdout.write(f"Safely matched Awards: {len(matched)}")
        self.stdout.write(f"Canonical ZenVibe Awards expected: {len(canonical_rows)}")
        self.stdout.write(f"Unmatched/legacy local records: {len(unmatched)}")
        self.stdout.write(f"Canonical Awards missing locally: {len(missing_rows)}")
        self.stdout.write(f"Confirmed duplicate Awards to disable: {len(stale)}")
        for pid, r in sorted(matched.items()):
            p = next(x for x in award_products if x.id == pid)
            self.stdout.write(f"MATCH {pid}: {p.name} -> {r.get('live_url')}")

        for r in missing_rows:
            self.stdout.write(f"MISSING: {r.get('local_name')} -> {r.get('live_url')}")
        for p in stale:
            self.stdout.write(f"DISABLE {p.id}: {p.name}")

        if opts["dry_run"] or not opts["apply"]:
            if not opts["dry_run"]:
                self.stdout.write(self.style.WARNING(
                    "Report only. Re-run with --apply to write these verified changes."
                ))
            return

        with transaction.atomic():
            # Remove guessed per-product geometry. Awards return to legacy until a
            # geometry is verified from the actual ZenVibe customizer/video.
            for p in award_products:
                if p.id not in matched:
                    continue
                r = matched[p.id]
                # Align identity/source mapping only. Existing templates/media stay attached.
                p.name = r.get("local_name") or p.name
                p.source_attributes = dict(p.source_attributes or {})
                p.source_attributes["source_url"] = r.get("live_url") or ""
                p.source_attributes["source_product_id"] = r.get("local_id") or ""
                p.editor_layout_mode = "legacy"
                p.workspace_width_in = None
                p.workspace_height_in = None
                p.constrain_to_print_area = False
                p.show_product_reference = False
                p.save(update_fields=[
                    "name", "source_attributes", "editor_layout_mode", "workspace_width_in", "workspace_height_in",
                    "constrain_to_print_area", "show_product_reference",
                ])
                ProductPrintArea.objects.filter(product=p).delete()
                ProductPrintSurface.objects.filter(product=p).delete()

            # Keep only canonical mapped duplicates visible. Never delete rows/templates.
            for p in stale:
                p.is_active = False
                p.save(update_fields=["is_active"])

        self.stdout.write(self.style.SUCCESS(
            "Awards remapped safely by name/slug. Guessed geometry cleared only for matched products; confirmed duplicates disabled; "
            "DesignTemplate rows were not modified."
        ))
