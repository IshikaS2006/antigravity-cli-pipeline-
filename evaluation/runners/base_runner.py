from abc import ABC, abstractmethod
from pathlib import Path

class BaseRunner(ABC):
    """Every agent runner (antigravity, devin, claude-code, etc.) implements this."""

    agent_name: str

    @abstractmethod
    def get_generated_files(self, job_dir: Path) -> list[Path]:
        """Return list of generated code file paths for this job."""
        pass

    @abstractmethod
    def get_reply(self, job_dir: Path) -> str:
        """Return the agent's textual reply/summary, if any."""
        pass