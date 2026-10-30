#!/usr/bin/env python3
"""Install the portable Codebase-Manifest skill into another repository.

Claude: .claude/skills; Codex & Gemini CLI: .agents/skills.
Other agents accepting the Agent Skills format can use the same skill directory.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "codebase-manifest"


def destinations(root: Path, agent: str) -> list[Path]:
    claude = root / ".claude" / "skills" / "codebase-manifest"
    shared = root / ".agents" / "skills" / "codebase-manifest"
    if agent == "claude":
        return [claude]
    if agent in ("codex", "gemini"):
        return [shared]
    return [claude, shared]


def install(target: Path, agent: str, *, force: bool = False) -> list[str]:
    target = target.resolve()
    if not target.is_dir():
        raise ValueError(f"Target directory does not exist: {target}")
    if not (SOURCE / "SKILL.md").is_file():
        raise ValueError(f"Missing canonical skill: {SOURCE}")
    dests = destinations(target, agent)
    for dst in dests:
        if dst.is_symlink():
            raise ValueError(f"Refusing to replace a symlink: {dst}")
        if dst.resolve() == SOURCE.resolve():
            continue
        if dst.exists() and not force:
            raise ValueError(f"Already exists: {dst} (use --force to replace)")
        if dst.exists() and not dst.is_dir():
            raise ValueError(f"Not a directory: {dst}")
    results: list[str] = []
    for dst in dests:
        if dst.resolve() == SOURCE.resolve():
            results.append(f"Already canonical: {dst}")
            continue
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SOURCE, dst)
        results.append(f"Installed: {dst}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True, help="existing target repo root")
    parser.add_argument("--agent", choices=("claude", "codex", "gemini", "all"), default="all")
    parser.add_argument("--force", action="store_true", help="replace an existing installed skill")
    args = parser.parse_args(argv)
    try:
        print("\n".join(install(args.target, args.agent, force=args.force)))
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
