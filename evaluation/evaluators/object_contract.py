"""
Manifest & object-numbering contract check for AL extensions.

Two things this validates, both deterministic (no LLM needed):
  1. app.json is structurally correct: valid GUID id, 4-part version strings,
     well-formed idRanges.
  2. Every object ID (table/page/codeunit extension, etc.) and every new
     field ID actually declared in the .al source falls inside the range(s)
     the manifest itself declares in idRanges — not a hardcoded band, so
     this works regardless of which per-tenant range a given job asks for.
"""

import json
import re
from pathlib import Path

GUID_PATTERN = re.compile(
    r'^\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?$'
)
VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+\.\d+$')

# Matches top-level AL object declarations with an explicit numeric ID, e.g.:
#   tableextension 50100 "Customer Loyalty Ext" extends Customer
#   pageextension 50100 "Customer Card Loyalty Ext" extends "Customer Card"
#   codeunit 50101 "Some Codeunit"
OBJECT_DECL_PATTERN = re.compile(
    r'\b(tableextension|pageextension|table|page|codeunit|report|query|xmlport|enum)\s+'
    r'(\d+)\s+"?([^"\n{]+?)"?\s*(?:extends|{)',
    re.IGNORECASE,
)

# Matches new field declarations inside a fields{} block, e.g.:
#   field(50100; "Loyalty Points"; Integer)
# Deliberately does NOT match modify("Existing Field") blocks, which have
# no leading numeric ID.
FIELD_DECL_PATTERN = re.compile(
    r'\bfield\s*\(\s*(\d+)\s*;\s*"?([^";]+?)"?\s*;',
    re.IGNORECASE,
)


def validate_manifest_structure(manifest: dict) -> list[str]:
    """Returns a list of structural problems found in app.json. Empty list = clean."""
    problems = []

    app_id = manifest.get("id", "")
    if not GUID_PATTERN.match(app_id):
        problems.append(f"app.json 'id' is not a valid GUID: '{app_id}'")

    for field in ("version", "application", "platform"):
        value = manifest.get(field, "")
        if not VERSION_PATTERN.match(value):
            problems.append(
                f"app.json '{field}' is not a valid 4-part version (x.y.z.w): '{value}'"
            )

    for required in ("name", "publisher"):
        if not manifest.get(required):
            problems.append(f"app.json is missing required field: '{required}'")

    id_ranges = manifest.get("idRanges", [])
    if not id_ranges:
        problems.append("app.json has no 'idRanges' declared")
    else:
        for r in id_ranges:
            if "from" not in r or "to" not in r:
                problems.append(f"idRanges entry missing 'from'/'to': {r}")
            elif r["from"] > r["to"]:
                problems.append(f"idRanges entry has from > to: {r}")

    return problems


def id_in_ranges(object_id: int, id_ranges: list[dict]) -> bool:
    return any(r.get("from", 0) <= object_id <= r.get("to", -1) for r in id_ranges)


def _find_matching_brace(text: str, opening_brace_index: int) -> int:
    """Returns the index of the matching closing brace for a given opening brace."""
    depth = 0
    for i in range(opening_brace_index, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def find_object_and_field_ids(al_files: list[Path]) -> list[dict]:
    """Scans .al source for every object/field declaration with an explicit numeric ID."""
    declarations = []
    for f in al_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in OBJECT_DECL_PATTERN.finditer(content):
            object_kind = match.group(1).lower()
            declarations.append({
                "file": f.name,
                "kind": object_kind,
                "id": int(match.group(2)),
                "name": match.group(3).strip(),
            })

            # Only field IDs declared in extension objects should be constrained
            # by app.json idRanges. New table/page objects can use low sequential
            # IDs for their internal fields.
            if object_kind not in {"tableextension", "pageextension"}:
                continue

            block_start = content.find("{", match.end())
            if block_start == -1:
                continue

            block_end = _find_matching_brace(content, block_start)
            if block_end == -1:
                continue

            object_block = content[block_start:block_end + 1]
            for field_match in FIELD_DECL_PATTERN.finditer(object_block):
                declarations.append({
                    "file": f.name,
                    "kind": "field",
                    "id": int(field_match.group(1)),
                    "name": field_match.group(2).strip(),
                })

    return declarations


def run_manifest_validation_on_job(project_dir: Path) -> dict:
    project_dir = Path(project_dir)
    app_json_path = project_dir / "app.json"

    if not app_json_path.exists():
        return {"status": "error", "error": "app.json not found in project_dir"}

    try:
        manifest = json.loads(app_json_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"app.json is not valid JSON: {e}"}

    structural_problems = validate_manifest_structure(manifest)
    id_ranges = manifest.get("idRanges", [])

    al_files = list(project_dir.rglob("*.al"))
    declarations = find_object_and_field_ids(al_files)

    out_of_range = [
        d for d in declarations
        if id_ranges and not id_in_ranges(d["id"], id_ranges)
    ]

    passed = not structural_problems and not out_of_range

    return {
        "status": "success",
        "passed": passed,
        "declared_id_ranges": id_ranges,
        "structural_problems": structural_problems,
        "objects_checked": len(declarations),
        "out_of_range_declarations": out_of_range,
        "all_declarations": declarations,
    }