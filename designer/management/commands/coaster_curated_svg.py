"""Import 100 individually authored SVG coaster artworks as editable Fabric objects.

Place files 001.svg ... 100.svg in designer/coaster_artworks/.
Each SVG uses a 1000x1000 viewBox and native vector shapes.
Unlike the former generator, this module NEVER synthesizes ten repeated themes.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from django.conf import settings

ART_DIR = Path(settings.BASE_DIR) / "designer" / "coaster_artworks"
ALLOWED = {"path", "circle", "ellipse", "rect", "line", "polygon", "polyline", "text"}
PAINT = {"fill", "stroke", "stroke-width", "opacity"}
NUMBER = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)")

def _num(value, default=0.0):
    if value is None:
        return default
    m = NUMBER.search(str(value))
    return float(m.group()) if m else default

def _style(element):
    result = {}
    for key, value in element.attrib.items():
        if key in PAINT:
            result[key] = value
    for item in element.attrib.get("style", "").split(";"):
        if ":" in item:
            key, value = item.split(":", 1)
            if key.strip() in PAINT:
                result[key.strip()] = value.strip()
    return result

def _colour(style, key, fallback="transparent"):
    value = style.get(key, fallback)
    if value in ("none", "", None):
        return "transparent"
    return value

def _absolute_path(data):
    """Normalize SVG M/L/H/V/Q/C/Z paths, including implicit repeated operands.

    SVG relative control points are relative to the command start, not to
    preceding control points. The original parser mispositioned curved art.
    """
    tokens = re.findall(r"[MmLlHhVvQqCcZz]|[-+]?(?:\\d*\\.)?\\d+(?:[eE][-+]?\\d+)?", data)
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6, "Z": 0}
    result = []
    i = 0
    cmd = None
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        if cmd is None:
            raise ValueError("SVG path is missing a command")
        upper = cmd.upper()
        if upper == "Z":
            result.append("Z")
            current = start
            cmd = None
            continue
        count = arity[upper]
        if i + count > len(tokens) or any(t.isalpha() for t in tokens[i:i + count]):
            raise ValueError(f"Incomplete SVG path command {cmd}")
        values = [float(v) for v in tokens[i:i + count]]
        i += count
        ox, oy = current
        relative = cmd.islower()
        if upper == "H":
            x = values[0] + ox if relative else values[0]
            values = [x, oy]
            upper = "L"
        elif upper == "V":
            y = values[0] + oy if relative else values[0]
            values = [ox, y]
            upper = "L"
        elif relative:
            for j in range(0, len(values), 2):
                values[j] += ox
                values[j + 1] += oy
        current = (values[-2], values[-1])
        if upper == "M":
            start = current
            # SVG subsequent coordinate pairs after M are implicit L commands.
            cmd = "l" if relative else "L"
        result.append(upper + " " + " ".join(f"{v:.3f}" for v in values))
    return " ".join(result)

def _parse_svg(file_path, index):
    root = ET.parse(file_path).getroot()
    viewbox = [_num(x) for x in root.attrib.get("viewBox", "0 0 1000 1000").split()]
    if len(viewbox) != 4 or viewbox[:2] != [0, 0] or viewbox[2:] != [1000, 1000]:
        raise ValueError(f"{file_path.name}: viewBox must be '0 0 1000 1000'")
    objects = []
    def visit(parent, inherited=None):
        inherited = inherited or {}
        for child in parent:
            kind = child.tag.rsplit("}", 1)[-1]
            style = dict(inherited)
            style.update(_style(child))
            if kind in ("svg", "g"):
                if child.get("transform"):
                    raise ValueError(f"{file_path.name}: transforms must be flattened before import")
                visit(child, style)
                continue
            if kind not in ALLOWED:
                raise ValueError(f"{file_path.name}: unsupported SVG element {kind!r}; convert it to paths")
            if child.get("transform"):
                raise ValueError(f"{file_path.name}: flatten transform on {kind!r} before import")
            key = f"coaster_{index:03d}_{len(objects):04d}"
            base = dict(id=key, name=child.get("id") or key, type=kind,
                        left=0, top=0, angle=0, scaleX=1, scaleY=1,
                        opacity=_num(style.get("opacity"), 1),
                        selectable=True, evented=True, customerEditable=True,
                        fill=_colour(style, "fill"),
                        stroke=_colour(style, "stroke"),
                        strokeWidth=_num(style.get("stroke-width")))
            if kind == "path":
                base["path"] = _absolute_path(child.get("d", ""))
                if not base["path"]:
                    continue
            elif kind == "circle":
                radius = _num(child.get("r"))
                base.update(type="circle", radius=radius,
                            left=_num(child.get("cx"))-radius,
                            top=_num(child.get("cy"))-radius)
            elif kind == "ellipse":
                rx, ry = _num(child.get("rx")), _num(child.get("ry"))
                base.update(type="ellipse", rx=rx, ry=ry,
                            left=_num(child.get("cx"))-rx,
                            top=_num(child.get("cy"))-ry)
            elif kind == "rect":
                base.update(type="rect", left=_num(child.get("x")),
                            top=_num(child.get("y")), width=_num(child.get("width")),
                            height=_num(child.get("height")))
            elif kind == "line":
                x1, y1 = _num(child.get("x1")), _num(child.get("y1"))
                x2, y2 = _num(child.get("x2")), _num(child.get("y2"))
                base.update(type="path", path=f"M {x1} {y1} L {x2} {y2}", fill="transparent")
            elif kind in ("polygon", "polyline"):
                coords = NUMBER.findall(child.get("points", ""))
                if len(coords) < 4 or len(coords)%2:
                    raise ValueError(f"{file_path.name}: invalid {kind} points")
                pairs = [" ".join(coords[i:i+2]) for i in range(0, len(coords), 2)]
                base.update(type="path", path="M "+" L ".join(pairs)+(" Z" if kind=="polygon" else ""))
            elif kind == "text":
                base.update(type="textbox", text="".join(child.itertext()).strip(),
                            left=_num(child.get("x")), top=_num(child.get("y")),
                            width=_num(child.get("data-width"), 500),
                            fontFamily=child.get("font-family", "Georgia"),
                            fontSize=_num(child.get("font-size"), 32),
                            textAlign=child.get("text-anchor", "start").replace("middle", "center"))
            objects.append(base)
    visit(root)
    if not objects:
        raise ValueError(f"{file_path.name}: no editable SVG elements")
    return objects

def validate_library():
    paths = [ART_DIR / f"{i:03d}.svg" for i in range(1, 101)]
    missing = [p.name for p in paths if not p.is_file()]
    if missing:
        raise ValueError(
            f"Curated coaster library incomplete: {len(missing)} missing SVGs "
            f"(first: {', '.join(missing[:10])}). "
            "Do not publish generated duplicates as replacements."
        )
    seen = {}
    for path in paths:
        # Ignore comments/whitespace, but reject identical authored artwork.
        tree = ET.parse(path)
        digest = hashlib.sha256(ET.tostring(tree.getroot())).hexdigest()
        if digest in seen:
            raise ValueError(f"Identical SVG files: {seen[digest]} and {path.name}")
        seen[digest] = path.name
    return paths

def load_curated_artwork(index):
    if not 0 <= index < 100:
        raise ValueError("Artwork index must be 0..99")
    validate_library()
    return _parse_svg(ART_DIR / f"{index+1:03d}.svg", index)
