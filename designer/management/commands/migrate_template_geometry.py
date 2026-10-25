from django.core.management.base import BaseCommand, CommandError

from designer.services.template_geometry import (
    snapshot_product_geometry,
    migrate_product_templates,
)


class Command(BaseCommand):
    help = "Audit or force Admin-driven master-template geometry migration for one product."

    def add_arguments(self, parser):
        parser.add_argument("--product-id", type=int, required=True)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply migration. Without this flag the command only prints current Admin geometry.",
        )

    def handle(self, *args, **options):
        product_id = options["product_id"]
        try:
            snapshot = snapshot_product_geometry(product_id)
        except Exception as exc:
            raise CommandError(str(exc))

        self.stdout.write(self.style.NOTICE(f"Product {product_id} Admin geometry:"))
        self.stdout.write(str(snapshot))

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Audit only. Nothing changed."))
            return

        # before_snapshot=None intentionally forces a one-time normalization.
        result = migrate_product_templates(
            product_id=product_id,
            before_snapshot=None,
            reason="management-command",
            changed_by="management-command",
        )
        if result["errors"]:
            raise CommandError("; ".join(result["errors"]))
        self.stdout.write(self.style.SUCCESS(
            f'Migrated {result["templates_migrated"]}/{result["templates_checked"]}; '
            f'unchanged {result["templates_unchanged"]}; backup={result["backup_file"]}'
        ))
