import sys
import json
import argparse
from pathlib import Path
from evaluation.runners.standard_runner import StandardRunner
from evaluation.scorecard import build_scorecard, save_scorecard
from evaluation.evaluators.al_pipeline import run_full_pipeline
from evaluation.evaluators.static_analysis import run_static_analysis_on_job
from evaluation.evaluators.test_execution import run_test_evaluation_on_job
from evaluation.evaluators.llm_judge import run_llm_judge
from evaluation.evaluators.sandbox_exec import run_sandbox_on_job
from docs.render_html import save_scorecard_html

NUGET_EXE_PATH = r"D:\college\own\i1\antigravity-pipeline\evaluation\nuget.exe"


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

        # FLAG: 'files' has printed empty ([]) in every job so far — if
        # get_generated_files() is broken, llm_judge/sandbox_exec/test_execution
        # below will all silently see zero files regardless of any other fix.
        print("Generated files:", [f.name for f in files])

        generated_dir = job_dir / "generated"

        al_compile = run_full_pipeline(generated_dir, nuget_exe=NUGET_EXE_PATH)

        # static_analysis re-compiles with analyzers on, reusing al_compile's
        # symbols_dir — only run it if al_compile actually succeeded.
        if al_compile.get("success"):
            static_analysis = run_static_analysis_on_job(
                generated_dir, symbols_dir=Path(al_compile["symbols_dir"])
            )
        else:
            static_analysis = {"status": "skipped", "reason": "al_compile did not succeed"}

        test_execution = run_test_evaluation_on_job(files)
        sandbox_exec = run_sandbox_on_job(files)
        llm_judge = run_llm_judge(job_dir, files, static_analysis, sandbox_exec)

        scorecard = build_scorecard(
            job_dir,
            metadata,
            al_compile=al_compile,
            static_analysis=static_analysis,
            test_execution=test_execution,
            sandbox_exec=sandbox_exec,
            llm_judge=llm_judge,
        )

        scorecard_path = save_scorecard(job_dir, scorecard)
        html_path = save_scorecard_html(job_dir, scorecard)
        print("Metadata:", metadata)
        print(f"\nScorecard saved to: {scorecard_path}")
        print(f"HTML report saved to: {html_path}")
        print(json.dumps(scorecard, indent=2))
    except Exception as e:
        print(f"Eval failed: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()