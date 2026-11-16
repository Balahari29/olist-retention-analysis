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

# ---- credentials must never be in project files
for path in [*report.rglob("*"), *model.parent.rglob("*"), powerbi / "Olist Retention.pbip"]:
    if path.is_file() and re.search(r"(?i)password|pwd\s*=|uid\s*=", path.read_text(encoding="utf-8", errors="ignore")):
        problems.append(f"possible credential text in {path.relative_to(powerbi)}")

print("PROBLEMS:" if problems else "ALL CHECKS PASSED")
for problem in problems:
    print("  -", problem)
sys.exit(1 if problems else 0)
