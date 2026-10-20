---
name: harness2
description: >-
  Use this skill when the user asks to run Harness² experiments, optimize or refine an agent's
  harness (prompts, guardrails, memory, skills, subagents, scripts, hooks) using recursive
  Propose-Probe-Compose and an Experience Library, configure Harness² models/benchmarks, or
  export an adopted Harness² configuration into an Antigravity (agy) workspace.
---

# Harness² Recursive Agent Harnessing Skill

This skill integrates **Harness²** (`/home/meldude/harness2`) into Antigravity (`agy`), enabling you to:
1. Run and manage Harness² benchmark sweeps (`lab`, `jb`, `wb`) and local demos using local inference (`192.168.9.33:8080`), `agy_cli`, or Vertex AI.
2. Execute the **Harness² Propose–Probe–Compose** recursive self-improvement loop natively inside `agy` on any workspace or coding task using `invoke_subagent`.
3. Export adopted Harness² component trees (`c1..c8`) and `EXPERIENCE.md` lessons directly into any `agy` workspace (`AGENTS.md`, `.agents/skills/`, `scripts/`).

---

## Workflow 1: Running Harness² CLI Commands

Always activate the `/home/meldude/harness2/.venv` environment and include `~/.local/bin` on `PATH`:

```bash
cd /home/meldude/harness2
export PATH="/home/meldude/harness2/.venv/bin:/home/meldude/.local/bin:$PATH"
```

### 1. Verify Readiness
```bash
harness2-check --bench lab
```

### 2. Preview Task Selection (`--dry-run`)
```bash
harness2 --bench lab --k 1 --mode parallel \
  --only-domains antitrust-competition --max-tasks 1 --dry-run
```

### 3. Run Recursive Adaptation Sweep (`harness2`)
On the single local inference server (`192.168.9.33:8080`), use `--workers 1` and start with `--k 1`:
```bash
harness2 --bench lab --k 1 --mode parallel \
  --only-domains antitrust-competition --max-tasks 1 --workers 1
```
- To use **`agy` itself as the Improver** (`HARNESS2_PROPOSER_CHANNEL=agy_cli`), copy `configs/agy-improver.env` to `.env`.

### 4. Judge & Report
```bash
harness2-judge --bench lab --k 1 --mode parallel
harness2-judge --bench lab --k 1 --mode parallel --bases
harness2-report --bench lab --k 1 --mode parallel
```

---

## Workflow 2: Exporting a Refined Harness² Tree into an `agy` Workspace

To apply an adopted Harness² harness (`c1..c8`) and domain `EXPERIENCE.md` to any project so `agy` uses those rules, skills, and scripts automatically, run [export_to_agy.py](/home/meldude/harness2/scripts/export_to_agy.py):

```bash
/home/meldude/harness2/.venv/bin/python /home/meldude/harness2/scripts/export_to_agy.py \
  --harness-dir /home/meldude/harness2/runs/<bench>/adapt/<namespace>/<task_id>/harnesses/<chosen_label> \
  --experience /home/meldude/harness2/runs/<bench>/library/<lib_ns>/<mode>/<domain>/EXPERIENCE.md \
  --target-dir /path/to/target/workspace
```

**Validation Step**: Run with `--dry-run` first to verify which `AGENTS.md`, `.agents/skills/*/SKILL.md`, `.agents/rules/harness2-experience.md`, and `scripts/*.py` files will be written.

---

## Workflow 3: Running Native Propose–Probe–Compose Inside `agy` on Any Task

When the user asks you to use **Harness² methodology** to solve or optimize a task directly inside an `agy` workspace:

1. **Base Rollout (`base1`)**:
   - Inspect the current workspace harness (`AGENTS.md`, `.agents/skills/`, `scripts/`, `.agents/rules/harness2-experience.md`).
   - Run a subagent (`invoke_subagent` with `Workspace="branch"` or `"inherit"`) on the task to observe the baseline trajectory and output.
2. **Contrastive Proposal (`inv1` & `dom1`)**:
   - Analyze failure modes, wasted tool turns, or missing verification in `base1` (without leaking any hidden test answers).
   - Propose two targeted harness refinements:
     - **Invariant (`inv1`)**: General verification guardrails or deterministic helper scripts in `scripts/<helper>.py`.
     - **Domain (`dom1`)**: Domain-specific workflow instructions in `AGENTS.md` or `.agents/skills/<domain>/SKILL.md`.
3. **Probe & Compose**:
   - Probe the candidate edits and compose the strongest instructions, scripts, and skills into the workspace's `AGENTS.md`, `.agents/skills/`, and `scripts/`.
4. **Experience Reflection**:
   - Append concise, evidence-backed lessons (`What failed -> What harness edit fixed it -> Evidence`) to `.agents/rules/harness2-experience.md` so future tasks in the workspace inherit the improvement.

---

## References
- Full Configuration & Usage Guide: [CONFIGURATION_AND_USAGE.md](/home/meldude/harness2/CONFIGURATION_AND_USAGE.md)
- Harness² Core Spec & Channels: [spec.py](/home/meldude/harness2/harness2/core/spec.py)
