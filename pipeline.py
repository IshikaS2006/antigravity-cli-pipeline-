import subprocess
import time
import shutil
import json 
import sys
from pathlib import Path
from datetime import datetime
from guardrails import validate_prompt
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
AGY_PATH = os.getenv("AGY_PATH")
JOBS_ROOT = Path("jobs").resolve()  # One trusted root for everything
MAX_WAIT = 900          # generous ceiling for a full multi-file build
POLL_INTERVAL = 2
QUIET_PERIOD = 20          # gap after generation is underway
STARTUP_GRACE = 30         # minimum time before we even consider "no files" a problem
EVAL_SCRIPT = Path(__file__).resolve().parent / "run_eval.py"

parser = argparse.ArgumentParser()
parser.add_argument("--variant-id", default=None, help="Optional variant tag for batch runs")
parser.add_argument("--requirements-file", default=None, help="Path to this job's requirements file")
args, _ = parser.parse_known_args()

# --- Create a fresh, timestamped job folder ---
AGENT_NAME = "antigravity"
job_id = datetime.now().strftime(f"job_%Y%m%d_%H%M%S_%f_{AGENT_NAME}")
job_dir = JOBS_ROOT / job_id
job_dir.mkdir(parents=True, exist_ok=False)

# Copy the shared system prompt into every new job folder as GEMINI.md
system_prompt_file = JOBS_ROOT / "system_prompt.txt"
if system_prompt_file.exists():
    shutil.copy(system_prompt_file, job_dir / "GEMINI.md")
else:
    raise FileNotFoundError(f"Missing: {system_prompt_file}")

# Read user requirements
requirements_file = Path(args.requirements_file).resolve() if args.requirements_file else JOBS_ROOT / "requirements.txt"
if requirements_file.exists():
    shutil.copy(requirements_file, job_dir / "requirements.txt")
else:
    raise FileNotFoundError(f"Missing: {requirements_file}")

user_prompt = requirements_file.read_text(encoding="utf-8").strip()
validate_prompt(user_prompt)

print("=" * 50)
print(f"Job: {job_id}")
print("Prompt:")
print(user_prompt)
print("=" * 50)

before_files = set(job_dir.rglob("*"))

proc = subprocess.Popen(
    [AGY_PATH, "--add-dir", str(job_dir), "--dangerously-skip-permissions", "--print", user_prompt],
    cwd=job_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    stdin=subprocess.DEVNULL,
    text=True,
)

start = time.time()
last_activity_time = time.time()   # updated any time the file set CHANGES, not just first time
seen_files = set(before_files)     # everything we've already counted
stdout_data = ""
stderr_data = ""
completion_reason = None

while True:
    if proc.poll() is not None:
        stdout_data, stderr_data = proc.communicate()
        completion_reason = "process_exited"
        print("agy exited on its own.")
        break

    current_files = set(job_dir.rglob("*"))
    new_files = current_files - seen_files

    if new_files:
        # Something changed -> reset the idle clock every time, not just once
        last_activity_time = time.time()
        seen_files |= new_files
        print(f"New file(s) detected: {[f.name for f in new_files]}")
    else:
        idle_for = time.time() - last_activity_time
        elapsed = time.time() - start
        if elapsed > STARTUP_GRACE and idle_for > QUIET_PERIOD:
            print(f"No new files for {QUIET_PERIOD}s — treating generation as complete. Terminating agy.")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            stdout_data, stderr_data = proc.communicate()
            completion_reason = "quiet_period_complete"
            break

    if time.time() - start > MAX_WAIT:
        print("Hit max wait time — force killing agy.")
        proc.kill()
        stdout_data, stderr_data = proc.communicate()
        completion_reason = "timeout"
        break

    time.sleep(POLL_INTERVAL)

if stdout_data:
    print(stdout_data)
    (job_dir / "reply.md").write_text(stdout_data, encoding="utf-8")
    
end_time = time.time()
if completion_reason == "quiet_period_complete":
    status = "success"
elif completion_reason == "timeout":
    status = "timeout"
elif completion_reason == "process_exited":
    status = "success" if proc.returncode == 0 else "error"
else:
    status = "unknown"

metadata = {
    "job_id": job_id,
    "agent_name": AGENT_NAME,
    "variant_id": args.variant_id,
    "started_at": datetime.fromtimestamp(start).isoformat(),
    "ended_at": datetime.fromtimestamp(end_time).isoformat(),
    "duration_seconds": round(end_time - start, 2),
    "exit_code": proc.returncode,
    "completion_reason": completion_reason,
    "status": status,
    "stderr_captured": bool(stderr_data),
}
(job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
if stderr_data:
    (job_dir / "stderr.log").write_text(stderr_data, encoding="utf-8")
META_FILES = {"GEMINI.md", "requirements.txt", "reply.md", "metadata.json","stderr.log"}
generated_dir = job_dir / "generated"
generated_dir.mkdir(exist_ok=True)

for f in job_dir.iterdir():
    if f.is_file() and f.name not in META_FILES:
        shutil.move(str(f), generated_dir / f.name)

if status == "success":
    print(f"\nRunning eval for {job_id}...")
    eval_result = subprocess.run(
        [sys.executable, str(EVAL_SCRIPT), "--job", str(job_dir)],
        cwd=EVAL_SCRIPT.parent,
        capture_output=True,
        text=True,
        timeout=300,
    )
    eval_ok = eval_result.returncode == 0
    print(eval_result.stdout)
    if not eval_ok:
        print(f"[eval] failed: {eval_result.stderr}")
    metadata["eval_status"] = "completed" if eval_ok else "failed"
else:
    print(f"\nSkipping eval — job status is '{status}'.")
    metadata["eval_status"] = "skipped"

(job_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

final_files = [f for f in job_dir.rglob("*") if f.is_file()]

print(f"\nFiles in {job_dir.name}:")
for f in final_files:
    print(" -", f.relative_to(job_dir))
print(f"JOB_ID:{job_id}")
print(f"\nPipeline Finished! Output at: {job_dir}")