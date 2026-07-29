import sys
import json
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from evaluation.runners.standard_runner import StandardRunner
from evaluation.scorecard import build_scorecard, save_scorecard
from evaluation.evaluators.al_pipeline import run_full_pipeline, resolve_alc_path
from evaluation.evaluators.static_analysis import run_static_analysis_on_job
from evaluation.evaluators.object_contract import run_manifest_validation_on_job
from evaluation.evaluators.llm_judge import run_llm_judge
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
        alc_path = resolve_alc_path()

        print("Generated files:", [f.name for f in files])

        generated_dir = job_dir / "generated"

        with ThreadPoolExecutor(max_workers=3) as executor:
            object_contract_future = executor.submit(run_manifest_validation_on_job, generated_dir)
            al_compile = run_full_pipeline(generated_dir, nuget_exe=NUGET_EXE_PATH, alc_path=alc_path)

            # static_analysis re-compiles with analyzers on, reusing al_compile's
            # symbols_dir — only run it if al_compile actually succeeded.
            if al_compile.get("success"):
                static_analysis = run_static_analysis_on_job(
                    generated_dir, symbols_dir=Path(al_compile["symbols_dir"]), alc_path=alc_path
                )
            else:
                static_analysis = {"status": "skipped", "reason": "al_compile did not succeed"}

            llm_judge_future = executor.submit(run_llm_judge, job_dir, files, static_analysis)

            object_contract = object_contract_future.result()
            llm_judge = llm_judge_future.result()

        scorecard = build_scorecard(
            job_dir,
            metadata,
            al_compile=al_compile,
            static_analysis=static_analysis,
            object_contract=object_contract,
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