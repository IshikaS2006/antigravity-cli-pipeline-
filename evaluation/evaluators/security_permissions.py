"""
Security / role-based permission evaluator for AL projects.

Checks implemented:
  1. Required permission sets exist: Front Desk, Finance, Admin.
  2. Front Desk permission set does NOT include refund-related permissions.
  3. Finance permission set DOES include refund-related permissions (soft check —
     see note below on why this is reported as informational, not a hard failure).

This evaluator is deterministic and based on parsing AL `permissionset` objects.
"""

import re
from pathlib import Path

PERMISSIONSET_DECL_PATTERN = re.compile(
    r'\bpermissionset\s+(\d+)\s+"([^"]+)"\s*\{',
    re.IGNORECASE,
)

PERMISSION_ENTRY_PATTERN = re.compile(
    r'\b(?P<object_type>tabledata|table|page|codeunit|report|query|xmlport|enum|permissionset)\s+'
    r'(?:"(?P<quoted_name>[^"]+)"|(?P<plain_name>[^=,;\n]+?))\s*=\s*(?P<rights>[A-Z]+)',
    re.IGNORECASE,
)

REQUIRED_ROLES = {
    "front_desk": "front desk",
    "finance": "finance",
    "admin": "admin",
}

REFUND_KEYWORDS = ("refund",)


def _find_matching_brace(text: str, opening_brace_index: int) -> int:
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


def _normalize_name(value: str) -> str:
    # AL object names commonly use underscores or hyphens instead of spaces
    # (e.g. "HOTEL_FRONT_DESK"). Normalize those to spaces too, or multi-word
    # role labels like "front desk" will never match a real permission set name.
    value = value.replace("_", " ").replace("-", " ")
    return " ".join(value.lower().split())


def _extract_permissionset_entries(content: str) -> list[dict]:
    permission_sets = []

    for match in PERMISSIONSET_DECL_PATTERN.finditer(content):
        set_id = int(match.group(1))
        set_name = match.group(2).strip()

        block_start = content.find("{", match.end() - 1)
        if block_start == -1:
            continue
        block_end = _find_matching_brace(content, block_start)
        if block_end == -1:
            continue

        block = content[block_start:block_end + 1]

        permissions = []
        for p_match in PERMISSION_ENTRY_PATTERN.finditer(block):
            object_name = (p_match.group("quoted_name") or p_match.group("plain_name") or "").strip()
            permissions.append({
                "object_type": p_match.group("object_type").lower(),
                "object_name": object_name,
                "rights": p_match.group("rights").upper(),
            })

        permission_sets.append({
            "id": set_id,
            "name": set_name,
            "normalized_name": _normalize_name(set_name),
            "permissions": permissions,
        })

    return permission_sets


def _find_role_set(permission_sets: list[dict], role_label: str) -> dict | None:
    for pset in permission_sets:
        if role_label in pset["normalized_name"]:
            return pset
    return None


def _refund_permissions(permission_set: dict) -> list[dict]:
    if not permission_set:
        return []

    results = []
    for entry in permission_set.get("permissions", []):
        object_name = entry.get("object_name", "")
        if any(keyword in object_name.lower() for keyword in REFUND_KEYWORDS):
            results.append(entry)
    return results


def run_security_permission_evaluator(project_dir: Path) -> dict:
    project_dir = Path(project_dir)
    al_files = list(project_dir.rglob("*.al"))

    if not al_files:
        return {"status": "skipped", "reason": "no .al files found"}

    permission_sets = []
    for al_file in al_files:
        try:
            content = al_file.read_text(encoding="utf-8")
        except Exception:
            continue

        file_permission_sets = _extract_permissionset_entries(content)
        for pset in file_permission_sets:
            pset["file"] = al_file.name
            permission_sets.append(pset)

    if not permission_sets:
        return {"status": "skipped", "reason": "no permissionset objects found"}

    front_desk = _find_role_set(permission_sets, REQUIRED_ROLES["front_desk"])
    finance = _find_role_set(permission_sets, REQUIRED_ROLES["finance"])
    admin = _find_role_set(permission_sets, REQUIRED_ROLES["admin"])

    missing_roles = []
    if not front_desk:
        missing_roles.append("Front Desk")
    if not finance:
        missing_roles.append("Finance")
    if not admin:
        missing_roles.append("Admin")

    front_refund = _refund_permissions(front_desk)
    finance_refund = _refund_permissions(finance)

    # HARD violations — these indicate a real security problem regardless of
    # implementation style.
    violations = []
    if missing_roles:
        violations.append(f"Missing required permission set(s): {', '.join(missing_roles)}")

    if front_desk and front_refund:
        violations.append("Front Desk permission set includes refund-related permissions")

    # SOFT/informational note — many valid AL designs enforce refund
    # authorization via a runtime permission check inside a security
    # management codeunit (e.g. HotelSecurityMgt.CheckRefundPermission())
    # rather than granting object-level AL permissions on something literally
    # named "Refund". That pattern is common and correct, so the absence of a
    # refund-named object grant on Finance is NOT treated as a hard failure —
    # it's surfaced as a note so a human (or the negative-case/authorization
    # check) can confirm enforcement exists elsewhere.
    notes = []
    if finance and not finance_refund:
        notes.append(
            "Finance permission set has no object explicitly named 'refund'. "
            "This is common when refund authorization is enforced at runtime "
            "via a security-management codeunit rather than a granular AL "
            "permission grant — not necessarily a defect on its own."
        )

    passed = not violations

    return {
        "status": "success",
        "passed": passed,
        "missing_roles": missing_roles,
        "violations": violations,
        "notes": notes,
        "roles": {
            "front_desk": {
                "name": front_desk.get("name") if front_desk else None,
                "file": front_desk.get("file") if front_desk else None,
                "refund_permissions": front_refund,
            },
            "finance": {
                "name": finance.get("name") if finance else None,
                "file": finance.get("file") if finance else None,
                "refund_permissions": finance_refund,
            },
            "admin": {
                "name": admin.get("name") if admin else None,
                "file": admin.get("file") if admin else None,
            },
        },
        "permission_set_count": len(permission_sets),
    }