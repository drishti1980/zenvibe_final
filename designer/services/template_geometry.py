"""
Admin-driven template geometry migration.

Source of truth:
1. Active ProductPrintSurface rows (page-by-page)
2. Matching active ProductSizeVariant for single-surface templates
3. Product.print_width_in / print_height_in fallback

This service permanently remaps DesignTemplate.json_data when Admin physical
dimensions change. Customer SavedDesign rows are intentionally NOT rewritten:
an ordered/customer design must retain the geometry it was created with.
"""
from __future__ import annotations

import copy
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction

LOGICAL_BASE_WIDTH = 1200
RATIO_TOLERANCE = 0.002


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _positive_pair(w, h):
    return _f(w) > 0 and _f(h) > 0


def _logical_size(width_in, height_in, base_width=LOGICAL_BASE_WIDTH):
    width_in, height_in = _f(width_in), _f(height_in)
    if not _positive_pair(width_in, height_in):
        return None
    w = int(base_width)
    h = max(1, int(round(w * height_in / width_in)))
    return w, h


def _surface_dict(s):
    return {
        "id": s.id,
        "label": s.label,
        "widthIn": _f(s.print_width_in),
        "heightIn": _f(s.print_height_in),
        "sortOrder": s.sort_order,
        "active": bool(s.is_active),
    }


def _variant_dict(v):
    return {
        "id": v.id,
        "key": v.size_key,
        "name": v.name,
        "widthIn": _f(v.print_width_in),
        "heightIn": _f(v.print_height_in),
        "canvasWidth": v.canvas_width,
        "canvasHeight": v.canvas_height,
        "active": bool(v.is_active),
    }


def snapshot_product_geometry(product_id):
    """Read the current persisted geometry before an Admin save."""
    if not product_id:
        return None
    from designer.models import Product

    p = (
        Product.objects
        .prefetch_related("print_surfaces", "size_variants")
        .get(pk=product_id)
    )
    return {
        "productId": p.id,
        "product": {
            "widthIn": _f(p.print_width_in),
            "heightIn": _f(p.print_height_in),
        },
        "surfaces": [
            _surface_dict(s)
            for s in p.print_surfaces.filter(is_active=True).order_by("sort_order", "id")
        ],
        "variants": [
            _variant_dict(v)
            for v in p.size_variants.filter(is_active=True).order_by("sort_order", "id")
        ],
    }


def _snapshot_equal(a, b):
    def normalized(x):
        if not x:
            return None
        return {
            "product": x.get("product") or {},
            "surfaces": [
                {
                    "id": s.get("id"),
                    "label": s.get("label"),
                    "widthIn": round(_f(s.get("widthIn")), 6),
                    "heightIn": round(_f(s.get("heightIn")), 6),
                    "sortOrder": s.get("sortOrder"),
                }
                for s in x.get("surfaces", [])
            ],
            "variants": [
                {
                    "id": v.get("id"),
                    "key": v.get("key"),
                    "widthIn": round(_f(v.get("widthIn")), 6),
                    "heightIn": round(_f(v.get("heightIn")), 6),
                    "canvasWidth": v.get("canvasWidth"),
                    "canvasHeight": v.get("canvasHeight"),
                }
                for v in x.get("variants", [])
            ],
        }
    return normalized(a) == normalized(b)


def _page_size(page, document=None):
    """Find the logical coordinate size the stored page currently uses."""
    if not isinstance(page, dict):
        return None

    candidates = [
        (page.get("documentWidth"), page.get("documentHeight")),
        (page.get("width"), page.get("height")),
    ]
    canvas = page.get("canvas")
    if isinstance(canvas, dict):
        candidates.append((canvas.get("width"), canvas.get("height")))

    if isinstance(document, dict):
        candidates.extend([
            (document.get("width"), document.get("height")),
            (document.get("documentWidth"), document.get("documentHeight")),
        ])

    for w, h in candidates:
        if _positive_pair(w, h):
            return _f(w), _f(h)
    return None


