# Antigravity Pipeline

A Python-based pipeline for executing Antigravity CLI with predefined guardrails.

## Overview

This project automates code generation by:

- Reading a user prompt from a requirements file.
- Applying system guardrails.
- Executing Antigravity CLI in a controlled workspace.
- Saving generated outputs for each execution.

## Project Structure

```
antigravity-pipeline/
│── pipeline.py
│── guardrails.py
│── README.md
│── .gitignore
│── jobs/
    └── requirements.txt
    └── system_prompts.txt
    └── .gitkeep
    └──job_YYYYMMDD_HHMMSS/
        ├── GEMINI.md
        ├── agy_reply.md
        └── generated_files
```

## Features

- Non-interactive execution
- Prompt validation
- Workspace isolation
- Guardrail enforcement
- Job-based output organization

## Requirements

- Python 3.10+
- Antigravity CLI installed

## Usage

1. Place your prompt inside:

```
jobs/requirements.txt
```

2. Run:

```bash
python pipeline.py
```

3. Generated outputs will be saved in the corresponding job directory.

## Files

- `pipeline.py` – Main execution pipeline
- `guardrails.py` – Prompt validation and safety checks
- `GEMINI.md` – System instructions for Antigravity CLI
- `jobs/requirements.txt` – User prompt
- `jobs/` – Generated outputs

## Notes

- The pipeline is designed to execute only inside the configured workspace.
- Interactive prompts are disabled for automated execution.
- Temporary files are ignored through `.gitignore`.