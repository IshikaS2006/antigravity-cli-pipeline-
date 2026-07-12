from pathlib import Path
import json

REQUIRED_FILES = {"GEMINI.md", "requirements.txt", "metadata.json"}

class JobContractError(Exception):
    pass

def validate_job_dir(job_dir: Path) -> dict:
    """Validates a job folder matches the contract. Returns parsed metadata."""
    if not job_dir.is_dir():
        raise JobContractError(f"Not a directory: {job_dir}")

    missing = [f for f in REQUIRED_FILES if not (job_dir / f).exists()]
    if missing:
        raise JobContractError(f"{job_dir.name} missing required files: {missing}")

    metadata_path = job_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    required_keys = {"job_id", "agent_name", "status", "exit_code"}
    missing_keys = required_keys - metadata.keys()
    if missing_keys:
        raise JobContractError(f"{job_dir.name} metadata.json missing keys: {missing_keys}")

    generated_dir = job_dir / "generated"
    if not generated_dir.exists():
        metadata["_warning"] = "no generated/ folder found"

    return metadata