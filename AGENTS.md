# Harness² Workspace Rules (Antigravity / `agy`)

This workspace hosts **Harness²** (`google-research/harness2`), configured for both local OpenAI-compatible inference (`http://192.168.9.33:8080/v1`, model `huihui-qwen3.8-flash-next-iq3_s`), Antigravity (`agy_cli`), and Vertex AI presets.

## Environment & Execution Rules

1. **Python Interpreter**: Always use `/home/meldude/harness2/.venv/bin/python` (Python 3.12) and prepend `/home/meldude/harness2/.venv/bin:/home/meldude/.local/bin` to `PATH` when invoking `harness2`, `harness2-setup`, `harness2-check`, `harness2-judge`, `harness2-report`, `harness2-demo`, or `harness2-bridge`.
2. **Configuration & Presets**:
   - Active configuration lives in `/home/meldude/harness2/.env` (git-ignored).
   - Tracked presets live in `/home/meldude/harness2/configs/`:
     - `configs/local-inference.env` (`192.168.9.33:8080` for Solver, Improver, and Judge)
     - `configs/agy-improver.env` (`192.168.9.33:8080` Solver + `agy_cli` Improver)
     - `configs/vertex-gemini.env` (Vertex AI Gemini)
     - `configs/vertex-claude-improver.env` (Vertex Gemini Solver + Claude Improver)
     - `configs/codex-bridge.env` (Codex CLI substrate via `harness2-bridge`)
   - OpenCode custom provider config lives in `configs/opencode-local.json` and `~/.config/opencode/opencode.json`.
3. **Run Isolation**: Never mix different models or task splits in the same `HARNESS2_RUNS_DIR`. Set `export HARNESS2_RUNS_DIR=runs/<new-experiment>` when changing models, splits, or task filters.
4. **Skills**: When the user asks to run Harness², optimize an agent harness using Propose–Probe–Compose, or export an adopted harness to an `agy` project, load the `harness2` skill (`.agents/skills/harness2/SKILL.md`).
