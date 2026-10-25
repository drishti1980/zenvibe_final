from pathlib import Path
import shutil
from datetime import datetime

ROOTS = [Path("templates"), Path("static")]
EXTS = {".html", ".js", ".css"}
BAD = ("Ã", "Â", "â", "ðŸ", "ï¼")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = Path(f"BACKUP_BEFORE_ENCODING_FIX_{stamp}")

fixed_files = []
fixed_lines = 0

def bad_score(s):
    return sum(s.count(x) for x in BAD)

def repair_line(line):
    original = line
    current = line

    # Repair only when conversion actually reduces mojibake.
    for _ in range(2):
        try:
            candidate = current.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

        if bad_score(candidate) < bad_score(current):
            current = candidate
        else:
            break

    return current if bad_score(current) < bad_score(original) else original

for root in ROOTS:
    if not root.exists():
        continue

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue

        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue

        if not any(x in text for x in BAD):
            continue

        lines = text.splitlines(keepends=True)
        repaired = []
        changed = 0

        for line in lines:
            new_line = repair_line(line)
            if new_line != line:
                changed += 1
            repaired.append(new_line)

        if not changed:
            continue

        relative = path
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

        path.write_text("".join(repaired), encoding="utf-8")

        fixed_files.append(str(path))
        fixed_lines += changed
        print(f"FIXED: {path} ({changed} lines)")

print()
print("Backup:", backup)
print("Files repaired:", len(fixed_files))
print("Lines repaired:", fixed_lines)
