#!/usr/bin/env python3
"""Export an adopted Harness² tree (or Experience Library entry) into an Antigravity (agy) workspace.

Maps Harness²'s 8 editable components (c1..c8) directly onto Antigravity's native customization
surface:
  - c1 (systemprompt.md), c2 (guardrails.md), c3 (LongTermMEMORY.md), c4 (tool_guidance.md)
    or AGENTS.md  -->  <target>/AGENTS.md (respecting Antigravity's 24,000-byte per-file rule cap)
  - c5 (sub_agents/<name>/AGENT.md)  -->  <target>/.agents/skills/subagent-<name>/SKILL.md
  - c6 (skills/<name>/SKILL.md or .agents/skills/<name>/SKILL.md)  -->  <target>/.agents/skills/<name>/SKILL.md
  - c7 (scripts/<name>.py)  -->  <target>/scripts/<name>.py
  - Experience Library (EXPERIENCE.md)  -->  <target>/.agents/rules/harness2-experience.md

Usage:
  python scripts/export_to_agy.py \
      --harness-dir runs/demo/runs/demo-oc-agg2/ledger-1/harnesses/agg1 \
      --experience runs/demo/library/k2/agg/accounting/EXPERIENCE.md \
      --target-dir /path/to/your/project
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

AGY_RULE_MAX_BYTES = 24_000

OC_SECTIONS = (
    ("systemprompt.md", "System Instructions (c1)"),
    ("guardrails.md", "Guardrails & Verification (c2)"),
    ("LongTermMEMORY.md", "Long-Term Memory (c3)"),
    ("tool_descriptions/tool_guidance.md", "Tool Guidance (c4)"),
)


def compose_agents_md(harness_dir: Path) -> str:
    """Compose AGENTS.md from either an OpenCode tree or a Codex tree."""
    agents_file = harness_dir / "AGENTS.md"
    if agents_file.is_file():
        body = agents_file.read_text(encoding="utf-8").strip()
    else:
        parts = ["# Workspace Agent Harness (Exported from Harness²)"]
        for rel, title in OC_SECTIONS:
            p = harness_dir / rel
            if p.is_file():
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    parts.append(f"## {title}\n\n{text}")
        body = "\n\n".join(parts)
    encoded = body.encode("utf-8")
    if len(encoded) > AGY_RULE_MAX_BYTES:
        # Truncate cleanly on a line boundary under Antigravity's 24 KB rule limit
        truncated = encoded[: AGY_RULE_MAX_BYTES - 120].decode("utf-8", errors="ignore")
        body = truncated.rsplit("\n", 1)[0] + "\n\n<!-- Truncated to 24KB agy rule limit -->\n"
    return body + ("\n" if not body.endswith("\n") else "")


def export_harness(
    harness_dir: Path,
    target_dir: Path,
    *,
    experience_path: Path | None = None,
    dry_run: bool = False,
) -> list[Path]:
    written: list[Path] = []
    if not harness_dir.is_dir():
        raise FileNotFoundError(f"Harness directory not found: {harness_dir}")

    # 1. Always-on Rules -> AGENTS.md
    agents_md = compose_agents_md(harness_dir)
    dest_agents = target_dir / "AGENTS.md"
    written.append(dest_agents)
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_agents.write_text(agents_md, encoding="utf-8")

    # 2. Skills (c6) -> .agents/skills/<name>/
    for skill_root in (harness_dir / "skills", harness_dir / ".agents" / "skills"):
        if skill_root.is_dir():
            for skill_md in sorted(skill_root.glob("*/SKILL.md")):
                skill_name = skill_md.parent.name
                dest_skill_dir = target_dir / ".agents" / "skills" / skill_name
                written.append(dest_skill_dir / "SKILL.md")
                if not dry_run:
                    shutil.copytree(skill_md.parent, dest_skill_dir, dirs_exist_ok=True)

    # 3. Subagents (c5) -> .agents/skills/subagent-<name>/SKILL.md
    subagents_root = harness_dir / "sub_agents"
    if subagents_root.is_dir():
        for agent_md in sorted(subagents_root.glob("*/AGENT.md")):
            name = agent_md.parent.name
            dest_skill = target_dir / ".agents" / "skills" / f"subagent-{name}" / "SKILL.md"
            written.append(dest_skill)
            if not dry_run:
                dest_skill.parent.mkdir(parents=True, exist_ok=True)
                raw = agent_md.read_text(encoding="utf-8")
                if raw.startswith("---"):
                    _, fm, body = raw.split("---", 2)
                    if "name:" not in fm:
                        fm = f"\nname: subagent-{name}" + fm
                    content = f"---{fm}---\n{body}"
                else:
                    content = (
                        f"---\nname: subagent-{name}\n"
                        f"description: Delegated specialist workflow for {name}\n---\n\n{raw}"
                    )
                dest_skill.write_text(content, encoding="utf-8")

    # 4. Deterministic Python helper scripts (c7) -> scripts/<name>.py
    scripts_root = harness_dir / "scripts"
    if scripts_root.is_dir():
        for py_file in sorted(scripts_root.glob("*.py")):
            dest_py = target_dir / "scripts" / py_file.name
            written.append(dest_py)
            if not dry_run:
                dest_py.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, dest_py)

    # 5. Optional Experience Library (EXPERIENCE.md) -> .agents/rules/harness2-experience.md
    if experience_path and experience_path.is_file():
        dest_exp = target_dir / ".agents" / "rules" / "harness2-experience.md"
        written.append(dest_exp)
        if not dry_run:
            dest_exp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(experience_path, dest_exp)

    return written


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--harness-dir",
        type=Path,
        required=True,
        help="Path to a Harness² tree directory (e.g. runs/.../harnesses/agg1)",
    )
    p.add_argument(
        "--target-dir",
        type=Path,
        required=True,
        help="Target Antigravity (agy) project root directory",
    )
    p.add_argument(
        "--experience",
        type=Path,
        default=None,
        help="Optional path to an EXPERIENCE.md file from a Harness² library",
    )
    p.add_argument("--dry-run", action="store_true", help="Preview files without writing")
    args = p.parse_args(argv)

    written = export_harness(
        args.harness_dir.expanduser().resolve(),
        args.target_dir.expanduser().resolve(),
        experience_path=args.experience.expanduser().resolve() if args.experience else None,
        dry_run=args.dry_run,
    )
    prefix = "[DRY-RUN] Would write" if args.dry_run else "Exported to agy workspace"
    for path in written:
        print(f"{prefix}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
