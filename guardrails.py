# guardrails.py

BANNED_KEYWORDS = [
    "rm -rf", "del /f", "format c:", "shutdown", "reg delete",
    "os.system", "subprocess.call", "eval(", "exec(",
    "curl ", "wget ", "pip install", "npm install",
]

MAX_PROMPT_LENGTH = 4000


def validate_prompt(prompt: str) -> None:
    if not prompt.strip():
        raise ValueError("Requirements file is empty.")

    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(f"Prompt too long ({len(prompt)} chars). Max is {MAX_PROMPT_LENGTH}.")

    lowered = prompt.lower()
    for keyword in BANNED_KEYWORDS:
        if keyword in lowered:
            raise ValueError(f"Prompt contains a disallowed pattern: '{keyword}'")