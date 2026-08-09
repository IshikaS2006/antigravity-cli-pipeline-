import json
from html import escape
from pathlib import Path


STYLE = """
:root {
    --bg: #f6f7fb;
    --panel: #ffffff;
    --panel-soft: #f9fafc;
    --border: #dbe2ea;
    --text: #17212b;
    --muted: #5f6b7a;
    --shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    --success: #1f7a3d;
    --warning: #a16207;
    --danger: #b42318;
    --info: #2563eb;
    --neutral: #475467;
    --chip-bg: #edf2f7;
}

* { box-sizing: border-box; }

html, body { margin: 0; padding: 0; }

body {
    background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 28%),
        radial-gradient(circle at top right, rgba(31, 122, 61, 0.05), transparent 24%),
        var(--bg);
    color: var(--text);
    font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.5;
}

.container {
    max-width: 1240px;
    margin: 0 auto;
    padding: 28px 20px 56px;
}

.hero {
    background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(255,255,255,0.88));
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 24px 24px 20px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
}

.hero-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    flex-wrap: wrap;
}

.title {
    margin: 0;
    font-size: clamp(24px, 3vw, 34px);
    line-height: 1.15;
    letter-spacing: -0.03em;
}

.subtitle {
    margin-top: 8px;
    color: var(--muted);
    font-size: 14px;
}

.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
    border: 1px solid transparent;
    white-space: nowrap;
}

.status-success { background: rgba(31, 122, 61, 0.1); color: var(--success); border-color: rgba(31, 122, 61, 0.18); }
.status-warning { background: rgba(161, 98, 7, 0.1); color: var(--warning); border-color: rgba(161, 98, 7, 0.18); }
.status-danger { background: rgba(180, 35, 24, 0.1); color: var(--danger); border-color: rgba(180, 35, 24, 0.18); }
.status-info { background: rgba(37, 99, 235, 0.1); color: var(--info); border-color: rgba(37, 99, 235, 0.18); }
.status-neutral { background: rgba(71, 84, 103, 0.08); color: var(--neutral); border-color: rgba(71, 84, 103, 0.16); }

.meta-grid,
.summary-grid,
.metric-grid,
.card-grid {
    display: grid;
    gap: 14px;
}

.meta-grid {
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    margin-top: 18px;
}

.metric-grid,
.summary-grid,
.card-grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.meta-item,
.summary-card,
.metric-card,
.panel,
.error-panel,
.raw-panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: var(--shadow);
}

.meta-item,
.summary-card,
.metric-card {
    padding: 14px 16px;
}

.eyebrow {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}

.meta-value,
.summary-value {
    font-size: 16px;
    font-weight: 700;
    word-break: break-word;
}

.section {
    margin-top: 18px;
}

.section h2 {
    margin: 0 0 12px;
    font-size: 18px;
    letter-spacing: -0.02em;
}

.section-note {
    color: var(--muted);
    font-size: 13px;
    margin: -6px 0 14px;
}

.panel,
.error-panel,
.raw-panel {
    padding: 18px;
}

.panel + .panel,
.panel + .error-panel,
.error-panel + .panel,
.error-panel + .error-panel {
    margin-top: 14px;
}

.kv-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 10px;
}

.kv {
    padding: 12px 14px;
    background: var(--panel-soft);
    border: 1px solid #e8edf3;
    border-radius: 14px;
}

.kv .key {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.kv .value {
    margin-top: 6px;
    font-size: 15px;
    font-weight: 600;
    word-break: break-word;
}

.table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: #fff;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 620px;
}

th, td {
    text-align: left;
    padding: 12px 14px;
    border-bottom: 1px solid #edf2f7;
    vertical-align: top;
}

th {
    background: #f8fafc;
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

tbody tr:hover {
    background: #fcfdff;
}

.chip,
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid transparent;
    white-space: nowrap;
}

.badge-success { background: rgba(31, 122, 61, 0.1); color: var(--success); border-color: rgba(31, 122, 61, 0.18); }
.badge-warning { background: rgba(161, 98, 7, 0.1); color: var(--warning); border-color: rgba(161, 98, 7, 0.18); }
.badge-danger { background: rgba(180, 35, 24, 0.1); color: var(--danger); border-color: rgba(180, 35, 24, 0.18); }
.badge-info { background: rgba(37, 99, 235, 0.1); color: var(--info); border-color: rgba(37, 99, 235, 0.18); }
.badge-neutral { background: rgba(71, 84, 103, 0.08); color: var(--neutral); border-color: rgba(71, 84, 103, 0.16); }

.section-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
}

.muted {
    color: var(--muted);
}

.empty {
    color: var(--muted);
    font-size: 13px;
    font-style: italic;
}

.error-panel {
    border-left: 5px solid var(--danger);
    background: linear-gradient(180deg, rgba(180, 35, 24, 0.04), rgba(255, 255, 255, 1));
}

.error-title {
    margin: 0 0 8px;
    font-size: 16px;
}

.error-text {
    margin: 0;
    color: var(--text);
}

details {
    margin-top: 12px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: #fff;
    overflow: hidden;
}

details > summary {
    cursor: pointer;
    list-style: none;
    padding: 12px 14px;
    background: #fbfcfe;
    color: var(--text);
    font-weight: 700;
}

details > summary::-webkit-details-marker {
    display: none;
}

.details-body {
    padding: 14px;
}

.evidence-list,
.problem-list {
    margin: 0;
    padding-left: 18px;
}

.evidence-list li + li,
.problem-list li + li {
    margin-top: 10px;
}

pre {
    margin: 0;
    padding: 12px 14px;
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 12px;
    overflow-x: auto;
    font-size: 12px;
    line-height: 1.55;
}

code {
    font-family: Consolas, "SFMono-Regular", Menlo, Monaco, "Liberation Mono", monospace;
}

.raw-panel pre {
    max-height: 520px;
}

.metric-card .metric-title {
    margin: 0 0 8px;
    font-size: 14px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.metric-card .metric-main {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
}

.metric-card .metric-value {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.03em;
}

.metric-card .metric-sub {
    margin-top: 8px;
    color: var(--muted);
    font-size: 13px;
}

.roles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
}

.role-card {
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--panel-soft);
}

.role-card h3 {
    margin: 0 0 8px;
    font-size: 15px;
}

.role-lines {
    display: grid;
    gap: 6px;
    font-size: 13px;
}

.role-lines span {
    color: var(--muted);
}

@media (max-width: 720px) {
    .container { padding: 18px 12px 40px; }
    .hero { padding: 18px 16px 16px; border-radius: 16px; }
    .section h2 { font-size: 17px; }
    table { min-width: 540px; }
}
"""


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scorecard — {job_id}</title>
<style>{style}</style>
</head>
<body>
    <div class="container">
        <header class="hero">
            <div class="hero-top">
                <div>
                    <h1 class="title">{job_id}</h1>
                    <div class="subtitle">Evaluation report for {agent_name}</div>
                </div>
                <span class="status-pill status-{gen_status_class}">{gen_status_label}</span>
            </div>

            <div class="meta-grid">
                <div class="meta-item">
                    <div class="eyebrow">Agent</div>
                    <div class="meta-value">{agent_name}</div>
                </div>
                <div class="meta-item">
                    <div class="eyebrow">Execution Status</div>
                    <div class="meta-value">{gen_status_label}</div>
                </div>
                <div class="meta-item">
                    <div class="eyebrow">Duration</div>
                    <div class="meta-value">{duration}</div>
                </div>
                <div class="meta-item">
                    <div class="eyebrow">Evaluated</div>
                    <div class="meta-value">{evaluated_at}</div>
                </div>
            </div>
        </header>

        <section class="section">
            <h2>Overall Summary</h2>
            <div class="summary-grid">
                {summary_cards}
            </div>
        </section>

        <section class="section">
            <h2>Static Analysis</h2>
            <div class="section-note">Analyzer findings are grouped by severity and shown as a table.</div>
            {static_analysis_card}
        </section>

        <section class="section">
            <h2>Object Contract</h2>
            <div class="section-note">Manifest checks, declared objects, and ID range validation.</div>
            {object_contract_card}
        </section>

        <section class="section">
            <h2>Security Permissions</h2>
            <div class="section-note">Permission-set coverage and refund authorization visibility.</div>
            {security_permissions_card}
        </section>

        <section class="section">
            <h2>Negative Cases</h2>
            <div class="section-note">Each evaluator check is rendered dynamically with collapsed evidence.</div>
            {negative_cases_card}
        </section>

        <section class="section">
            <h2>LLM Judge</h2>
            <div class="section-note">Judge output, errors, and raw response diagnostics.</div>
            {llm_judge_card}
        </section>

        <section class="section">
            <details>
                <summary>Raw JSON</summary>
                <div class="details-body raw-panel">
                    <pre><code>{raw_json}</code></pre>
                </div>
            </details>
        </section>
    </div>
