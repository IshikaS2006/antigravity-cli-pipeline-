"""
AL-focused static analysis. Instead of pylint (which doesn't understand AL),
this reuses the AL compiler's own built-in analyzers: CodeCop, UICop, and
PerTenantExtensionCop. These ship inside the same VS Code AL extension that
provides alc.exe, so no extra tools/installs are needed.

Assumes al_pipeline.py (your existing compile module) is importable and that
symbols have already been downloaded for this project via download_symbols().
"""

import re
from pathlib import Path

from evaluation.evaluators.al_pipeline import (
    resolve_alc_path,
    resolve_analyzer_dlls,
    compile_al_project,
    default_symbols_dir,
)

# Matches AL diagnostic lines, e.g.:
#   app.json(13,3): warning AL0667: 'capabilities' is being deprecated...
#   src\CustomerExt.TableExt.al(5,10): warning AA0072: The name...
DIAGNOSTIC_PATTERN = re.compile(
    r'(?P<file>[^\r\n]+?)\((?P<line>\d+),(?P<col>\d+)\):\s*'
    r'(?P<severity>error|warning|info)\s+(?P<code>[A-Za-z]+\d+):\s*(?P<message>.+)'
)

# Code prefixes tell you which analyzer raised it
ANALYZER_PREFIX = {
    "AA": "CodeCop",
    "AW": "UICop",
    "PTE": "PerTenantExtensionCop",
    "AS": "AppSourceCop",
    "AL": "Compiler",  # base compiler diagnostics, not an analyzer rule
}


def parse_diagnostics(compiler_output: str) -> list[dict]:
    diagnostics = []
    for match in DIAGNOSTIC_PATTERN.finditer(compiler_output):
        code = match.group("code")
        prefix = re.match(r'[A-Za-z]+', code).group()
        diagnostics.append({
            "file": Path(match.group("file")).name,
            "line": int(match.group("line")),
            "severity": match.group("severity").lower(),
            "code": code,
            "source": ANALYZER_PREFIX.get(prefix, "Unknown"),
            "message": match.group("message").strip(),
        })
    return diagnostics


def run_static_analysis_on_job(project_dir: Path, symbols_dir: Path = None,
                                alc_path: Path = None) -> dict:
    """
    Re-compiles the AL project with CodeCop/UICop/PerTenantExtensionCop enabled
    and scores it based on the diagnostics they raise. Reuses symbols already
    downloaded by al_compile, so this should run after that step succeeds.
    """
    project_dir = Path(project_dir)
    if symbols_dir is None:
        symbols_dir = default_symbols_dir(project_dir)
    if alc_path is None:
        alc_path = resolve_alc_path()

    analyzer_dlls = resolve_analyzer_dlls(alc_path)
    if not analyzer_dlls:
        return {
            "status": "error",
            "error": "Could not locate analyzer DLLs (CodeCop/UICop/PerTenantExtensionCop) "
                     "alongside alc.exe — check your AL extension install.",
        }

    result = compile_al_project(
        project_dir, symbols_dir, alc_path,
        out_name="analysis_pass.app",  # separate output so it doesn't clobber al_compile's .app
        analyzer_paths=analyzer_dlls,
    )

    combined_output = result["stdout"] + "\n" + result["stderr"]
    diagnostics = parse_diagnostics(combined_output)

    # Only count analyzer-raised issues for scoring, not base compiler AL#### diagnostics
    # (those are already captured by your al_compile success/fail check).
    analyzer_diagnostics = [d for d in diagnostics if d["source"] != "Compiler"]

    severity_counts = {"error": 0, "warning": 0, "info": 0}
    for d in analyzer_diagnostics:
        if d["severity"] in severity_counts:
            severity_counts[d["severity"]] += 1

    score = 10.0
    score -= severity_counts["error"] * 1.5
    score -= severity_counts["warning"] * 0.5
    score -= severity_counts["info"] * 0.1
    score = max(0.0, round(score, 2))

    return {
        "status": "success",
        "compiled_clean": result["success"],
        "analyzers_used": [Path(d).stem for d in analyzer_dlls],
        "score": score,
        "issue_counts": severity_counts,
        "total_issues": len(analyzer_diagnostics),
        "issues": analyzer_diagnostics,
    }