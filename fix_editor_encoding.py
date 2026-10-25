from pathlib import Path

p = Path("templates/designer/editor.html")
s = p.read_text(encoding="utf-8")

replacements = {
    "Â·": "·",
    "Ã—": "×",

    "â†\x90": "←",
    "â†\x91": "↑",
    "â†\x92": "→",
    "â†\x93": "↓",

    "â†¶": "↶",
    "â†·": "↷",

    "âœ•": "✕",
    "âœ“": "✓",
    "âœ”": "✔",

    "â€¢": "•",
    "â€“": "–",
    "â€”": "—",
    "â€¦": "…",

    "Â©": "©",
    "Â®": "®",
    "Â°": "°",
    "Â£": "£",
}

before = s

for bad, good in replacements.items():
    s = s.replace(bad, good)

p.write_text(s, encoding="utf-8")

print("editor.html repaired")
print("Characters changed:", sum(a != b for a, b in zip(before, s)) + abs(len(before)-len(s)))

for marker in ("Â", "Ã", "â", "ð"):
    print(marker, "remaining:", s.count(marker))
