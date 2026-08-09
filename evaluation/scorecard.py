import json
from pathlib import Path
from datetime import datetime


def build_scorecard(job_dir: Path, metadata: dict, al_compile: dict,
                     static_analysis: dict = None, object_contract: dict = None,
                     security_permissions: dict = None, negative_cases: dict = None,
                     llm_judge: dict = None) -> dict:
    """
    Aggregates evaluator output into a single scorecard.
    al_compile is required (the core AL build check); the other checks are
    optional so older callers passing only al_compile still work.
    """
    metrics = {"al_compile": al_compile}
    if static_analysis is not None:
        metrics["static_analysis"] = static_analysis
    if object_contract is not None:
        metrics["object_contract"] = object_contract
    if security_permissions is not None:
        metrics["security_permissions"] = security_permissions
    if negative_cases is not None:
        metrics["negative_cases"] = negative_cases
    if llm_judge is not None:
        metrics["llm_judge"] = llm_judge

    scorecard = {
        "job_id": metadata.get("job_id"),
        "agent_name": metadata.get("agent_name"),
        "variant_id": metadata.get("variant_id"),
        "generation_status": metadata.get("status"),
        "generation_duration_seconds": metadata.get("duration_seconds"),
        "evaluated_at": datetime.now().isoformat(),
        "metrics": metrics,
    }
    return scorecard


def save_scorecard(job_dir: Path, scorecard: dict) -> Path:
    out_path = job_dir / "scorecard.json"
    out_path.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    return out_path