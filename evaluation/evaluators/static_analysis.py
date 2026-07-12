import subprocess
import json
from pathlib import Path


def run_static_analysis(file_path: Path) -> dict:
    """
    Runs pylint on a single Python file and returns a structured result.
    Works on any .py file regardless of which agent generated it —
    no antigravity-specific assumptions here.
    """
    if not file_path.exists():
        return {
            "file": file_path.name,
            "status": "error",
            "error": "file not found",
        }

    if file_path.suffix != ".py":
        return {
            "file": file_path.name,
            "status": "skipped",
            "reason": f"unsupported file type: {file_path.suffix}",
        }

    try:
        result = subprocess.run(
            ["pylint", str(file_path), "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return {
            "file": file_path.name,
            "status": "error",
            "error": "pylint timed out",
        }
    except FileNotFoundError:
        return {
            "file": file_path.name,
            "status": "error",
            "error": "pylint not installed — run: pip install pylint",
        }

    # pylint exits non-zero even on successful runs (nonzero = issues found),
    # so don't treat returncode alone as failure. Only stdout parsing matters.
    try:
        issues = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        return {
            "file": file_path.name,
            "status": "error",
            "error": "could not parse pylint output",
            "raw_stderr": result.stderr[:500],
        }

    severity_counts = {"error": 0, "warning": 0, "convention": 0, "refactor": 0}
    for issue in issues:
        category = issue.get("type", "").lower()
        if category in severity_counts:
            severity_counts[category] += 1

    # Simple 0-10 score: start at 10, dock points per issue by severity weight
    score = 10.0
    score -= severity_counts["error"] * 1.5
    score -= severity_counts["warning"] * 0.5
    score -= severity_counts["convention"] * 0.2
    score -= severity_counts["refactor"] * 0.3
    score = max(0.0, round(score, 2))

    return {
        "file": file_path.name,
        "status": "success",
        "score": score,
        "issue_counts": severity_counts,
        "total_issues": len(issues),
        "issues": [
            {
                "line": i.get("line"),
                "type": i.get("type"),
                "message": i.get("message"),
                "symbol": i.get("symbol"),
            }
            for i in issues
        ],
    }


def run_static_analysis_on_job(generated_files: list[Path]) -> dict:
    """Runs static analysis across all generated files in a job and aggregates."""
    results = [run_static_analysis(f) for f in generated_files if f.is_file()]
    scored = [r for r in results if r.get("status") == "success"]
    avg_score = round(sum(r["score"] for r in scored) / len(scored), 2) if scored else None

    return {
        "average_score": avg_score,
        "files_analyzed": len(results),
        "per_file": results,
    }