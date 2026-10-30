---
name: codebase-manifest
description: Generate, inspect, or selectively refresh feature-first architecture documents from repository source. Use when asked for a codebase manifest, architecture map, feature catalog, flows, or documentation updates.
---

# Codebase-Manifest (Claude Code entry point)

The **single source of truth** for this skill is `../../../.agents/skills/codebase-manifest/SKILL.md`, relative to this file (the Codebase-Manifest project root contains both `.claude/` and `.agents/`).

**Read and follow that canonical SKILL.md in full**, then load its `references/output-contract.md` and optionally run its `scripts/validate_docs.py`. Use Claude Code's own file/search tools; do not invoke the project's remote Copilot CLI.

To use this skill in **another repository**, run `python scripts/install_skill.py --target /path/to/repository --agent claude` from the Codebase-Manifest source repository. The installer copies the complete portable skill into the target's `.claude/skills/`; this small source-repo adapter is not the distributable skill.
