# Codebase-Manifest

**Feature-first architecture documentation for AI coding agents.**

Coding agents shouldn't have to rediscover a repository every time they make a change. **Codebase-Manifest** turns source code into a predictable set of Markdown documents that explain **what each feature does, where it lives, and how it connects to the rest of the system**.

Unlike a repository-to-text dump, it focuses on navigable architecture and code-backed execution flows.

## What you get

- **Consistent structure** — project summary, architecture map, feature catalog, and per-feature deep dives.
- **Traceable workflows** — entry points, source files, and function-level execution paths.
- **Change context** — cross-feature dependencies, events, side effects, and relevant data models.
- **Agent-ready Markdown** — documentation stored alongside your code, easy to read, review, and version.

```text
.architectureY/
├── PROJECT_SUMMARY.md
├── HIGH_LEVEL_ARCHITECTURE.md
├── FEATURE_CATALOG.md
├── 01_GENERAL_ARCHITECTURE.md
└── NN_<Feature_Key>.md       # One deep dive per feature
```

## Quick start — Agent Skill (Claude Code, Codex, Gemini CLI)

The [portable Agent Skill](.agents/skills/codebase-manifest/SKILL.md) uses your active agent's filesystem tools; **no remote Copilot VM is required**.

```bash
git clone https://github.com/MohammadAsadolahi/Codebase-Manifest.git
cd Codebase-Manifest
python scripts/install_skill.py --target /path/to/repository --agent all
```

This installs complete copies under `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex and Gemini CLI). Use `--agent claude`, `codex`, or `gemini` for a single target. In Claude Code invoke `/codebase-manifest`; in Codex mention `$codebase-manifest`.

**Inspect a task (read-only):** Ask your agent to use Codebase-Manifest to `inspect where login failures are handled`. It returns a focused reading order and verified source flow, without generating docs or changing code. Existing `.architectureY/` docs are optional for inspection.

**Generate or refresh:** Ask your agent to `generate` the architecture docs, or `refresh` a named feature. Generation writes the structure above; refresh is guided by the agent, not automatic incremental tracking.

## Remote CLI (optional)

**Requirements:** Python 3.10+, SSH and rsync, and an authenticated GitHub Copilot CLI on a trusted, isolated remote machine.

```bash
python -m pip install -e .
export DOCER_SSH_HOST="user@your-vm"
export DOCER_REMOTE_WORKDIR="/home/user/docer_work"
raw-docer generate /path/to/your/repository
```

The CLI uploads the repository, uses remote Copilot to analyze it, and downloads the documents. Use `--skip-features` for overview docs only. The remote runner is less restricted than the portable skill; review the security warning below before using it.

**For coding agents:** Start with `01_GENERAL_ARCHITECTURE.md`, find the feature in `FEATURE_CATALOG.md`, then verify documented flows against the source.

## Current status

**Available now:** Feature-level documentation generation, guided selective refresh, and read-only task-scoped source inspection via the portable skill.

**Next:** Stable feature identities, machine-validated document schemas, and **incremental updates** that regenerate only affected sections. These are planned—not implemented yet. Current runs regenerate the documentation, and feature names or numbers may change.

> **Security:** Source code is uploaded to your configured VM. The current runner grants Copilot broad tool access, disables SSH host-key checking, and does not reliably exclude secrets such as `.env` files. Use a trusted, isolated environment and review what you upload.

---

**The goal:** Give every coding agent the same reliable map of your codebase.
