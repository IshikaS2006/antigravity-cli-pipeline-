import os
import subprocess
import json
import re
from pathlib import Path

AGY_PATH = os.getenv("AGY_PATH")

def build_judge_prompt(requirements: str    , code_contents: dict, static_analysis: dict) -> str:
    """Builds the judging prompt, including other evaluators' results as context."""
    code_section = "\n\n".join(
        f"--- {fname} ---\n{content}" for fname, content in code_contents.items()
    )

    return f"""You are a code reviewer. Judge the following generated code against the original requirement.

ORIGINAL REQUIREMENT:
{requirements}

GENERATED CODE:
{code_section}

STATIC ANALYSIS RESULT (for context, do not re-derive):
{json.dumps(static_analysis, indent=2)[:1000]}

Respond with ONLY a JSON object, no other text, in this exact format:
{{
  "requirement_fulfilled": true or false,
  "correctness_score": 0-10,
  "reasoning_quality_score": 0-10,
  "summary": "1-2 sentence assessment",
  "concerns": ["list", "of", "specific issues if any"]
}}"""


def run_llm_judge(job_dir: Path, generated_files: list[Path], static_analysis: dict, timeout: int = 120) -> dict:
    requirements_file = job_dir / "requirements.txt"
    requirements_text = requirements_file.read_text(encoding="utf-8") if requirements_file.exists() else ""

    code_contents = {}
    for f in generated_files:
        if f.is_file() and f.suffix in {".py", ".js", ".ts", ".java", ".al", ".json", ".md"}:
            try:
                code_contents[f.name] = f.read_text(encoding="utf-8")
            except Exception:
                continue

    if not code_contents:
        return {"status": "skipped", "reason": "no readable code files found"}

    prompt = build_judge_prompt(requirements_text, code_contents, static_analysis)

    try:
        result = subprocess.run(
            [AGY_PATH, "--print", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"judge call exceeded {timeout}s"}
    except FileNotFoundError:
        return {"status": "error", "error": "agy.exe not found — check AGY_PATH"}

    raw_output = result.stdout.strip()

    # Judge might wrap JSON in markdown fences or add stray text — extract the JSON block
    json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)
    if not json_match:
        return {
            "status": "error",
            "error": "could not find JSON in judge response",
            "raw_output": raw_output[:1000],
        }

    try:
        judgment = json.loads(json_match.group())
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error": "judge response was not valid JSON",
            "raw_output": raw_output[:1000],
        }

    return {
        "status": "success",
        **judgment,
    }