def _scale_object(obj, sx, sy):
    """
    Remap a Fabric object from old page coordinates to new page coordinates.

    Position is remapped directly. Visual size is remapped through scaleX/scaleY,
    which avoids corrupting intrinsic image/text/path dimensions.
    """
    if not isinstance(obj, dict):
        return

    for key in ("left", "x", "x1", "x2"):
        if isinstance(obj.get(key), (int, float)):
            obj[key] = obj[key] * sx
    for key in ("top", "y", "y1", "y2"):
        if isinstance(obj.get(key), (int, float)):
            obj[key] = obj[key] * sy

    obj["scaleX"] = _f(obj.get("scaleX"), 1.0) * sx
    obj["scaleY"] = _f(obj.get("scaleY"), 1.0) * sy

    # Clip paths/groups can contain their own Fabric objects.
    if isinstance(obj.get("clipPath"), dict):
        _scale_object(obj["clipPath"], sx, sy)
    if isinstance(obj.get("objects"), list):
        for child in obj["objects"]:
            _scale_object(child, sx, sy)


def _surface_for_page(new_snapshot, page, index, data):
    surfaces = new_snapshot.get("surfaces") or []
    if surfaces:
        # Stable surface id wins when a template already carries it.
        sid = page.get("surfaceId") if isinstance(page, dict) else None
        if sid is not None:
            for s in surfaces:
                if str(s.get("id")) == str(sid):
                    return s
        # Otherwise Admin sort order defines page order.
        if index < len(surfaces):
            return surfaces[index]
        return None

    # Single-surface template: a size-specific Admin variant can own geometry.
    size_key = (
        (page.get("sizeKey") if isinstance(page, dict) else None)
        or data.get("sizeKey")
        or data.get("selectedSizeKey")
        or ""
    )
    if size_key:
        for v in new_snapshot.get("variants") or []:
            if v.get("key") == size_key and _positive_pair(v.get("widthIn"), v.get("heightIn")):
                return {
                    "id": None,
                    "label": v.get("name") or size_key,
                    "widthIn": v["widthIn"],
                    "heightIn": v["heightIn"],
                    "sortOrder": 0,
                    "sizeKey": size_key,
                }

    product = new_snapshot.get("product") or {}
    if _positive_pair(product.get("widthIn"), product.get("heightIn")):
        return {
            "id": None,
            "label": "Print Area",
            "widthIn": product["widthIn"],
            "heightIn": product["heightIn"],
            "sortOrder": 0,
        }
    return None


def _set_page_geometry(page, surface, new_w, new_h):
    page["width"] = new_w
    page["height"] = new_h
    page["documentWidth"] = new_w
    page["documentHeight"] = new_h

    canvas = page.get("canvas")
    if not isinstance(canvas, dict):
        canvas = {}
        page["canvas"] = canvas
    canvas["width"] = new_w
    canvas["height"] = new_h

    physical = page.get("physical")
    if not isinstance(physical, dict):
        physical = {}
        page["physical"] = physical
    physical.update({
        "widthIn": surface["widthIn"],
        "heightIn": surface["heightIn"],
        "unit": "in",
    })
    if surface.get("id") is not None:
        page["surfaceId"] = surface["id"]
    if surface.get("label"):
        page.setdefault("name", surface["label"])


