import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import time 

VARIANTS_FILE = Path("config/variants.json")
REQUIREMENTS_FILE = Path("jobs/requirements.txt")

batch_id = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
batch_dir = Path("jobs/batches") / batch_id
batch_dir.mkdir(parents=True, exist_ok=True)
MANIFEST_FILE = batch_dir / "manifest.json"

variants = json.loads(VARIANTS_FILE.read_text(encoding="utf-8"))
manifest = []
batch_start = time.time()   # add this

for variant in variants:
    print(f"\n=== Running variant: {variant['variant_id']} ===")
    REQUIREMENTS_FILE.write_text(variant["prompt"], encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "pipeline.py", "--variant-id", variant["variant_id"]],
        capture_output=True,
        text=True,
    )
    print(result.stdout)

    if result.returncode != 0:
        print(f"[batch] variant {variant['variant_id']} failed: {result.stderr}")
        manifest.append({"variant_id": variant["variant_id"], "label": variant.get("label", ""),
                          "job_id": None, "status": "failed"})
        continue

    job_id = None
    for line in result.stdout.splitlines():
        if line.startswith("JOB_ID:"):
            job_id = line.split("JOB_ID:", 1)[1].strip()
            break

    manifest.append({"variant_id": variant["variant_id"], "label": variant.get("label", ""),
                      "job_id": job_id, "status": "success" if job_id else "unknown"})

batch_end = time.time()   # add this
manifest_summary = {
    "total_duration_seconds": round(batch_end - batch_start, 2),
    "variants": manifest,
}
MANIFEST_FILE.write_text(json.dumps(manifest_summary, indent=2), encoding="utf-8")
print(f"\nBatch complete. Manifest saved to: {MANIFEST_FILE}")
print(f"Total batch execution time: {batch_end - batch_start:.2f}s")

compare_result = subprocess.run(
    [sys.executable, "compare_scorecards.py", "--batch-dir", str(batch_dir)],
    capture_output=True,
    text=True,
)
print(compare_result.stdout)
if compare_result.returncode != 0:
    print(f"[batch] comparison report failed: {compare_result.stderr}")
else:
    print(f"Comparison report saved to: {batch_dir / 'comparison_report.html'}")