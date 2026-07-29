import sys
import json
import argparse
from pathlib import Path

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Comparison Report — {batch_id}</title>
<style>
  :root {{
    --bg: #fafafa;
    --card: #ffffff;
    --border: #e5e5e5;
    --text: #1a1a1a;
    --muted: #6b6b6b;
    --good: #1a7f37;
    --bad: #b91c1c;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 1100px;
    margin: 0 auto;
    padding: 48px 24px 80px;
    line-height: 1.5;
  }}
  h1 {{ font-size: 22px; font-weight: 600; margin: 0 0 4px; }}
  .meta {{ color: var(--muted); font-size: 13px; margin-bottom: 32px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }}
  th, td {{
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    border-bottom: 1px solid #f0f0f0;
    vertical-align: top;
  }}
  th {{
    background: #f7f7f7;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--muted);
    font-size: 11px;
    font-weight: 600;
  }}
  .metric-label {{ color: var(--muted); font-weight: 500; white-space: nowrap; }}
  .status-pill {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }}
  .status-success {{ background: #e6f4ea; color: var(--good); }}
  .status-failed, .status-unknown {{ background: #fbeaea; color: var(--bad); }}
  .prompt-label {{ font-weight: 600; }}
</style>
</head>
<body>
  <h1>Comparison Report</h1>
  <div class="meta">Batch: {batch_id} · {variant_count} variants</div>
  <table>
    {table_rows}
  </table>
</body>
</html>
"""


def _cell(value):
    if value is None:
        return '<span style="color:#b91c1c;">—</span>'
    return str(value)


def build_comparison_html(batch_id: str, manifest: list, scorecards: dict) -> str:
    variant_ids = [m["variant_id"] for m in manifest]

    header = "<tr><th>Metric</th>" + "".join(
        f'<th>{m.get("label") or m["variant_id"]}<br>'
        f'<span class="status-pill status-{m["status"]}">{m["status"]}</span></th>'
        for m in manifest
    ) + "</tr>"

    def metric_row(label, extractor):
        cells = "".join(
            f"<td>{_cell(extractor(scorecards.get(m['job_id'])) if m['job_id'] else None)}</td>"
            for m in manifest
        )
        return f'<tr><td class="metric-label">{label}</td>{cells}</tr>'

    rows = [header]
    rows.append(metric_row("Static analysis score",
        lambda sc: sc["metrics"]["static_analysis"].get("average_score") if sc else None))
    rows.append(metric_row("Files analyzed",
        lambda sc: sc["metrics"]["static_analysis"].get("files_analyzed") if sc else None))
    rows.append(metric_row("Object contract",
      lambda sc: sc["metrics"]["object_contract"].get("passed") if sc and "object_contract" in sc["metrics"] else None))
    rows.append(metric_row("LLM judge",
        lambda sc: sc["metrics"]["llm_judge"].get("status") if sc else None))
    rows.append(metric_row("Job ID",
        lambda sc: sc.get("job_id") if sc else None))

    return TEMPLATE.format(
        batch_id=batch_id,
        variant_count=len(variant_ids),
        table_rows="".join(rows),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", required=True, help="Path to jobs/batches/<batch_id>")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir).resolve()
    manifest_path = batch_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"No manifest found at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    jobs_root = batch_dir.parent.parent  # jobs/batches/<id> -> jobs/

    scorecards = {}
    for entry in manifest:
        job_id = entry.get("job_id")
        if not job_id:
            continue
        scorecard_path = jobs_root / job_id / "scorecard.json"
        if scorecard_path.exists():
            scorecards[job_id] = json.loads(scorecard_path.read_text(encoding="utf-8"))
        else:
            print(f"[compare] scorecard missing for {job_id}, skipping")

    html = build_comparison_html(batch_dir.name, manifest, scorecards)
    out_path = batch_dir / "comparison_report.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Comparison report written to: {out_path}")


if __name__ == "__main__":
    main()