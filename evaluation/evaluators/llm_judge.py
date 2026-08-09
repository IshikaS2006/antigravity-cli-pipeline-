import os
import subprocess
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

AGY_PATH = os.getenv("AGY_PATH")

# Windows CreateProcess has a hard ~32,767 character total command-line limit
# (executable + all args combined). Passing every generated file's full
# content as part of --print's argument can exceed this on larger, real
# multi-object projects (it never showed up on small single-table jobs).
# Leave generous headroom for the executable path, flags, and the prompt's
# own scaffolding text.
MAX_PROMPT_CHARS = 20000

# When a project's total code exceeds the budget, prioritize files that
# carry actual business logic — codeunits and tables — over UI-only files
# like pages, which matter less for judging requirement fulfillment.
PRIORITY_SUFFIXES = {".codeunit.al": 0, ".table.al": 0, ".al": 1, ".json": 2, ".md": 3}


def _file_priority(filename: str) -> int:
    lower = filename.lower()
    for suffix, priority in PRIORITY_SUFFIXES.items():
        if lower.endswith(suffix):
            return priority
    return 4


def _budget_code_contents(code_contents: dict, max_chars: int) -> dict:
    """Fits code_contents within max_chars total, keeping full content for
    higher-priority files first and truncating or dropping lower-priority
    ones as needed, rather than blindly cutting every file proportionally."""
    ordered_names = sorted(code_contents.keys(), key=_file_priority)

    budgeted = {}
    remaining = max_chars
    for name in ordered_names:
        content = code_contents[name]
        if remaining <= 0:
            budgeted[name] = "[omitted — prompt size budget exhausted]"
            continue
        if len(content) <= remaining:
            budgeted[name] = content
            remaining -= len(content)
        else:
            budgeted[name] = content[:remaining] + f"\n[... truncated, {len(content) - remaining} more characters]"
            remaining = 0

    return budgeted


def build_judge_prompt(requirements: str, code_contents: dict, static_analysis: dict) -> str:
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

    total_chars = sum(len(c) for c in code_contents.values())
    was_budgeted = total_chars > MAX_PROMPT_CHARS
    if was_budgeted:
        code_contents = _budget_code_contents(code_contents, MAX_PROMPT_CHARS)

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
    except FileNotFoundError as e:
        return {
            "status": "error",
            "error": str(e),
            "agy_path": repr(AGY_PATH),
        }
    except OSError as e:
        # Covers WinError 206 (filename/command-line too long) and similar
        # OS-level failures that aren't a missing-file problem.
        return {
            "status": "error",
            "error": f"OS error launching agy.exe: {e}",
            "prompt_chars": len(prompt),
        }

    raw_output = result.stdout.strip()

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
        "prompt_was_truncated": was_budgeted,
        **judgment,
    }