import re
from pathlib import Path

TEST_CODEUNIT_PATTERN = re.compile(
    r'codeunit\s+(\d+)\s+"?([^"\n{]+)"?\s*\{([^}]*Subtype\s*=\s*Test[^}]*)\}',
    re.IGNORECASE | re.DOTALL,
)
TEST_METHOD_PATTERN = re.compile(r'\[Test\]\s*\r?\n\s*procedure\s+(\w+)', re.IGNORECASE)
ASSERT_CALL_PATTERN = re.compile(r'\bAssert\.\w+\s*\(', re.IGNORECASE)


def find_al_test_files(generated_files: list[Path]) -> list[Path]:
    """Any .al file whose content declares a Subtype = Test codeunit."""
    test_files = []
    for f in generated_files:
        if f.is_file() and f.suffix.lower() == ".al":
            try:
                content = f.read_text(encoding="utf-8")
            except Exception:
                continue
            if re.search(r'subtype\s*=\s*test', content, re.IGNORECASE):
                test_files.append(f)
    return test_files


def analyze_al_test_file(file_path: Path) -> dict:
    """
    Static check of an AL test codeunit — no BC server needed.
    Confirms test structure exists and that tests actually assert something,
    rather than just running without checking anything.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"file": file_path.name, "status": "error", "error": str(e)}

    codeunit_match = TEST_CODEUNIT_PATTERN.search(content)
    test_methods = TEST_METHOD_PATTERN.findall(content)
    assertion_calls = ASSERT_CALL_PATTERN.findall(content)

    return {
        "file": file_path.name,
        "status": "success",
        "codeunit_id": codeunit_match.group(1) if codeunit_match else None,
        "codeunit_name": codeunit_match.group(2).strip() if codeunit_match else None,
        "test_methods_found": len(test_methods),
        "test_method_names": test_methods,
        "assertions_found": len(assertion_calls),
        "has_assertions": len(assertion_calls) > 0,
    }


def run_test_evaluation_on_job(generated_files: list[Path]) -> dict:
    """
    Lighter-weight AL test check: verifies the agent wrote real test
    codeunits with actual assertions, without executing them (no BC
    container available). Flags cases where tests exist structurally
    but assert nothing, since that's a common shortcut agents take.
    """
    test_files = find_al_test_files(generated_files)

    if not test_files:
        return {
            "status": "no_tests_found",
            "message": "Agent did not generate any AL test codeunits (Subtype = Test) for this job.",
            "files_tested": 0,
        }

    results = [analyze_al_test_file(f) for f in test_files]
    scored = [r for r in results if r.get("status") == "success"]

    total_methods = sum(r.get("test_methods_found", 0) for r in scored)
    total_assertions = sum(r.get("assertions_found", 0) for r in scored)
    hollow_tests = [r["file"] for r in scored if r.get("test_methods_found", 0) > 0 and not r.get("has_assertions")]

    return {
        "status": "evaluated",
        "files_tested": len(results),
        "total_test_methods": total_methods,
        "total_assertions": total_assertions,
        "hollow_test_files": hollow_tests,  # tests found but no Assert calls — warning sign
        "per_file": results,
    }