import json
from pathlib import Path
from datetime import datetime


def build_scorecard(job_dir: Path, metadata: dict, static_analysis: dict, sandbox_execution: dict, test_results: dict, llm_judge: dict) -> dict:
    """
    Aggregates all evaluator outputs into a single scorecard.
    Additional evaluators (sandbox_exec, test_results, llm_judge) get added
    as new keys here later — this function's shape is deliberately open-ended.
    """
    scorecard = {
        "job_id": metadata.get("job_id"),
        "agent_name": metadata.get("agent_name"),
        "variant_id": metadata.get("variant_id"),
        "generation_status": metadata.get("status"),
        "generation_duration_seconds": metadata.get("duration_seconds"),
        "evaluated_at": datetime.now().isoformat(),
        "metrics": {
            "static_analysis": static_analysis,
            "sandbox_execution": sandbox_execution,   
            "test_results": test_results,        
            "llm_judge": llm_judge,            
        },
    }
    return scorecard


def save_scorecard(job_dir: Path, scorecard: dict) -> Path:
    out_path = job_dir / "scorecard.json"
    out_path.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    return out_path