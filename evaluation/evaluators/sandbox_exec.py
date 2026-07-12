import subprocess
import sys
from pathlib import Path


def run_sandboxed(file_path: Path, timeout: int = 15) -> dict:
    """
    Attempts to execute a generated Python file in isolation.
    Not testing correctness — just: does it import/run without crashing?
    Agent-agnostic: works on any .py file regardless of which agent wrote it.
    """
    if not file_path.exists():
        return {"file": file_path.name, "status": "error", "error": "file not found"}

    if file_path.suffix != ".py":
        return {
            "file": file_path.name,
            "status": "skipped",
            "reason": f"unsupported file type: {file_path.suffix}",
        }

    try:
        result = subprocess.run(
            [sys.executable, str(file_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,  # prevent hanging on input() calls
        )
    except subprocess.TimeoutExpired:
        return {
            "file": file_path.name,
            "status": "timeout",
            "error": f"execution exceeded {timeout}s (possible infinite loop or blocking input())",
        }
    except Exception as e:
        return {
            "file": file_path.name,
            "status": "error",
            "error": f"failed to launch: {e}",
        }

    return {
        "file": file_path.name,
        "status": "success" if result.returncode == 0 else "crashed",
        "exit_code": result.returncode,
        "stdout_tail": result.stdout[-500:],  # last 500 chars, avoid huge dumps
        "stderr_tail": result.stderr[-500:],
    }


def run_sandbox_on_job(generated_files: list[Path]) -> dict:
    """Runs sandboxed execution across all generated files in a job."""
    py_files = [f for f in generated_files if f.is_file() and f.suffix == ".py"]
    results = [run_sandboxed(f) for f in py_files]

    success_count = sum(1 for r in results if r.get("status") == "success")

    return {
        "files_tested": len(results),
        "successful_runs": success_count,
        "per_file": results,
    }