def migrate_template_json(data, new_snapshot):
    """Return (new_json, changed, notes). Never mutates the caller's object."""
    result = copy.deepcopy(data or {})
    pages = result.get("pages")
    if not isinstance(pages, list) or not pages:
        # Legacy one-page JSON: treat the document itself as a page only when
        # it actually carries an objects list.
        if isinstance(result.get("objects"), list):
            pages = [result]
            root_is_page = True
        else:
            return result, False, ["No editable pages/objects found; skipped safely."]
    else:
        root_is_page = False

    changed = False
    notes = []
    root_document = result.get("document") if isinstance(result.get("document"), dict) else {}

    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        surface = _surface_for_page(new_snapshot, page, index, result)
        if not surface or not _positive_pair(surface.get("widthIn"), surface.get("heightIn")):
            notes.append(f"Page {index + 1}: no complete Admin physical dimensions; unchanged.")
            continue

        target = _logical_size(surface["widthIn"], surface["heightIn"])
        if not target:
            continue
        new_w, new_h = target
        old = _page_size(page, root_document if index == 0 else None)

        # If old logical size is unknown, establish metadata but do not guess how
        # to transform artwork coordinates.
        if not old:
            _set_page_geometry(page, surface, new_w, new_h)
            changed = True
            notes.append(f"Page {index + 1}: geometry metadata established; objects not guessed/scaled.")
            continue

        old_w, old_h = old
        sx, sy = new_w / old_w, new_h / old_h
        if abs(sx - 1.0) > 1e-9 or abs(sy - 1.0) > 1e-9:
            for obj in page.get("objects") or []:
                _scale_object(obj, sx, sy)
            changed = True

        before_meta = (
            _f(page.get("width")), _f(page.get("height")),
            _f((page.get("physical") or {}).get("widthIn")),
            _f((page.get("physical") or {}).get("heightIn")),
        )
        _set_page_geometry(page, surface, new_w, new_h)
        after_meta = (float(new_w), float(new_h), _f(surface["widthIn"]), _f(surface["heightIn"]))
        if before_meta != after_meta:
            changed = True

        notes.append(
            f'Page {index + 1}: {old_w:g}×{old_h:g} logical → '
            f'{new_w}×{new_h}; Admin {surface["widthIn"]:g}×{surface["heightIn"]:g} in.'
        )

    # Keep top-level document aligned to page 1 for editor compatibility.
    if pages:
        first = pages[0]
        if _positive_pair(first.get("width"), first.get("height")):
            doc = result.get("document")
            if not isinstance(doc, dict):
                doc = {}
                result["document"] = doc
            new_doc = {
                "width": int(_f(first["width"])),
                "height": int(_f(first["height"])),
                "unit": "in",
            }
            physical = first.get("physical") or {}
            if _positive_pair(physical.get("widthIn"), physical.get("heightIn")):
                new_doc["physical"] = {
                    "widthIn": _f(physical["widthIn"]),
                    "heightIn": _f(physical["heightIn"]),
                    "unit": "in",
                }
            for k, v in new_doc.items():
                if doc.get(k) != v:
                    doc[k] = v
                    changed = True

    if root_is_page:
        # result itself was modified through pages[0].
        pass

    return result, changed, notes


def _backup_templates(product, templates, before_snapshot, after_snapshot, reason, changed_by):
    if not templates:
        return None

    backup_dir = Path(settings.MEDIA_ROOT) / "template_geometry_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"product-{product.id}-{stamp}.json"

    payload = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "productId": product.id,
        "productName": product.name,
        "reason": reason,
        "changedBy": changed_by or "",
        "beforeGeometry": before_snapshot,
        "afterGeometry": after_snapshot,
        "templates": [
            {"id": t.id, "name": t.name, "json_data": t.json_data}
            for t in templates
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


@transaction.atomic
def migrate_product_templates(product_id, before_snapshot=None, reason="manual", changed_by=""):
    """
    Permanently migrate all master DesignTemplate JSON for one product.

    A full JSON backup is written before any template row is changed.
    """
    from designer.models import Product, DesignTemplate

    product = Product.objects.select_for_update().get(pk=product_id)
    after = snapshot_product_geometry(product_id)

    # New products or Admin saves that did not change geometry need no rewrite.
    if before_snapshot is not None and _snapshot_equal(before_snapshot, after):
        return {
            "geometry_changed": False,
            "templates_checked": 0,
            "templates_migrated": 0,
            "templates_unchanged": 0,
            "errors": [],
            "backup_file": None,
        }

    templates = list(
        DesignTemplate.objects.select_for_update()
        .filter(product_id=product_id)
        .order_by("id")
    )

    plans = []
    errors = []
    unchanged = 0
    for template in templates:
        try:
            migrated, changed, notes = migrate_template_json(template.json_data or {}, after)
            if changed:
                plans.append((template, migrated, notes))
            else:
                unchanged += 1
        except Exception as exc:
            errors.append(f"Template {template.id} ({template.name}): {exc}")

    # If any template could not be analysed, abort rather than leave a partial library.
    if errors:
        transaction.set_rollback(True)
        return {
            "geometry_changed": True,
            "templates_checked": len(templates),
            "templates_migrated": 0,
            "templates_unchanged": unchanged,
            "errors": errors,
            "backup_file": None,
        }

    backup_file = _backup_templates(
        product, templates, before_snapshot, after, reason, changed_by
    ) if plans else None

    for template, migrated, notes in plans:
        template.json_data = migrated
        template.save(update_fields=["json_data", "updated_at"])

    return {
        "geometry_changed": True,
        "templates_checked": len(templates),
        "templates_migrated": len(plans),
        "templates_unchanged": unchanged,
        "errors": [],
        "backup_file": backup_file,
    }
