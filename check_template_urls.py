import re
from pathlib import Path
from django.urls import get_resolver

resolver = get_resolver()

namespace = resolver.namespace_dict.get("designer")

if not namespace:
    print("ERROR: designer namespace not found")
    raise SystemExit(1)

designer_resolver = namespace[1]

valid = {
    p.name
    for p in designer_resolver.url_patterns
    if getattr(p, "name", None)
}

print("\nVALID DESIGNER URL NAMES:")
for name in sorted(valid):
    print("  ", name)

print("\nINVALID TEMPLATE REFERENCES:")

found = False

for file in Path("templates").rglob("*.html"):
    text = file.read_text(encoding="utf-8-sig", errors="ignore")

    for line_no, line in enumerate(text.splitlines(), 1):
        matches = re.findall(
            r"""{%\s*url\s+['"]designer:([^'"]+)['"]""",
            line
        )

        for name in matches:
            if name not in valid:
                found = True
                print(f"{file}:{line_no} -> designer:{name}")

if not found:
    print("NONE")