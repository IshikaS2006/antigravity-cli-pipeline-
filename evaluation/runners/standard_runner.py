from pathlib import Path
from evaluation.contracts.job_schema import validate_job_dir

class StandardRunner:
    agent_name = "antigravity"

    def validate(self, job_dir: Path) -> dict:
        return validate_job_dir(job_dir)

    def get_generated_files(self, job_dir: Path) -> list[Path]:
        generated_dir = job_dir / "generated"
        return list(generated_dir.rglob("*")) if generated_dir.exists() else []

    def get_reply(self, job_dir: Path) -> str:
        reply_path = job_dir / "reply.md"
        return reply_path.read_text(encoding="utf-8") if reply_path.exists() else ""