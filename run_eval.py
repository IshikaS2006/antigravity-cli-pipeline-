import sys
import json
import argparse
from pathlib import Path
from evaluation.runners.standard_runner import StandardRunner
from evaluation.evaluators.static_analysis import run_static_analysis_on_job
from evaluation.evaluators.sandbox_exec import run_sandbox_on_job
from evaluation.scorecard import build_scorecard, save_scorecard
from evaluation.evaluators.test_execution import run_test_evaluation_on_job
from evaluation.evaluators.llm_judge import run_llm_judge
from evaluation.dashboard.render_html import save_scorecard_html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="Path to job directory")
    args = parser.parse_args()

    job_dir = Path(args.job).resolve()
    runner = StandardRunner()

    try:
        metadata = runner.validate(job_dir)
        files = runner.get_generated_files(job_dir)
        reply = runner.get_reply(job_dir)

        static_analysis = run_static_analysis_on_job(files)
        sandbox_execution = run_sandbox_on_job(files)
        test_results = run_test_evaluation_on_job(files)
        llm_judge = run_llm_judge(job_dir, files, static_analysis, sandbox_execution)

        scorecard = build_scorecard(job_dir, metadata, static_analysis, sandbox_execution, test_results, llm_judge)
        scorecard_path = save_scorecard(job_dir, scorecard)
        html_path = save_scorecard_html(job_dir, scorecard)
        print("Metadata:", metadata)
        print("Generated files:", [f.name for f in files])
        print(f"\nScorecard saved to: {scorecard_path}")
        print(f"HTML report saved to: {html_path}")
        print(json.dumps(scorecard, indent=2))
    except Exception as e:
        print(f"Eval failed: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()