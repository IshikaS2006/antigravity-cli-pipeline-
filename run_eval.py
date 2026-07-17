import sys
import json
from pathlib import Path
from evaluation.runners.standard_runner import StandardRunner
from evaluation.evaluators.static_analysis import run_static_analysis_on_job
from evaluation.evaluators.sandbox_exec import run_sandbox_on_job
from evaluation.scorecard import build_scorecard, save_scorecard
from evaluation.evaluators.test_execution import run_test_evaluation_on_job
from evaluation.evaluators.llm_judge import run_llm_judge


job_dir = Path(sys.argv[1]).resolve()
runner = StandardRunner()

metadata = runner.validate(job_dir)
files = runner.get_generated_files(job_dir)
reply = runner.get_reply(job_dir)

static_analysis = run_static_analysis_on_job(files)
sandbox_execution = run_sandbox_on_job(files)
test_results = run_test_evaluation_on_job(files)
llm_judge = run_llm_judge(job_dir, files, static_analysis, sandbox_execution)

scorecard = build_scorecard(job_dir, metadata, static_analysis, sandbox_execution, test_results, llm_judge)
scorecard_path = save_scorecard(job_dir, scorecard)

print("Metadata:", metadata)
print("Generated files:", [f.name for f in files])
print(f"\nScorecard saved to: {scorecard_path}")
print(json.dumps(scorecard, indent=2))