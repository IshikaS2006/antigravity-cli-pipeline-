"""
Negative-case evaluator for AL hotel scenario outputs.

Checks for explicit rejection/guard logic for the four required negative cases:
  1. Overbooking attempts
  2. Failed payment/deposit capture failures
  3. Duplicate invoice generation
  4. Unauthorized refund attempts

This evaluator is heuristic but deterministic: it scans generated AL files and
requires concrete guard/error patterns instead of happy-path-only signals.

DESIGN NOTE: earlier versions of these checks hardcoded one exact expected
implementation (a specific procedure name, a specific compound boolean, a
specific built-in AL API). Real generated code often implements the same
correct behavior a different, equally valid way — so checks below look for
the general pattern (a relevant concept near an Error() rejection) rather
than one literal phrasing.
"""

import re
from pathlib import Path


def _normalize(text: str) -> str:
    return text.lower()


def _find_snippet(text: str, pattern: re.Pattern, radius: int = 160) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return text[start:end].strip().replace("\r", "")


def _scan_overbooking(full_text: str) -> tuple[bool, list[str]]:
    evidence = []

    has_conflict_concept = bool(re.search(r"overbook|overlap|already\s+reserved|occupied", full_text, re.IGNORECASE))

    # Generalized: the conflict concept (occupied/overbook/overlap) appearing
    # near an Error() call, regardless of exact surrounding syntax — covers
    # both inline SetFilter-based checks and custom helper procedures like
    # CheckOverbooking(...) that raise Error() internally.
    guard_pattern = re.compile(
        r"(overbook\w*|overlap\w*|occupied)[\s\S]{0,150}?error\(",
        re.IGNORECASE,
    )
    has_guard_near_error = bool(guard_pattern.search(full_text))

    if has_conflict_concept:
        snippet = _find_snippet(full_text, re.compile(r"overbook|overlap|already\s+reserved|occupied", re.IGNORECASE))
        if snippet:
            evidence.append(f"Conflict concept found: {snippet}")
    if has_guard_near_error:
        snippet = _find_snippet(full_text, guard_pattern)
        if snippet:
            evidence.append(f"Conflict rejection via Error() found near guard condition: {snippet}")

    passed = has_conflict_concept and has_guard_near_error
    return passed, evidence


def _scan_failed_payment(full_text: str) -> tuple[bool, list[str]]:
    evidence = []

    has_failure_branch = bool(re.search(r'if\s+not\s+\w*payment\w*\s+then', full_text, re.IGNORECASE))
    # after — generalize the field name the same way the other checks were generalized
    has_deposit_not_captured = bool(re.search(
        r'"Deposit\s+(Captured|Paid|Success(ful)?)"\s*:=\s*false',
        full_text, re.IGNORECASE
    ))
    has_error = bool(re.search(r'if\s+not\s+\w*payment\w*\s+then[\s\S]{0,350}?Error\(', full_text, re.IGNORECASE))

    if has_failure_branch:
        snippet = _find_snippet(full_text, re.compile(r'if\s+not\s+\w*payment\w*\s+then', re.IGNORECASE))
        if snippet:
            evidence.append(f"Payment failure branch found: {snippet}")
    if has_deposit_not_captured:
        snippet = _find_snippet(full_text, re.compile(r'"Deposit Captured"\s*:=\s*false', re.IGNORECASE))
        if snippet:
            evidence.append(f"Deposit capture rollback found: {snippet}")
    if has_error:
        snippet = _find_snippet(full_text, re.compile(r'if\s+not\s+\w*payment\w*\s+then[\s\S]{0,350}?Error\(', re.IGNORECASE))
        if snippet:
            evidence.append(f"Payment failure rejection via Error() found: {snippet}")

    passed = has_failure_branch and has_deposit_not_captured and has_error
    return passed, evidence


def _scan_duplicate_invoice(full_text: str) -> tuple[bool, list[str]]:
    evidence = []

    has_duplicate_guard = bool(
        re.search(r'invoiced', full_text, re.IGNORECASE)
        or re.search(r'duplicate\s+invoice', full_text, re.IGNORECASE)
    )

    # Generalized: any "invoiced" flag check within a short distance of an
    # Error() call — covers both "if reservation.invoiced then error(...)"
    # and more compound boolean variants, without requiring exact syntax.
    has_error = bool(re.search(r'invoiced[\s\S]{0,150}?error\(', full_text, re.IGNORECASE))

    if has_duplicate_guard:
        snippet = _find_snippet(full_text, re.compile(r'invoiced|duplicate\s+invoice', re.IGNORECASE))
        if snippet:
            evidence.append(f"Duplicate invoice guard found: {snippet}")
    if has_error:
        snippet = _find_snippet(full_text, re.compile(r'invoiced[\s\S]{0,150}?error\(', re.IGNORECASE))
        if snippet:
            evidence.append(f"Duplicate invoice rejection via Error() found: {snippet}")

    passed = has_duplicate_guard and has_error
    return passed, evidence


