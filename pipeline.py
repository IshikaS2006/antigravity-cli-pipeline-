import subprocess
import time
import shutil
from pathlib import Path
from datetime import datetime

from guardrails import validate_prompt

# --- Config ---
AGY_PATH = r"C:\Users\Lenovo\AppData\Local\agy\bin\agy.exe"
SCRATCH_DIR = Path.home() / ".gemini" / "antigravity-cli" / "scratch"
JOBS_ROOT = Path("jobs").resolve()  # One trusted root for everything

MAX_WAIT = 900          # generous ceiling for a full multi-file build
POLL_INTERVAL = 2
QUIET_PERIOD = 45       # seconds of TRUE silence (no new files at all) before we call it done

# --- Create a fresh, timestamped job folder ---
job_id = datetime.now().strftime("job_%Y%m%d_%H%M%S")
job_dir = JOBS_ROOT / job_id
job_dir.mkdir(parents=True, exist_ok=False)

# Copy the shared system prompt into every new job folder as GEMINI.md
system_prompt_file = JOBS_ROOT / "system_prompt.txt"
if system_prompt_file.exists():
    shutil.copy(system_prompt_file, job_dir / "GEMINI.md")
else:
    raise FileNotFoundError(f"Missing: {system_prompt_file}")

# Read user requirements
requirements_file = JOBS_ROOT / "requirements.txt"
if not requirements_file.exists():
    raise FileNotFoundError(f"Missing: {requirements_file}")

user_prompt = requirements_file.read_text(encoding="utf-8").strip()
validate_prompt(user_prompt)

print("=" * 50)
print(f"Job: {job_id}")
print("Prompt:")
print(user_prompt)
print("=" * 50)

before_files = set(job_dir.rglob("*"))
before_scratch = set(SCRATCH_DIR.rglob("*")) if SCRATCH_DIR.exists() else set()

proc = subprocess.Popen(
    [AGY_PATH, "--add-dir", str(job_dir), "--sandbox", "--print", user_prompt],
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

while True:
    if proc.poll() is not None:
        stdout_data, stderr_data = proc.communicate()
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
        if idle_for > QUIET_PERIOD:
            print(f"No new files for {QUIET_PERIOD}s — treating generation as complete. Terminating agy.")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            break

    if time.time() - start > MAX_WAIT:
        print("Hit max wait time — force killing agy.")
        proc.kill()
        break

    time.sleep(POLL_INTERVAL)

if stdout_data:
    print(stdout_data)
    (job_dir / "agy_reply.md").write_text(stdout_data, encoding="utf-8")

# Rescue anything that leaked into scratch
after_scratch = set(SCRATCH_DIR.rglob("*")) if SCRATCH_DIR.exists() else set()

for f in [f for f in (after_scratch - before_scratch) if f.is_file()]:
    dest = job_dir / f.name
    shutil.move(str(f), dest)
    print(f"Rescued from scratch -> {dest}")

final_files = [f for f in job_dir.rglob("*") if f.is_file()]

print(f"\nFiles in {job_dir.name}:")
for f in final_files:
    print(" -", f.relative_to(job_dir))

print(f"\nPipeline Finished! Output at: {job_dir}")