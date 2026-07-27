import json
from pathlib import Path
from datetime import datetime


def build_scorecard(job_dir: Path, metadata: dict, al_compile: dict,
                     static_analysis: dict = None, test_execution: dict = None,
                     sandbox_exec: dict = None, llm_judge: dict = None) -> dict:
    """
    Aggregates evaluator output into a single scorecard.
    al_compile is required (the core AL build check); the other four are
    optional so older callers passing only al_compile still work.
    """
    metrics = {"al_compile": al_compile}
    if static_analysis is not None:
        metrics["static_analysis"] = static_analysis
    if test_execution is not None:
        metrics["test_execution"] = test_execution
    if sandbox_exec is not None:
        metrics["sandbox_exec"] = sandbox_exec
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