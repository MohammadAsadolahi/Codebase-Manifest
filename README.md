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

## Quick start

**Requirements:** Python 3.10+, SSH and rsync, and an authenticated GitHub Copilot CLI on a remote machine.

```bash
git clone https://github.com/MohammadAsadolahi/Codebase-Manifest.git
cd Codebase-Manifest
python -m pip install -e .

export DOCER_SSH_HOST="user@your-vm"
export DOCER_REMOTE_WORKDIR="/home/user/docer_work"
raw-docer generate /path/to/your/repository
```

The CLI syncs your repository to the remote machine, uses Copilot CLI to analyze it, and downloads the generated documentation. Use `--skip-features` for overview docs only, or `raw-docer generate --help` for all options.

**For coding agents:** Start with `01_GENERAL_ARCHITECTURE.md`, find the relevant feature in `FEATURE_CATALOG.md`, then follow its documented flows into the source code.

## Agent skill (Claude Code, Codex, Gemini CLI)

The same [portable Agent Skill](.agents/skills/codebase-manifest/SKILL.md) works across CLIs. Install it into a different repository:

```bash
python scripts/install_skill.py --target /path/to/repository --agent all
```

This installs complete copies under `.claude/skills/` (Claude Code) and `.agents/skills/` (Codex and Gemini CLI). You can choose `--agent claude`, `codex`, or `gemini`. In Claude Code invoke `/codebase-manifest`; in Codex mention `$codebase-manifest`. The skill uses the active agent's filesystem tools; **no remote Copilot VM is required for this mode**.

It generates the existing `.architectureY/` format. Selective `refresh` is guided by the agent; automatic incremental updates remain on the roadmap.

## Current status

**Available now:** Full documentation generation with fixed-format prompts and feature-level analysis.

**Next:** Stable feature identities, machine-validated document schemas, and **incremental updates** that regenerate only affected sections. These are planned—not implemented yet. Current runs regenerate the documentation, and feature names or numbers may change.

> **Security:** Source code is uploaded to your configured VM. The current runner grants Copilot broad tool access, disables SSH host-key checking, and does not reliably exclude secrets such as `.env` files. Use a trusted, isolated environment and review what you upload.

---

**The goal:** Give every coding agent the same reliable map of your codebase.
