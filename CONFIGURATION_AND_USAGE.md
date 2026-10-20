# Harness² — Configuration and Usage Guide

This guide explains how **Harness²** (`google-research/harness2`) is configured in this repository, how its recursive agent-harnessing pipeline works, and how to configure and run experiments locally.

---

## Table of Contents

1. [Overview: What is Harness²?](#1-overview-what-is-harness)
2. [What Is Configured in This Repository](#2-what-is-configured-in-this-repository)
3. [How to Configure Harness²](#3-how-to-configure-harness)
   - [Environment Variables Reference](#31-environment-variables-reference)
   - [Model Naming Rules (Important)](#32-model-naming-rules-important)
   - [Using Preset Configurations (`configs/`)](#33-using-preset-configurations-configs)
   - [Authentication Setup](#34-authentication-setup)
   - [Configuring the Codex Executor (`--substrate cx`)](#35-configuring-the-codex-executor---substrate-cx)
4. [How to Use Harness² (Workflows)](#4-how-to-use-harness-workflows)
   - [Activate the Virtual Environment](#41-activate-the-virtual-environment)
   - [Run the Local Credential-Free Demo](#42-run-the-local-credential-free-demo)
   - [Install a Benchmark (`lab`, `jb`, `wb`)](#43-install-a-benchmark-lab-jb-wb)
   - [Run Preflight Checks (`harness2-check`)](#44-run-preflight-checks-harness2-check)
   - [Preview Tasks & Domains (`--dry-run`)](#45-preview-tasks--domains---dry-run)
   - [Create Train/Test Task Splits](#46-create-traintest-task-splits)
   - [Run Recursive Harness Adaptation (`harness2`)](#47-run-recursive-harness-adaptation-harness2)
   - [Judge Deliverables (`harness2-judge`)](#48-judge-deliverables-harness2-judge)
   - [Generate Score Reports (`harness2-report`)](#49-generate-score-reports-harness2-report)
   - [One-Command End-to-End Scripts](#410-one-command-end-to-end-scripts)
5. [Editable Harness Surface (`c1..c8`)](#5-editable-harness-surface-c1c8)
6. [Output Structure, Resuming Runs, and Troubleshooting](#6-output-structure-resuming-runs-and-troubleshooting)

---

## 1. Overview: What is Harness²?

An agent **harness** is everything surrounding an LLM that turns it into an effective agent: system prompts, guardrails, memory, tool descriptions, subagents, skills, helper scripts, and lifecycle hooks/plugins.

**Harness²** optimizes the agent harness at deployment time **without ground-truth labels or verifiers** and **without modifying model weights**, using two coupled levels of recursion:

1. **Task-Level Recursion (Propose–Probe–Compose)**:
   - Runs `k` reference executions of the base harness on the current task.
   - **Proposes** `k` general (invariant, `INV`) harness edits and `k` domain-specific (`DOM`) harness edits based on execution trajectories and deliverables.
   - **Probes** each candidate harness by executing it on the same task.
   - **Composes** `k` refined harnesses by contrasting behavioral differences across candidate executions, then selects the best deliverable via a blind terminal selector.
   - **Modes**:
     - `--mode parallel` (`agg` on disk): Explores wider (`k` invariant + `k` domain candidates in parallel, then `k` compositions).
     - `--mode sequential` (`seq` on disk): Refines deeper (`k` sequential Propose–Probe–Compose steps, carrying the refined harness forward).
   - **Cost per task**: `R = 4k` executor rollouts and `P = 3k` improver sessions.
2. **Harnessing-Level Recursion (Experience Library)**:
   - After a task finishes and a harness is adopted, an experience reflector distills evidence-backed lessons (`EXPERIENCE.md`) and saves the adopted harness into a per-domain library (`runs/<bench>/library/`).
   - Subsequent tasks in the same domain read prior entries to guide future proposals.

---

## 2. What Is Configured in This Repository

The local workspace (`/home/meldude/harness2`) has been initialized and configured with:

| Path | Purpose |
|---|---|
| `.venv/` | Python 3.12 virtual environment with `harness2` installed in editable mode along with `[render,bridge]` extras (`openpyxl`, `python-pptx`, `litellm[proxy]`, `fastapi`, `google-auth`). |
| `.env.example` | Documented template of all supported Harness² environment variables. |
| `.env` | Active local configuration file (git-ignored so your credentials/project IDs stay private). |
| `configs/vertex-gemini.env` | Tracked preset for Vertex AI Gemini solver, improver, and judge (OpenCode substrate). |
| `configs/vertex-claude-improver.env` | Tracked preset using Vertex Gemini as solver/judge and Vertex Claude Sonnet as the improver. |
| `configs/codex-bridge.env` | Tracked preset for running the Codex CLI substrate (`--substrate cx`) via `harness2-bridge`. |
| `.gitignore` | Protects `.env`, `.venv/`, `runs/`, and downloaded third-party checkouts under `dependencies/` while keeping configs and docs tracked in Git. |
| `dependencies/opencode/` & `dependencies/harvey-labs/` | Installed and patched OpenCode runtime (with Bun `1.3.11`) and the **LAB** legal benchmark (`1,143` tasks across 10 legal domains). |
| `harness2/cli/setup.py` | Enhanced with an automatic `bun` postinstall check so `npm v12+` script blocking does not break `harness2-setup`. |

---

## 3. How to Configure Harness²

Configuration is loaded by [`harness2/config.py`](harness2/config.py) from `.env` in the repository root. **Shell environment variables always override `.env` values.**

### 3.1 Environment Variables Reference

| Variable | Required? | Default | Description |
|---|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | Yes (for Vertex AI) | `""` | Your Google Cloud Project ID with Vertex AI API enabled. |
| `GOOGLE_CLOUD_LOCATION` | No | `global` | Vertex AI region (`global`, `us-central1`, `us-east5`, etc.). |
| `HARNESS2_SOLVER_MODEL` | Yes | `""` | Executor model in OpenCode `provider/model` format (e.g. `google-vertex/gemini-2.5-flash`). |
| `HARNESS2_IMPROVER_MODEL` | No | `HARNESS2_SOLVER_MODEL` | Improver (proposer/composer/selector/reflector) model in `provider/model` format. |
| `HARNESS2_JUDGE_MODEL` | Yes (for sweeps & judging) | `""` | **Bare** model ID for grading deliverables (e.g. `gemini-2.5-pro`). |
| `HARNESS2_RUNS_DIR` | No | `runs` | Root directory where sweep states, deliverables, libraries, and scores are stored. |
| `HARNESS2_CODEX_BASE_URL` | Only for `--substrate cx` | `""` | Responses API endpoint URL for Codex (printed by `harness2-bridge`). |
| `HARNESS2_CODEX_API_KEY` | Only for `--substrate cx` | `""` | API key for the Codex Responses endpoint / local bridge. |
| `HARNESS2_CODEX_MODEL` | Only for `--substrate cx` | `<SOLVER_MODEL without prefix>` | Bare model name served by the Codex Responses endpoint. |
| `HARNESS2_CODEX_CONTAINER_URL` | Only for `wb` + `cx` | `HARNESS2_CODEX_BASE_URL` | URL reachable from inside WorkBuddy Docker containers (`http://host.docker.internal:<port>/v1`). |
| `HARNESS2_JUDGE_BASE_URL` | Optional (`jb` only) | Vertex OpenAI URL | Custom OpenAI-compatible base URL if using a non-Vertex judge for JobBench. |
| `HARNESS2_JUDGE_API_KEY` | Optional (`jb` only) | `""` | API key for a custom JobBench judge endpoint. |

### 3.2 Model Naming Rules (Important)

Harness² validates model strings strictly before starting any run:

1. **`HARNESS2_SOLVER_MODEL` and `HARNESS2_IMPROVER_MODEL` MUST include a provider prefix (`provider/model`)**:
   - Vertex Gemini: `google-vertex/gemini-2.5-flash`, `google-vertex/gemini-2.5-pro`
   - Vertex Anthropic Claude: `google-vertex-anthropic/claude-sonnet-4-5@20250929`
2. **`HARNESS2_JUDGE_MODEL` MUST be a bare model ID (no `google-vertex/` prefix)** for Vertex AI:
   - Good: `gemini-2.5-pro`, `gemini-2.5-flash`, `claude-sonnet-4-5@20250929`
   - Why: Each benchmark adapter automatically prepends the prefix its own grader expects (`vertex/` for LAB, `google/` for JobBench and WorkBuddy).
3. **WorkBuddy-Bench restriction**:
   - WorkBuddy requires `HARNESS2_SOLVER_MODEL` to start with `google-vertex/gemini` and `HARNESS2_JUDGE_MODEL` to start with `gemini`. If you change either model in `.env`, re-run `harness2-setup wb` so `configs/models/harness2/{solver,judge}.yaml` is regenerated.

### 3.3 Using Preset Configurations (`configs/`)

Three ready-to-use configuration presets are stored in [`configs/`](configs/):

```bash
# Option A: Vertex AI Gemini for Solver, Improver, and Judge (Recommended Default)
cp configs/vertex-gemini.env .env

# Option B: Vertex Gemini Solver + Vertex Claude Sonnet Improver
cp configs/vertex-claude-improver.env .env

# Option C: Codex Substrate via Local LiteLLM Bridge
cp configs/codex-bridge.env .env
```

After copying a preset to `.env`, edit `GOOGLE_CLOUD_PROJECT` in `.env` to match your GCP project ID.

### 3.4 Authentication Setup

Harness² uses Google Cloud Application Default Credentials (ADC) for Vertex AI models. Ensure the [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) is installed and on your `PATH`, then run:

```bash
# Standard interactive login:
gcloud auth application-default login

# Headless / SSH machine without a local browser:
gcloud auth application-default login --no-browser

# Or use a Service Account JSON key file:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

> **Note:** Even when using `GOOGLE_APPLICATION_CREDENTIALS` or an attached VM service account, `gcloud` must be on `PATH` because `harness2-check` verifies credentials via `gcloud auth application-default print-access-token`.

### 3.5 Configuring the Codex Executor (`--substrate cx`)

By default, Harness² uses **OpenCode** (`--substrate oc`). To use the **Codex CLI** executor (`--substrate cx`) with Gemini on Vertex AI:

1. Start the local LiteLLM Responses API bridge in a separate terminal:
   ```bash
   source .venv/bin/activate
   harness2-bridge
   # Or, if running WorkBuddy-Bench (which runs inside Docker containers):
   harness2-bridge --host 0.0.0.0
   ```
2. Copy the `HARNESS2_CODEX_*` lines printed by `harness2-bridge` into your `.env`.
3. Run setup with `--substrate cx` to write `dependencies/codex/home/config.toml`:
   ```bash
   harness2-setup lab --substrate cx
   harness2-check --bench lab --substrate cx
   ```
   *(If you later change `HARNESS2_CODEX_BASE_URL` or `HARNESS2_CODEX_MODEL`, re-run `harness2-setup <bench> --substrate cx`.)*

---

## 4. How to Use Harness² (Workflows)

### 4.1 Activate the Virtual Environment

Always run commands from `/home/meldude/harness2` with the main `.venv` active:

```bash
cd /home/meldude/harness2
source .venv/bin/activate
```

### 4.2 Run the Local Credential-Free Demo

Verify the installation and observe both parallel (`agg`) and sequential (`seq`) recursion modes without making any cloud API calls:

```bash
harness2-demo --output runs/demo --k 2
```

- Runs 2 local accounting tasks (`ledger-1`, `ledger-2`) using deterministic local editors and real Python script executions.
- Writes full trajectory, candidate diff, selection, reflection, and experience library artifacts under `runs/demo/`.
- Re-running the exact same command demonstrates **automatic checkpoint resume** (`skipped` on already-completed tasks).

### 4.3 Install a Benchmark (`lab`, `jb`, `wb`)

Each benchmark is installed on demand into `dependencies/` (with its own isolated `.venv` that Harness² invokes automatically):

```bash
# 1. LAB (Legal tasks - already installed in this workspace!)
#    Requires: pandoc, poppler-utils (pdftoppm)
harness2-setup lab

# 2. JobBench (Professional tasks across occupations; downloads dataset from Hugging Face)
harness2-setup jb

# 3. WorkBuddy-Bench (Office, Web, and Code tasks; requires Docker daemon)
harness2-setup wb --subset office   # or --subset web, --subset code, or omit --subset for all 3
```

Add `--dry-run` to any `harness2-setup` command to preview the exact clone, patch, and install commands without executing them.

### 4.4 Run Preflight Checks (`harness2-check`)

Before launching a paid benchmark run, verify that patches, dependencies, model settings, and credentials are ready:

```bash
harness2-check --bench lab
harness2-check --bench jb
harness2-check --bench wb --subset office
```

### 4.5 Preview Tasks & Domains (`--dry-run`)

Use `--dry-run` on `harness2` to inspect the task stream, available domain names, and output namespaces without calling any models or requiring cloud credentials:

```bash
# Preview all 1,143 tasks and 10 legal domains in LAB:
harness2 --bench lab --k 1 --mode parallel --dry-run

# Preview 1 task from a single domain:
harness2 --bench lab --k 1 --mode parallel \
  --only-domains antitrust-competition --max-tasks 1 --dry-run
```

### 4.6 Create Train/Test Task Splits

To create a reproducible, domain-stratified train/test partition:

```bash
python scripts/split_tasks.py --bench lab --seed 42 --output splits/lab.json
```

Then pass `--split-file splits/lab.json --split test` (or `--split train`) to `harness2`.

### 4.7 Run Recursive Harness Adaptation (`harness2`)

Start small (e.g., 1 domain, `--max-tasks 1`, `--k 1`) to verify model access and cost before scaling up:

```bash
# Single Propose-Probe-Compose step (k=1) in parallel mode on 1 task:
harness2 --bench lab --k 1 --mode parallel \
  --only-domains antitrust-competition --max-tasks 1

# Higher recursion budget (k=2) in sequential mode across 2 concurrent domains:
HARNESS2_RUNS_DIR=runs/lab-seq-k2 \
harness2 --bench lab --k 2 --mode sequential \
  --only-domains antitrust-competition,corporate-ma \
  --max-tasks 2 --workers 2
```

**Key CLI flags for `harness2`:**
- `--bench {jb,lab,wb}`: Target benchmark (`wb` also requires `--subset {office,web,code}`).
- `--substrate {oc,cx}`: Executor framework (`oc` = OpenCode default, `cx` = Codex).
- `--k INT`: Recursion budget per task (`R = 4k` executor rollouts, `P = 3k` improver calls).
- `--mode {parallel,sequential}`: Recursion mode (or `parallel,sequential` to run both on the same reference rollouts).
- `--only-domains DOMAIN1,DOMAIN2`: Filter to specific domains.
- `--max-tasks N`: Cap the number of tasks **per domain**.
- `--workers N`: Number of domains to run in parallel (tasks within a single domain always run sequentially so the domain's Experience Library builds in order).
- `--seed INT`: Deterministically shuffle task order within each domain.

### 4.8 Judge Deliverables (`harness2-judge`)

After `harness2` completes, grade the blind-selected deliverables. **Pass the exact same `--bench`, `--subset`, `--substrate`, `--k`, `--mode`, and `--seed` flags used during the adaptation run:**

```bash
# Score the selected refined-harness deliverables (writes judged.json):
harness2-judge --bench lab --k 1 --mode parallel

# Optional: Also score the unmodified base-harness reference runs (writes base_judged.json):
harness2-judge --bench lab --k 1 --mode parallel --bases
```

### 4.9 Generate Score Reports (`harness2-report`)

Render a formatted summary table of benchmark scores, selection provenance, fallback counts, and improver spend:

```bash
harness2-report --bench lab --k 1 --mode parallel

# Compare multiple recursion budgets side-by-side:
harness2-report --bench lab --k 1,2,3 --mode parallel
```

### 4.10 One-Command End-to-End Scripts

The `scripts/` directory provides wrapper scripts that run `harness2-check` → `harness2` → `harness2-judge` → `harness2-report` in sequence:

```bash
# LAB end-to-end on 1 task:
bash scripts/run_lab.sh --only-domains antitrust-competition --max-tasks 1

# JobBench end-to-end with k=2 sequential recursion:
K=2 MODE=sequential bash scripts/run_jobbench.sh --max-tasks 1

# WorkBuddy-Bench (web subset) end-to-end:
SUBSET=web bash scripts/run_workbuddy.sh --max-tasks 1
```

---

## 5. Editable Harness Surface (`c1..c8`)

During adaptation, the Harness² improver proposes edits to an 8-component tree (`c1..c8`), defined in [`harness2/core/tree.py`](harness2/core/tree.py):

| Component | Role | OpenCode Path (`--substrate oc`) | Codex Path (`--substrate cx`) |
|---|---|---|---|
| **c1: System Prompt** | Core agent role & instructions | `systemprompt.md` | `AGENTS.md` |
| **c2: Guardrails** | Verification rules & constraints | `guardrails.md` | `AGENTS.md` |
| **c3: Memory** | Persistent domain/task facts | `LongTermMEMORY.md` | `AGENTS.md` |
| **c4: Tool Guidance** | How/when to invoke tools | `tool_descriptions/tool_guidance.md` | `AGENTS.md` |
| **c5: Subagents** | Delegated specialist agents | `sub_agents/<name>/AGENT.md` | `sub_agents/<name>/AGENT.md` |
| **c6: Skills** | On-demand workflows & scripts | `skills/<name>/SKILL.md` (+ `scripts/`) | `.agents/skills/<name>/SKILL.md` |
| **c7: Scripts** | Deterministic Python helpers | `scripts/<name>.py` | `scripts/<name>.py` |
| **c8: Plugins / Hooks** | In-loop middleware enforcement | `plugin/<name>.ts` | `.codex/hooks.json` |

---

## 6. Output Structure, Resuming Runs, and Troubleshooting

### Output Directory Layout (`runs/`)

```text
runs/
├── demo/                          # Output from `harness2-demo`
└── lab/                           # Output for LAB (or `jb/`, `wb/<subset>/`)
    ├── adapt/
    │   ├── _audit/                # Raw improver prompt/reply audit logs
    │   ├── _sweeps/               # Sweep execution records (<namespace>-<timestamp>.json)
    │   └── lab-oc-agg1/           # Namespace directory (<bench>-<substrate>-<mode><k>)
    │       ├── config.json        # Locked experiment identity (models, split, tasks, seed)
    │       ├── judged.json        # Cached grader scores for selected deliverables
    │       ├── base_judged.json   # Cached grader scores for base harness (--bases)
    │       └── <task_id>/
    │           ├── summary.json   # Checkpoint of stages, selections, and spend
    │           ├── harnesses/     # Proposed & composed harness trees (inv*, dom*, c*)
    │           ├── context/       # Evidence bundles shown to the improver
    │           └── reflection/    # Post-task reflection inputs & adoption record
    └── library/                   # Persistent Experience Library across tasks in a domain
        └── lab-k1-oc/
            └── agg/
                └── <domain>/
                    ├── EXPERIENCE.md
                    └── harnesses/<task_id>/
```

### Resuming & Starting New Experiments

- **Resume an interrupted run**: Simply re-run the exact same `harness2` command. Completed tasks with intact adopted harnesses and deliverables are automatically skipped.
- **Change models, splits, or task filters**: Harness² locks the experiment parameters in `<namespace>/config.json` to prevent accidentally mixing different models or task sets in the same run directory. When changing models or task selection, set a new `HARNESS2_RUNS_DIR`:
  ```bash
  export HARNESS2_RUNS_DIR=runs/experiment-2
  ```

### Troubleshooting Common Issues

1. **`gcloud: FileNotFoundError` during `harness2-check`**:
   - Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) and ensure `gcloud` is on your `PATH`, then run `gcloud auth application-default login`.
2. **`This run directory belongs to different models or tasks`**:
   - You changed `.env` models or `--only-domains`/`--max-tasks` while pointing at an existing `HARNESS2_RUNS_DIR`. Set `export HARNESS2_RUNS_DIR=runs/<new-name>`.
3. **Judge fails with Vertex `429 RESOURCE_EXHAUSTED`**:
   - Failed judge calls are recorded as `ungraded` (never as a `0` score). Wait for quota recovery and re-run `harness2-judge`; already-graded tasks are preserved and only ungraded tasks are re-scored.
4. **Fair Evaluation & Web Access**:
   - Benchmark rubrics (such as JobBench's `RUBRICS.json` on Hugging Face) are publicly accessible on the internet. After running `harness2-setup`, block executor egress to `huggingface.co`, `hf.co`, `*.hf.co`, `github.com`, and `raw.githubusercontent.com` during official evaluations so agents cannot look up grading rubrics online.
