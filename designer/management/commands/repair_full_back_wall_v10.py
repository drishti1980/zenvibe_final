from django.core.management.base import BaseCommand
from django.core.management import call_command
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--product-id",type=int,default=199)
    def handle(self,*a,**o):
        call_command("rebuild_full_back_wall_100",product_id=o["product_id"],count=100,replace=True)
        call_command("verify_full_back_wall_v10",product_id=o["product_id"])