</body>
</html>
"""


def _escape(value):
        if value is None:
                return "N/A"
        return escape(str(value))


def _json_text(value):
        return _escape(json.dumps(value, indent=2, ensure_ascii=False))


def _badge(text, kind="neutral"):
        return f'<span class="badge badge-{kind}">{_escape(text)}</span>'


def _status_kind(value):
        if isinstance(value, bool):
                return "success" if value else "danger"
        if value is None:
                return "neutral"

        normalized = str(value).strip().lower()
        if normalized in {"success", "passed", "completed", "true", "yes"}:
                return "success"
        if normalized in {"warning", "skipped", "partial"}:
                return "warning"
        if normalized in {"error", "failed", "timeout", "false", "no"}:
                return "danger"
        if normalized in {"running", "in progress"}:
                return "info"
        return "neutral"


def _status_label(value):
        if isinstance(value, bool):
                return "✓ Passed" if value else "✕ Failed"
        if value is None:
                return "N/A"

        normalized = str(value).strip().lower()
        if normalized == "success":
                return "✓ Success"
        if normalized == "passed":
                return "✓ Passed"
        if normalized == "completed":
                return "✓ Completed"
        if normalized == "skipped":
                return "⚠ Skipped"
        if normalized == "warning":
                return "⚠ Warning"
        if normalized in {"error", "failed", "timeout"}:
                return "✕ Failed"
        return str(value)


def _format_scalar(value):
        if value is None:
                return "N/A"
        if isinstance(value, bool):
                return "✓ Yes" if value else "✕ No"
        if isinstance(value, (int, float)):
                return str(value)
        return _escape(value)


def _kv_item(label, value):
        return f'<div class="kv"><div class="key">{_escape(label)}</div><div class="value">{value}</div></div>'


def _render_message_box(title, message, kind="warning"):
        return (
                f'<div class="{ "error-panel" if kind == "danger" else "panel" }">'
                f'<div class="section-summary">{_badge(title, kind)}</div>'
                f'<p class="error-text">{_escape(message)}</p>'
                f'</div>'
        )


def _render_table(headers, rows):
        if not rows:
                return '<div class="empty">No findings.</div>'

        header_html = "".join(f"<th>{_escape(header)}</th>" for header in headers)
        row_html = []
        for row in rows:
                cells = "".join(f"<td>{cell}</td>" for cell in row)
                row_html.append(f"<tr>{cells}</tr>")
        return f'<div class="table-wrap"><table><thead><tr>{header_html}</tr></thead><tbody>{"".join(row_html)}</tbody></table></div>'


def _render_details(summary, body_html, open_by_default=False):
        open_attr = " open" if open_by_default else ""
        return f'<details{open_attr}><summary>{_escape(summary)}</summary><div class="details-body">{body_html}</div></details>'


def _render_evidence_item(item):
        if item is None:
                return '<li><div class="empty">N/A</div></li>'
        if isinstance(item, (dict, list)):
                content = json.dumps(item, indent=2, ensure_ascii=False)
        else:
                content = str(item)
        content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
        return f'<li><pre><code>{_escape(content)}</code></pre></li>'


def _render_metric_card(title, value, subtitle="", kind="neutral"):
        return (
                f'<div class="metric-card">'
                f'<div class="metric-title">{_escape(title)}</div>'
                f'<div class="metric-main"><div class="metric-value">{value}</div><span class="badge badge-{kind}">{_escape(_status_label(kind))}</span></div>'
                f'{f"<div class=\"metric-sub\">{_escape(subtitle)}</div>" if subtitle else ""}'
                f'</div>'
        )


def _render_static_analysis(sa):
        if sa.get("status") != "success":
                return _render_message_box("Static Analysis", sa.get("error") or sa.get("reason") or "No analysis run for this job.", "danger")

        issue_counts = sa.get("issue_counts", {})
        summary = (
                '<div class="kv-grid">'
                + _kv_item("Score", _format_scalar(sa.get("score")))
                + _kv_item("Compiled clean", _format_scalar(sa.get("compiled_clean")))
                + _kv_item("Total issues", _format_scalar(sa.get("total_issues")))
                + _kv_item("Errors", _format_scalar(issue_counts.get("error")))
                + _kv_item("Warnings", _format_scalar(issue_counts.get("warning")))
                + _kv_item("Info", _format_scalar(issue_counts.get("info")))
                + '</div>'
        )

        issues = sa.get("issues", [])
        rows = []
        for issue in issues:
                severity = issue.get("severity", "info")
                rows.append([
                        _badge(severity.upper(), _status_kind(severity)),
                        _escape(issue.get("file")),
                        _escape(issue.get("line")),
                        _escape(issue.get("code")),
                        _escape(issue.get("message", "")),
                ])

        table = _render_table(["Severity", "File", "Line", "Rule", "Message"], rows)
        return f'<div class="panel">{summary}{table}</div>'


def _render_object_contract(oc):
        if oc.get("status") != "success":
                return _render_message_box("Object Contract", oc.get("error") or "Object contract check did not run.", "danger")

        declared_ranges = oc.get("declared_id_ranges", [])
        structural_problems = oc.get("structural_problems", [])
        out_of_range = oc.get("out_of_range_declarations", [])
        all_declarations = oc.get("all_declarations", [])

        summary = (
                '<div class="kv-grid">'
                + _kv_item("Passed", _format_scalar(oc.get("passed")))
                + _kv_item("Objects checked", _format_scalar(oc.get("objects_checked")))
                + _kv_item("Declared ID ranges", _format_scalar(len(declared_ranges)))
                + _kv_item("Structural problems", _format_scalar(len(structural_problems)))
                + _kv_item("Out-of-range declarations", _format_scalar(len(out_of_range)))
                + '</div>'
        )

        body = [summary]
        if declared_ranges:
                body.append(_render_details("Declared ID ranges", f'<pre><code>{_json_text(declared_ranges)}</code></pre>'))
        if structural_problems:
                body.append(_render_details(
                        "Structural problems",
                        '<ul class="problem-list">' + ''.join(f'<li>{_escape(problem)}</li>' for problem in structural_problems) + '</ul>',
                        open_by_default=True,
                ))
        if out_of_range:
                out_rows = [[_escape(item.get("kind")), _escape(item.get("id")), _escape(item.get("name")), _escape(item.get("file"))] for item in out_of_range]
                body.append(_render_details("Out-of-range declarations", _render_table(["Kind", "ID", "Name", "File"], out_rows)))
        if all_declarations:
                decl_rows = [[_escape(item.get("kind")), _escape(item.get("id")), _escape(item.get("name")), _escape(item.get("file"))] for item in all_declarations]
                body.append(_render_details(f"All declarations ({len(all_declarations)})", _render_table(["Kind", "ID", "Name", "File"], decl_rows)))

        return '<div class="panel">' + ''.join(body) + '</div>'


def _render_security_permissions(sp):
        if sp.get("status") != "success":
                return _render_message_box("Security Permissions", sp.get("error") or sp.get("reason") or "Security permission check did not run.", "danger")

        missing_roles = sp.get("missing_roles", [])
        violations = sp.get("violations", [])
        roles = sp.get("roles", {}) or {}

        summary = (
                '<div class="kv-grid">'
                + _kv_item("Passed", _format_scalar(sp.get("passed")))
                + _kv_item("Permission sets found", _format_scalar(sp.get("permission_set_count")))
                + _kv_item("Missing roles", _format_scalar(len(missing_roles)))
                + _kv_item("Violations", _format_scalar(len(violations)))
                + '</div>'
        )

        chips = []
        if missing_roles:
                chips.append(''.join(_badge(role, "warning") for role in missing_roles))
        else:
                chips.append(_badge("No missing roles", "success"))
        if violations:
                chips.append(''.join(_badge("Violation", "danger") for _ in violations))
        else:
                chips.append(_badge("No violations", "success"))

        role_cards = []
        for role_key, role in roles.items():
                refund_permissions = role.get("refund_permissions", []) or []
                role_cards.append(
                        '<div class="role-card">'
                        f'<h3>{_escape(role_key.replace("_", " ").title())}</h3>'
                        '<div class="role-lines">'
                        f'<div><span>Name:</span> {_escape(role.get("name") or "Not found")}</div>'
                        f'<div><span>File:</span> {_escape(role.get("file") or "N/A")}</div>'
                        f'<div><span>Refund permissions:</span> {_format_scalar(len(refund_permissions))}</div>'
                        f'</div>'
                        + (
                                _render_details(
                                        "Refund permission entries",
                                        f'<pre><code>{_json_text(refund_permissions)}</code></pre>'
                                ) if refund_permissions else ''
                        )
                        + '</div>'
                )

        body = [summary, '<div class="section-summary">' + ''.join(chips) + '</div>']
        if violations:
                body.append(
                        _render_details(
                                "Violations",
                                '<ul class="problem-list">' + ''.join(f'<li>{_escape(v)}</li>' for v in violations) + '</ul>',
                                open_by_default=True,
                        )
                )
        body.append('<div class="roles-grid">' + ''.join(role_cards) + '</div>')
        return '<div class="panel">' + ''.join(body) + '</div>'


def _render_negative_cases(nc):
        if nc.get("status") != "success":
                return _render_message_box("Negative Cases", nc.get("error") or nc.get("reason") or "Negative-case check did not run.", "danger")

        checks = nc.get("checks", {}) or {}
        failed_checks = nc.get("failed_checks", []) or []
        total_checks = len(checks)
        passed_checks = sum(1 for result in checks.values() if result.get("passed"))

        summary = (
                '<div class="kv-grid">'
                + _kv_item("Passed", _format_scalar(nc.get("passed")))
                + _kv_item("Checks passed", f"{passed_checks} / {total_checks}")
                + _kv_item("Failed checks", _format_scalar(len(failed_checks)))
                + '</div>'
        )

        if failed_checks:
                failure_badges = ''.join(_badge(check, "danger") for check in failed_checks)
        else:
                failure_badges = _badge("No failed checks", "success")

        check_cards = []
        for check_name, check_result in checks.items():
                evidence = check_result.get("evidence", []) or []
                evidence_html = (
                        '<ul class="evidence-list">' + ''.join(_render_evidence_item(item) for item in evidence) + '</ul>'
                        if evidence else '<div class="empty">No evidence captured.</div>'
                )
                details = _render_details(f"Evidence ({len(evidence)})", evidence_html)
                check_cards.append(
                        '<div class="role-card">'
                        f'<h3>{_escape(check_name.replace("_", " "))}</h3>'
                        f'<div class="section-summary">{_badge("Passed" if check_result.get("passed") else "Failed", "success" if check_result.get("passed") else "danger")}</div>'
                        + details +
                        '</div>'
                )

        return (
                '<div class="panel">'
                + summary
                + f'<div class="section-summary">{failure_badges}</div>'
                + '<div class="card-grid">' + ''.join(check_cards) + '</div>'
                + '</div>'
        )


def _render_llm_judge(lj):
        status = lj.get("status")
        if status == "skipped":
                return _render_message_box("LLM Judge", lj.get("reason", "Skipped."), "warning")
        if status == "error":
                error_message = lj.get("error") or "LLM judge failed."
                raw_output = lj.get("raw_output")
                body = [
                        '<div class="kv-grid">'
                        + _kv_item("Status", _status_label(status))
                        + _kv_item("Error", error_message)
                        + '</div>'
                ]
                if raw_output is not None:
                        body.append(_render_details("Raw output", f'<pre><code>{_escape(raw_output)}</code></pre>', open_by_default=True))
                return '<div class="error-panel">' + ''.join(body) + '</div>'

        if status is None:
                return _render_message_box("LLM Judge", "No judge data was returned.", "warning")

        items = []
        for key, value in lj.items():
                if key == "raw_output":
                        continue
                if isinstance(value, (dict, list)):
                        value_html = f'<pre><code>{_json_text(value)}</code></pre>'
                else:
                        value_html = _format_scalar(value)
                items.append(_kv_item(key.replace("_", " ").title(), value_html))

        body = '<div class="panel">' + '<div class="kv-grid">' + ''.join(items) + '</div>'
        raw_output = lj.get("raw_output")
        if raw_output:
                body += _render_details("Raw output", f'<pre><code>{_escape(raw_output)}</code></pre>')
        body += '</div>'
        return body


def _summary_card(title, main_value, kind="neutral", subtitle=""):
        return (
                '<div class="summary-card">'
                f'<div class="eyebrow">{_escape(title)}</div>'
                f'<div class="summary-value">{main_value}</div>'
                f'<div class="section-summary">{_badge(_status_label(kind), kind)}</div>'
                + (f'<div class="muted">{_escape(subtitle)}</div>' if subtitle else '')
                + '</div>'
        )


def render_scorecard_html(scorecard: dict) -> str:
        metrics = scorecard.get("metrics", {}) or {}

        sa = metrics.get("static_analysis", {}) or {}
        oc = metrics.get("object_contract", {}) or {}
        sp = metrics.get("security_permissions", {}) or {}
        nc = metrics.get("negative_cases", {}) or {}
        lj = metrics.get("llm_judge", {}) or {}

        summary_cards = []
        if sa.get("status") == "success":
                summary_cards.append(_summary_card(
                        "Static Analysis",
                        f'{_escape(sa.get("score", "N/A"))} / 10',
                        "info" if sa.get("compiled_clean") else "warning",
                        f'{_format_scalar(len(sa.get("issues", []) or []))} findings'
                ))
        else:
                summary_cards.append(_summary_card(
                        "Static Analysis",
                        _status_label(sa.get("status")),
                        _status_kind(sa.get("status")),
                        _escape(sa.get("error") or sa.get("reason") or "No analysis run")
                ))

        if oc.get("status") == "success":
                summary_cards.append(_summary_card(
                        "Object Contract",
                        _status_label(oc.get("passed")),
                        "success" if oc.get("passed") else "danger",
                        f'{_format_scalar(oc.get("objects_checked"))} objects checked'
                ))
        else:
                summary_cards.append(_summary_card(
                        "Object Contract",
                        _status_label(oc.get("status")),
                        _status_kind(oc.get("status")),
                        _escape(oc.get("error") or oc.get("reason") or "No object-contract result")
                ))

        if sp.get("status") == "success":
                summary_cards.append(_summary_card(
                        "Security Permissions",
                        _status_label(sp.get("passed")),
                        "success" if sp.get("passed") else "danger",
                        f'{_format_scalar(sp.get("permission_set_count"))} permission sets'
                ))
        else:
                summary_cards.append(_summary_card(
                        "Security Permissions",
                        _status_label(sp.get("status")),
                        _status_kind(sp.get("status")),
                        _escape(sp.get("error") or sp.get("reason") or "No security result")
                ))

        if nc.get("status") == "success":
                checks = nc.get("checks", {}) or {}
                passed_checks = sum(1 for result in checks.values() if result.get("passed"))
                summary_cards.append(_summary_card(
                        "Negative Cases",
                        _status_label(nc.get("passed")),
                        "success" if nc.get("passed") else "danger",
                        f'{passed_checks} / {len(checks)} checks passed'
                ))
        else:
                summary_cards.append(_summary_card(
                        "Negative Cases",
                        _status_label(nc.get("status")),
                        _status_kind(nc.get("status")),
                        _escape(nc.get("error") or nc.get("reason") or "No negative-case result")
                ))

        if lj.get("status") == "success":
                judge_value = lj.get("score", lj.get("status", "success"))
                summary_cards.append(_summary_card(
                        "LLM Judge",
                        _escape(judge_value),
                        "success",
                        _escape(lj.get("summary") or lj.get("result") or "Judge completed")
                ))
        elif lj.get("status") == "error":
                summary_cards.append(_summary_card(
                        "LLM Judge",
                        "Error",
                        "danger",
                        _escape(lj.get("error") or "Judge response could not be parsed")
                ))
        else:
                summary_cards.append(_summary_card(
                        "LLM Judge",
                        _status_label(lj.get("status")),
                        _status_kind(lj.get("status")),
                        _escape(lj.get("reason") or "No judge result")
                ))

        duration_seconds = scorecard.get("generation_duration_seconds")
        duration = f"{duration_seconds} s" if duration_seconds is not None else "N/A"
        gen_status = scorecard.get("generation_status", "unknown")
        gen_status_label = _status_label(gen_status)

        return TEMPLATE.format(
                job_id=_escape(scorecard.get("job_id", "unknown")),
                agent_name=_escape(scorecard.get("agent_name", "unknown")),
                duration=_escape(duration),
                evaluated_at=_escape(scorecard.get("evaluated_at", "N/A")),
                gen_status=gen_status,
                gen_status_label=gen_status_label,
                gen_status_class=_status_kind(gen_status),
                summary_cards="".join(summary_cards),
                static_analysis_card=_render_static_analysis(sa),
                object_contract_card=_render_object_contract(oc),
                security_permissions_card=_render_security_permissions(sp),
                negative_cases_card=_render_negative_cases(nc),
                llm_judge_card=_render_llm_judge(lj),
                raw_json=_json_text(scorecard),
                style=STYLE,
        )


def save_scorecard_html(job_dir: Path, scorecard: dict) -> Path:
        html = render_scorecard_html(scorecard)

        html_path = job_dir / "scorecard.html"
        html_path.write_text(html, encoding="utf-8")

        return html_path