"""Validate the PBIR report against Desktop's own JSON schemas, and cross-check every field reference
against the TMDL model. Usage: python validate_report.py <powerbi_dir> <schema_root>
"""
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource

powerbi, schema_root = Path(sys.argv[1]), Path(sys.argv[2])
report = powerbi / "Olist Retention.Report"
model = powerbi / "Olist Retention.SemanticModel" / "definition"
problems = []

# ---- schema registry from the schemas extracted from Desktop
resources = []
for path in schema_root.rglob("schema.json"):
    doc = json.loads(path.read_text(encoding="utf-8"))
    resources.append((doc["$id"], Resource.from_contents(doc, default_specification=__import__("referencing").jsonschema.DRAFT7)))
registry = Registry().with_resources(resources)

checked = 0
for path in sorted((report / "definition").rglob("*.json")):
    doc = json.loads(path.read_text(encoding="utf-8"))
    schema_id = doc["$schema"]
    try:
        schema = registry.contents(schema_id)
    except Exception:
        problems.append(f"{path.relative_to(powerbi)}: schema not shipped by Desktop: {schema_id}")
        continue
    validator = Draft7Validator(schema, registry=registry)
    for error in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
        problems.append(f"{path.relative_to(powerbi)}: {'/'.join(map(str, error.path))}: {error.message[:300]}")
    checked += 1
print(f"schema-validated files: {checked}")

# ---- model inventory from TMDL (tables, columns, measures)
inventory = {}
for tmdl in (model / "tables").glob("*.tmdl"):
    text = tmdl.read_text(encoding="utf-8")
    table = re.search(r"^table (.+)$", text, re.M).group(1).strip().strip("'")
    names = set()
    for match in re.finditer(r"^\t(column|measure) ('(?:[^']|'')+'|[^\s=]+)", text, re.M):
        names.add(match.group(2).strip("'").replace("''", "'"))
    inventory[table] = names


def walk(node, found):
    if isinstance(node, dict):
        for kind in ("Column", "Measure"):
            if kind in node and isinstance(node[kind], dict) and "Property" in node[kind]:
                source = node[kind]["Expression"].get("SourceRef", {})
                if "Entity" in source:
                    found.append((kind, source["Entity"], node[kind]["Property"]))
        for value in node.values():
            walk(value, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, found)


field_refs, filter_names, visual_count = [], [], 0
for path in (report / "definition" / "pages").rglob("*.json"):
    doc = json.loads(path.read_text(encoding="utf-8"))
    walk(doc, field_refs)
    for f in doc.get("filterConfig", {}).get("filters", []):
        filter_names.append(f["name"])
    if path.name == "visual.json":
        visual_count += 1
        position = doc["position"]
        if position["x"] + position["width"] > 1280 or position["y"] + position["height"] > 720:
            problems.append(f"{path.relative_to(powerbi)}: visual outside the 1280x720 page")
missing = sorted({(k, e, p) for k, e, p in field_refs if p not in inventory.get(e, set())})
for kind, entity, prop in missing:
    problems.append(f"field not in model: {kind} {entity}[{prop}]")
print(f"field references checked: {len(field_refs)} (distinct {len(set(field_refs))}), visuals: {visual_count}")
duplicates = {n for n in filter_names if filter_names.count(n) > 1}
if duplicates:
    problems.append(f"duplicate filter names: {duplicates}")

# ---- structure and references
pages_meta = json.loads((report / "definition/pages/pages.json").read_text(encoding="utf-8"))
page_dirs = {p.name for p in (report / "definition/pages").iterdir() if p.is_dir()}
if set(pages_meta["pageOrder"]) != page_dirs:
    problems.append(f"pages.json pageOrder {pages_meta['pageOrder']} != page folders {page_dirs}")
for page_dir in page_dirs:
    page = json.loads((report / "definition/pages" / page_dir / "page.json").read_text(encoding="utf-8"))
    if page["name"] != page_dir:
        problems.append(f"page name {page['name']} != folder {page_dir}")
    binding = page.get("pageBinding")
    if binding:
        names = {f["name"] for f in page.get("filterConfig", {}).get("filters", [])}
        for parameter in binding.get("parameters", []):
            if parameter["boundFilter"] not in names:
                problems.append(f"drill-through parameter bound to missing filter {parameter['boundFilter']}")
for visual_dir in (report / "definition/pages").glob("*/visuals/*"):
    visual = json.loads((visual_dir / "visual.json").read_text(encoding="utf-8"))
    if visual["name"] != visual_dir.name:
        problems.append(f"visual name {visual['name']} != folder {visual_dir.name}")

report_json = json.loads((report / "definition/report.json").read_text(encoding="utf-8"))
for package in report_json["resourcePackages"]:
    for item in package["items"]:
        resource = report / "StaticResources" / package["name"] / item["path"]
        if not resource.exists():
            problems.append(f"missing resource file {resource.relative_to(powerbi)}")
        else:
            json.loads(resource.read_text(encoding="utf-8"))
pbir = json.loads((report / "definition.pbir").read_text(encoding="utf-8"))
if not (report / pbir["datasetReference"]["byPath"]["path"] / "definition.pbism").exists():
    problems.append("definition.pbir does not point at the semantic model folder")
