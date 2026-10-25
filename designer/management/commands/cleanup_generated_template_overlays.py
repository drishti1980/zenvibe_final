from django.core.management.base import BaseCommand
from designer.models import DesignTemplate


class Command(BaseCommand):
    help = "Remove duplicated autoInvitationField/autoInvitationCover objects from templates."

    def add_arguments(self, parser):
        parser.add_argument("--template-id", type=int)
        parser.add_argument("--all", action="store_true")

    def handle(self, *args, **options):
        qs = DesignTemplate.objects.all()
        if options.get("template_id"):
            qs = qs.filter(pk=options["template_id"])
        elif not options.get("all"):
            self.stderr.write("Use --all or --template-id ID")
            return
        changed=0
        removed=0
        for template in qs:
            data=template.json_data or {}
            pages=data.get("pages") or []
            dirty=False
            for page in pages:
                objects=page.get("objects") or []
                kept=[]
                for obj in objects:
                    if obj.get("autoInvitationField") or obj.get("autoInvitationCover"):
                        removed += 1
                        dirty=True
                    else:
                        kept.append(obj)
                page["objects"]=kept
            if dirty:
                template.json_data=data
                template.save(update_fields=["json_data", "updated_at"])
                changed += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {changed} template(s); removed {removed} generated overlay object(s)."))
