# Antigravity Pipeline

A Python-based pipeline for generating code using Antigravity CLI with predefined guardrails and workspace isolation, along with an extensible evaluation framework for benchmarking generated code across multiple coding agents.

---

## Overview

This project consists of two independent stages:

### 1. Generation Pipeline

Automates code generation by:

- Reading a user prompt from `requirements.txt`
- Applying predefined system guardrails
- Executing Antigravity CLI inside a dedicated job workspace
- Organizing generated outputs and execution metadata for every run

### 2. Evaluation Framework

Evaluates generated code across multiple quality dimensions:

- Static Analysis (code quality and style)
- Execution Evaluation (does the generated program execute successfully)
- Test Execution (runs generated test cases when available)
- LLM-as-Judge (qualitative evaluation using an agentic CLI)

The evaluation framework is **agent-agnostic**. It interacts with generated outputs through a runner interface rather than directly accessing agent-specific folders. Supporting a new coding agent (Claude Code, Devin, Codex CLI, etc.) only requires implementing a new runner without modifying any evaluator logic.

---

# Project Structure

```text
antigravity-pipeline/
│
├── pipeline.py                     # Generation pipeline
├── guardrails.py                   # Prompt validation and safety checks
├── run_eval.py                     # Evaluation entry point
├── README.md
├── .gitignore
│
├── jobs/
│   ├── requirements.txt            # User prompt
│   ├── system_prompt.txt           # Shared system prompt
│   └── job_<timestamp>_<agent>/
│       ├── GEMINI.md
│       ├── requirements.txt
│       ├── reply.md
│       ├── metadata.json
│       ├── stderr.log
│       ├── scorecard.json
│       └── generated/
│           └── ...generated files
│
└── evaluation/
    ├── contracts/
    │   └── job_schema.py
    │
    ├── runners/
    │   ├── base_runner.py
    │   └── antigravity_runner.py
    │
    ├── evaluators/
    │   ├── static_analysis.py
    │   ├── execution.py
    │   ├── test_execution.py
    │   └── llm_judge.py
    │
    ├── scorecard.py
    └── README.md
```

---

# Features

## Generation Pipeline

- Non-interactive execution
- Prompt validation
- Guardrail enforcement
- Dedicated per-job workspace
- Automatic metadata generation
- Organized output directory for every execution

## Evaluation Framework

- Agent-agnostic architecture
- Static code quality analysis
- Execution validation
- Automated test execution
- LLM-based qualitative evaluation
- Aggregated scorecard generation
- Easily extensible to additional coding agents

---

# Requirements

- Python 3.10+
- Antigravity CLI installed

Python packages:

```bash
pip install pylint pytest
```

---

# Usage

## Generate Code

Place the prompt inside:

```text
jobs/requirements.txt
```

Run:

```bash
python pipeline.py
```

A new timestamped job folder will be created under `jobs/`.

---

## Evaluate Generated Code

Run:

```bash
python run_eval.py jobs/job_<timestamp>_<agent>/
```

The evaluator will:

1. Validate the job structure
2. Run all evaluation modules
3. Aggregate results
4. Generate `scorecard.json`

---

# Evaluation Metrics

| Metric | Purpose |
|---------|----------|
| Static Analysis | Measures code quality and style |
| Execution Evaluation | Verifies the generated program executes successfully |
| Test Execution | Executes generated tests and records pass/fait statistics |
| LLM-as-Judge | Evaluates correctness, completeness, and overall implementation quality |

---

# Architecture

```text
requirements.txt
        │
        ▼
   pipeline.py
        │
        ▼
Antigravity CLI
        │
        ▼
 Generated Project
        │
        ▼
  Runner Interface
        │
        ▼
 Evaluation Framework
        │
 ┌──────────┬──────────┬────────────┐
 ▼          ▼          ▼            ▼
Static   Execution   Testing    LLM Judge
Analysis Evaluation Execution
 └──────────┴──────────┴────────────┘
                     │
                     ▼
               Score Aggregator
                     │
                     ▼
               scorecard.json
```

---

# Known Limitations

- Execution evaluation currently performs a **controlled execution check** using `subprocess` with timeout and output capture. It is **not** a security sandbox or containerized execution environment.
- Static analysis scoring is heuristic-based and may be refined with additional benchmarking data.
- Currently only the Antigravity runner is implemented. Additional agents can be integrated by implementing new runner adapters.

---

# Extending to New Agents

The evaluation framework is intentionally designed to remain independent of the code generation agent.

To support a new agent:

1. Implement a new runner inside `evaluation/runners/`
2. Convert the agent's output into the standard job schema
3. Reuse all existing evaluators without modification

No changes are required in:

- Static Analysis
- Execution Evaluation
- Test Execution
- LLM Judge
- Score Aggregation

---

# Notes

- Every generation request creates a separate timestamped job directory.
- Generated code, execution metadata, replies, and evaluation reports remain isolated per job.
- Temporary files are ignored through `.gitignore`.
- The project is designed for future benchmarking across multiple coding agents using a common evaluation framework.