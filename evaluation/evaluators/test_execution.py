import subprocess
import sys
import re
from pathlib import Path


def find_test_files(generated_files: list[Path]) -> list[Path]:
    """Heuristic: files matching test_*.py or *_test.py are treated as test files."""
    return [
        f for f in generated_files
        if f.is_file() and f.suffix == ".py"
        and (f.name.startswith("test_") or f.name.endswith("_test.py"))
    ]


def run_tests(test_file: Path, timeout: int = 30) -> dict:
    """
    Runs a single test file using pytest and parses pass/fail counts.
    Falls back gracefully if pytest isn't installed or the file isn't
    actually a valid test file.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=test_file.parent,  # so it can import sibling modules like calculator.py
        )
    except subprocess.TimeoutExpired:
        return {
            "file": test_file.name,
            "status": "timeout",
            "error": f"tests exceeded {timeout}s",
        }
    except FileNotFoundError:
        return {
            "file": test_file.name,
            "status": "error",
            "error": "pytest not installed — run: pip install pytest",
        }

    output = result.stdout + result.stderr

    # Parse pytest's summary line, e.g. "3 passed, 1 failed in 0.12s"
    passed = failed = errors = 0


    passed_match = re.search(r"(\d+) passed", output)
    failed_match = re.search(r"(\d+) failed", output)
    error_match = re.search(r"(\d+) error", output)

    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    errors = int(error_match.group(1)) if error_match else 0

    return {
        "file": test_file.name,
        "status": "success" if result.returncode == 0 else "failures",
        "exit_code": result.returncode,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "output_tail": output[-800:],
    }


def run_test_evaluation_on_job(generated_files: list[Path]) -> dict:
    """Finds and runs any test files in the generated output."""
    test_files = find_test_files(generated_files)

    if not test_files:
        return {
            "status": "no_tests_found",
            "message": "Agent did not generate any test files for this job.",
            "files_tested": 0,
        }

    results = [run_tests(f) for f in test_files]
    total_passed = sum(r.get("passed", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)

    return {
        "status": "evaluated",
        "files_tested": len(results),
        "total_passed": total_passed,
        "total_failed": total_failed,
        "per_file": results,
    }