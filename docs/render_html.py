import json
from pathlib import Path

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Scorecard — {job_id}</title>
<link rel="stylesheet" href="scorecard.css">
</head>
<body>
  <h1>{job_id}
    <span class="status-pill status-{gen_status_class}">{gen_status}</span>
  </h1>
  <div class="meta">Agent: {agent_name} · Duration: {duration}s · Evaluated: {evaluated_at}</div>

  {static_analysis_card}
  {sandbox_card}
  {test_card}
  {llm_judge_card}

</body>
</html>
"""

def _card(title, rows_html, empty_message=None):
    if empty_message:
        body = f'<div class="empty">{empty_message}</div>'
    else:
        body = rows_html
    return f'<div class="card"><h2>{title}</h2>{body}</div>'

def _row(label, value):
    return f'<div class="row"><span class="label">{label}</span><span>{value}</span></div>'

def render_scorecard_html(scorecard: dict) -> str:
    metrics = scorecard.get("metrics", {})

    # Static analysis (AL CodeCop/UICop/PerTenantExtensionCop-based)
    sa = metrics.get("static_analysis", {})
    if sa.get("status") != "success":
        static_card = _card(
            "Static Analysis", "",
            sa.get("error") or sa.get("reason") or "No analysis run for this job."
        )
    else:
        rows = _row("Score", sa.get("score"))
        rows += _row("Compiled clean", sa.get("compiled_clean"))
        rows += _row("Total issues", sa.get("total_issues"))
        counts = sa.get("issue_counts", {})
        rows += _row("Errors / Warnings / Info",
                      f"{counts.get('error', 0)} / {counts.get('warning', 0)} / {counts.get('info', 0)}")
        for issue in sa.get("issues", []):
            rows += _row(
                f"{issue.get('file')}:{issue.get('line')} [{issue.get('code')}]",
                issue.get("message", "")
            )
        static_card = _card("Static Analysis", rows)

    # Sandbox execution (Python-only right now; on hold for AL)
    sb = metrics.get("sandbox_exec", {})
    if sb.get("files_tested", 0) == 0:
        sandbox_card = _card("Sandbox Execution", "", "No files tested (not applicable to AL yet).")
    else:
        rows = _row("Files tested", sb.get("files_tested"))
        rows += _row("Successful runs", sb.get("successful_runs"))
        sandbox_card = _card("Sandbox Execution", rows)

    # Test results (static AL test-codeunit check)
    tr = metrics.get("test_execution", {})
    if tr.get("status") == "no_tests_found":
        test_card = _card("Test Results", "", tr.get("message", "No tests found."))
    else:
        rows = _row("Status", tr.get("status"))
        rows += _row("Files tested", tr.get("files_tested"))
        rows += _row("Total test methods", tr.get("total_test_methods"))
        rows += _row("Total assertions", tr.get("total_assertions"))
        hollow = tr.get("hollow_test_files", [])
        if hollow:
            rows += _row("Hollow tests (no assertions)", ", ".join(hollow))
        test_card = _card("Test Results", rows)

    # LLM judge
    lj = metrics.get("llm_judge", {})
    if lj.get("status") == "skipped":
        llm_card = _card("LLM Judge", "", lj.get("reason", "Skipped."))
    else:
        rows = "".join(_row(k, v) for k, v in lj.items())
        llm_card = _card("LLM Judge", rows)

    gen_status = scorecard.get("generation_status", "unknown")

    return TEMPLATE.format(
        job_id=scorecard.get("job_id", "unknown"),
        agent_name=scorecard.get("agent_name", "unknown"),
        duration=scorecard.get("generation_duration_seconds", "?"),
        evaluated_at=scorecard.get("evaluated_at", "?"),
        gen_status=gen_status,
        gen_status_class=gen_status,
        static_analysis_card=static_card,
        sandbox_card=sandbox_card,
        test_card=test_card,
        llm_judge_card=llm_card,
    )


CSS_FILE = Path(__file__).parent / "scorecard.css"

def save_scorecard_html(job_dir: Path, scorecard: dict) -> Path:
    html = render_scorecard_html(scorecard)

    html_path = job_dir / "scorecard.html"
    html_path.write_text(html, encoding="utf-8")

    css_path = job_dir / "scorecard.css"
    css_path.write_text(CSS_FILE.read_text(encoding="utf-8"), encoding="utf-8")

    return html_path