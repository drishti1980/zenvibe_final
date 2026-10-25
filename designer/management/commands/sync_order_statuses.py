from django.core.management.base import BaseCommand
from designer.services.order_workflow import sync_all_orders
class Command(BaseCommand):
    help = "Advance ZenVibe order statuses using Order Workflow Configuration. Safe for cPanel cron."
    def handle(self, *args, **options):
        changed = sync_all_orders()
        self.stdout.write(self.style.SUCCESS(f"Updated {changed} order(s)."))
