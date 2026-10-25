import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from designer.models import Product

URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.I)
CONTENT_FIELDS = (
    "short_description", "description", "product_information",
    "printing_method", "design_guidelines", "printing_guidelines", "faqs",
)


def walk(value, path=""):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(value, str):
        for match in URL_RE.findall(value):
            yield path, match


class Command(BaseCommand):
    help = "Audit product DB and project text files for external runtime dependencies."

    def add_arguments(self, parser):
        parser.add_argument("--legacy-host", required=True)
        parser.add_argument("--project-root", default=".")
        parser.add_argument("--json", default="external_dependency_audit.json")

    def handle(self, *args, **opts):
        legacy = opts["legacy_host"].lower().lstrip("www.")
        findings = {"database": [], "code": []}

        for p in Product.objects.all().order_by("id"):
            for field in CONTENT_FIELDS:
                value = getattr(p, field, "") or ""
                if legacy in value.lower():
                    findings["database"].append({"product_id": p.id, "field": field, "type": "legacy-host"})
                for url in URL_RE.findall(value):
                    findings["database"].append({"product_id": p.id, "field": field, "type": "external-url", "url": url})
            for path, url in walk(p.source_attributes or {}):
                findings["database"].append({"product_id": p.id, "field": f"source_attributes:{path}", "type": "external-url", "url": url})

        root = Path(opts["project_root"]).resolve()
        ignored = {".git", "venv", ".venv", "node_modules", "__pycache__", "media"}
        for path in root.rglob("*"):
            if not path.is_file() or any(part in ignored for part in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".html", ".js", ".css", ".json", ".txt", ".md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if legacy in text.lower():
                for no, line in enumerate(text.splitlines(), 1):
                    if legacy in line.lower():
                        findings["code"].append({"file": str(path.relative_to(root)), "line": no, "text": line.strip()[:300]})

        Path(opts["json"]).write_text(json.dumps(findings, indent=2, ensure_ascii=False), encoding="utf-8")
        db_count = len(findings["database"])
        code_count = len(findings["code"])
        if db_count or code_count:
            self.stdout.write(self.style.ERROR(f"DEPENDENCIES FOUND: database={db_count}, code={code_count}"))
            self.stdout.write(self.style.WARNING(f"See {opts['json']}"))
        else:
            self.stdout.write(self.style.SUCCESS("PASS: zero legacy-host references found in product DB or project text files."))