pbip = json.loads((powerbi / "Olist Retention.pbip").read_text(encoding="utf-8"))
for artifact in pbip["artifacts"]:
    if not (powerbi / artifact["report"]["path"] / "definition.pbir").exists():
        problems.append(f"pbip artifact path missing: {artifact}")

# ---- layout: overlapping visuals and clipped KPI cards / slicers
# The clipping check is an estimate from font sizes (it cannot render the report): text height = points * 4/3 px
# * 1.35 line spacing. It caught the Stage 4 problem (12 pt container title + 14/16 px theme padding on 86 px cards).
LINE = 4 / 3 * 1.35                                   # px of height per point of font size
SLICER_CONTROL_PX = {"Between": 48, "Dropdown": 32}   # date inputs + slider / one dropdown box


def literal(properties, name, default=None):
    """Value of a formatting property like {"expr": {"Literal": {"Value": "8D"}}} -> "8D"."""
    try:
        return properties[name]["expr"]["Literal"]["Value"]
    except (KeyError, TypeError):
        return default


def number(value):
    return float(str(value).rstrip("DL"))


base_theme = json.loads((report / "StaticResources/SharedResources/BaseThemes/Fluent2-CY26SU10.json")
                        .read_text(encoding="utf-8-sig"))


def theme_padding(visual_type):
    """Default container padding from the base theme: the visual type's own style (slicer = 0), else '*'."""
    styles = base_theme["visualStyles"]
    for paddings in (styles.get(visual_type, {}).get("*", {}).get("padding", []), styles["*"]["*"]["padding"]):
        for padding in paddings:
            if "top" in padding:
                return padding
    return {"top": 0, "bottom": 0}


def container_box(visual):
    """(padding top+bottom, title height in px) of a visual container, after its own overrides."""
    objects = visual["visual"].get("visualContainerObjects", {})
    pad = objects.get("padding", [{}])[0].get("properties", {})
    defaults = theme_padding(visual["visual"]["visualType"])
    vertical = sum(number(literal(pad, side, defaults[side])) for side in ("top", "bottom"))
    title = objects.get("title", [{}])[0].get("properties", {})
    title_shown = literal(title, "show", "true") == "true"   # the custom theme shows a title on every visual
    title_px = number(literal(title, "fontSize", 12)) * LINE if title_shown else 0
    return vertical, title_px


overlaps = clipped = 0
for page_dir in sorted((report / "definition/pages").iterdir()):
    if not page_dir.is_dir():
        continue
    boxes = []
    for visual_path in sorted(page_dir.glob("visuals/*/visual.json")):
        visual = json.loads(visual_path.read_text(encoding="utf-8-sig"))
        pos, kind = visual["position"], visual["visual"]["visualType"]
        boxes.append((visual["name"], kind, pos["x"], pos["y"], pos["x"] + pos["width"], pos["y"] + pos["height"]))
        vertical, title_px = container_box(visual)
        objects = visual["visual"].get("objects", {})
        if kind == "card":
            value_pt = number(literal(objects.get("labels", [{}])[0].get("properties", {}), "fontSize", 24))
            label = objects.get("categoryLabels", [{}])[0].get("properties", {})
            label_pt = number(literal(label, "fontSize", 10)) if literal(label, "show", "true") == "true" else 0
            needed = (value_pt + label_pt) * LINE
        elif kind == "slicer":
            mode = literal(objects.get("data", [{}])[0].get("properties", {}), "mode", "'Basic'").strip("'")
            header_shown = literal(objects.get("header", [{}])[0].get("properties", {}), "show", "true") == "true"
            needed = SLICER_CONTROL_PX.get(mode, 40) + (12 * LINE if header_shown else 0)
        else:
            continue
        available = pos["height"] - vertical - title_px
        if available < needed:
            clipped += 1
            problems.append(f"{visual_path.relative_to(powerbi)}: {kind} content likely clipped: needs ~{needed:.0f} px, "
                            f"has {available:.0f} px (height {pos['height']} - padding {vertical:.0f} - title {title_px:.0f})")
    for i, first in enumerate(boxes):
        for second in boxes[i + 1:]:
            if first[2] < second[4] and second[2] < first[4] and first[3] < second[5] and second[3] < first[5]:
                overlaps += 1
                problems.append(f"{page_dir.name}: {first[1]} {first[0]} overlaps {second[1]} {second[0]}")
print(f"layout checked: {overlaps} overlapping pairs, {clipped} cards/slicers likely clipped")

# ---- credentials must never be in project files
# Skips Desktop's local-only files, which .gitignore keeps out of the repo: cache.abf (compressed imported data,
# whose random bytes can spell "uid=") and localSettings.json.
LOCAL_ONLY = {"cache.abf", "localSettings.json"}
for path in [*report.rglob("*"), *model.parent.rglob("*"), powerbi / "Olist Retention.pbip"]:
    if path.is_file() and path.name not in LOCAL_ONLY and re.search(r"(?i)password|pwd\s*=|uid\s*=", path.read_text(encoding="utf-8", errors="ignore")):
        problems.append(f"possible credential text in {path.relative_to(powerbi)}")

print("PROBLEMS:" if problems else "ALL CHECKS PASSED")
for problem in problems:
    print("  -", problem)
sys.exit(1 if problems else 0)
