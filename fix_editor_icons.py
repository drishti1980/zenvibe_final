from pathlib import Path

p = Path("templates/designer/editor.html")
s = p.read_text(encoding="utf-8")

replacements = {
    "â–¦": "▦",
    "â—ˆ": "◈",
    "â‡§": "⇧",
    "âœ¦": "✦",
    "â–£": "▣",
    "âŒ˜": "⌘",
    "â˜º": "☺",
    "â–§": "▧",
    "â˜·": "☷",
    "âŒ•": "⌕",

    "â¬Ÿ": "⬟",
    "â¬¢": "⬢",
    "â˜…": "★",
    "â™¥": "♥",
    "âžœ": "➜",
    "â–°": "▰",
    "â”\x81": "━",
    "â”…": "┅",
    "âœš": "✚",

    "ðŸ“·": "📷",

    "âž¤": "➤",
    "âœŽ": "✎",
    "â—\x8f": "●",
    "â•±": "╱",
    "â—©": "◩",

    "âŒ„": "⌄",
    "â€¹": "‹",
    "â€º": "›",
    "âˆ’": "−",
    "ï¼‹": "＋",
}

changed = []

for bad, good in replacements.items():
    count = s.count(bad)
    if count:
        s = s.replace(bad, good)
        changed.append((repr(bad), good, count))

p.write_text(s, encoding="utf-8")

print("FIXED:")
for bad, good, count in changed:
    print(f"  {bad} -> {good}  x{count}")

print()
print("Remaining:")
for marker in ("Â", "Ã", "â", "ð", "ï¼"):
    print(marker, s.count(marker))
