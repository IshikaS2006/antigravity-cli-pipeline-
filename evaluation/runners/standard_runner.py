from pathlib import Path
from evaluation.contracts.job_schema import validate_job_dir

# Extensions relevant to an AL/Business Central job. Add more here if your
# prompts start asking for other file types (e.g. .rdlc for reports).
AL_RELEVANT_EXTENSIONS = {".al", ".json", ".md"}


class StandardRunner:
    agent_name = "antigravity"

    def validate(self, job_dir: Path) -> dict:
        return validate_job_dir(job_dir)

    def get_generated_files(self, job_dir: Path) -> list[Path]:
        generated_dir = job_dir / "generated"
        if not generated_dir.exists():
            return []
        return [
            f for f in generated_dir.rglob("*")
            if f.is_file()
            and f.suffix.lower() in AL_RELEVANT_EXTENSIONS
            and "__pycache__" not in f.parts
        ]

    def get_reply(self, job_dir: Path) -> str:
        reply_path = job_dir / "reply.md"
        return reply_path.read_text(encoding="utf-8") if reply_path.exists() else ""