def _extract_procedure_body(full_text: str, procedure_name: str) -> str | None:
    """Isolates a named procedure's body (from its signature to the next
    top-level procedure declaration), so checks can be scoped to the actual
    production logic instead of matching unrelated text anywhere in the file
    (e.g. a same-named test procedure, or an unrelated Error() elsewhere)."""
    pattern = re.compile(
        rf'procedure\s+{re.escape(procedure_name)}\s*\([^)]*\)[\s\S]*?'
        rf'(?=\n\s{{0,4}}(?:local\s+)?procedure\s|\Z)',
        re.IGNORECASE,
    )
    match = pattern.search(full_text)
    return match.group() if match else None


def _scan_unauthorized_refund(full_text: str) -> tuple[bool, list[str]]:
    evidence = []

    has_refund_flow = bool(re.search(r'procedure\s+ProcessRefund', full_text, re.IGNORECASE))
    if has_refund_flow:
        snippet = _find_snippet(full_text, re.compile(r'procedure\s+ProcessRefund', re.IGNORECASE))
        if snippet:
            evidence.append(f"Refund flow found: {snippet}")

    refund_body = _extract_procedure_body(full_text, "ProcessRefund")
    if not refund_body:
        return False, evidence

    # Pattern A: inline role/enum comparison against a restricted role,
    # e.g. "if (UserRole = Enum::...::FrontDesk) ... then Error(...)" —
    # covers direct role-check implementations.
    inline_role_check = re.compile(
        r'enum::"[^"]*role"::\w+[\s\S]{0,150}?error\(',
        re.IGNORECASE,
    )
    has_inline_role_check = bool(inline_role_check.search(refund_body))
    if has_inline_role_check:
        snippet = _find_snippet(refund_body, inline_role_check, radius=120)
        if snippet:
            evidence.append(f"Inline role check with rejection found in ProcessRefund: {snippet}")

    # Pattern B: delegated permission-check call, e.g.
    # "HotelSecurityMgt.CheckRefundPermission()" — covers implementations
    # that push authorization into a separate security-management codeunit.
    # We then confirm that named procedure actually rejects internally,
    # rather than just trusting the call exists.
    delegated_call = re.search(
        r'\.\s*((?:Check|Verify|Validate)\w*(?:Permission|Refund|Finance|Access)\w*)\s*\(',
        refund_body, re.IGNORECASE,
    )
    has_delegated_enforcement = False
    if delegated_call:
        called_name = delegated_call.group(1)
        evidence.append(f"Delegated permission-check call found in ProcessRefund: {delegated_call.group()}")
        called_proc_body = _extract_procedure_body(full_text, called_name)
        if called_proc_body and re.search(r'error\(', called_proc_body, re.IGNORECASE):
            has_delegated_enforcement = True
            snippet = _find_snippet(called_proc_body, re.compile(r'error\(', re.IGNORECASE))
            if snippet:
                evidence.append(f"Rejection confirmed inside {called_name}: {snippet}")

    passed = has_refund_flow and (has_inline_role_check or has_delegated_enforcement)
    return passed, evidence


def run_negative_case_evaluator(project_dir: Path) -> dict:
    project_dir = Path(project_dir)
    all_al_files = list(project_dir.rglob("*.al"))

    if not all_al_files:
        return {"status": "skipped", "reason": "no .al files found"}

    # Exclude test codeunits from the evidence pool. A test file asserting
    # expected behavior ("if not X then error('test failed...')") is not the
    # same as production code actually enforcing that behavior — evidence
    # must come from the real implementation, not the test that checks it.
    al_files = [
        f for f in all_al_files
        if "test" not in f.name.lower()
    ]

    if not al_files:
        return {"status": "skipped", "reason": "no non-test .al files found"}

    collected_parts = []
    files_scanned = []
    for al_file in al_files:
        try:
            content = al_file.read_text(encoding="utf-8")
        except Exception:
            continue
        files_scanned.append(al_file.name)
        collected_parts.append(f"\n\n--- {al_file.name} ---\n{content}")

    if not collected_parts:
        return {"status": "skipped", "reason": "no readable .al files found"}

    full_text = _normalize("".join(collected_parts))

    overbooking_passed, overbooking_evidence = _scan_overbooking(full_text)
    payment_passed, payment_evidence = _scan_failed_payment(full_text)
    duplicate_invoice_passed, duplicate_invoice_evidence = _scan_duplicate_invoice(full_text)
    refund_auth_passed, refund_auth_evidence = _scan_unauthorized_refund(full_text)

    checks = {
        "overbooking_rejected": {
            "passed": overbooking_passed,
            "evidence": overbooking_evidence,
        },
        "failed_payment_not_marked_captured": {
            "passed": payment_passed,
            "evidence": payment_evidence,
        },
        "duplicate_invoice_rejected": {
            "passed": duplicate_invoice_passed,
            "evidence": duplicate_invoice_evidence,
        },
        "unauthorized_refund_rejected": {
            "passed": refund_auth_passed,
            "evidence": refund_auth_evidence,
        },
    }

    failures = [name for name, result in checks.items() if not result["passed"]]

    return {
        "status": "success",
        "passed": len(failures) == 0,
        "checks": checks,
        "failed_checks": failures,
        "files_scanned": files_scanned,
    }