#!/usr/bin/env python3
"""Validate Codebase-Manifest Markdown structure and referenced source paths.

Uses only Python's standard library. This is a structural check, NOT proof that
claims in the generated documents match runtime behavior.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OVERVIEWS = (
    "PROJECT_SUMMARY.md",
    "HIGH_LEVEL_ARCHITECTURE.md",
    "FEATURE_CATALOG.md",
)
DETAIL_SECTIONS = (
    "## Overview",
    "## Cross-Feature Coupling",
    "## Database Schema & Relationships",
)
COUPLING_HEADINGS = (
    "### Outbound Dependencies (this feature calls INTO other features)",
    "### Inbound Dependencies (other features call INTO this feature)",
    "### Hidden Side Effects",
    "### Events Published",
    "### Events Consumed",
    "### Files Touched by Cross-Feature Coupling",
)
SCHEMA_HEADINGS = (
    "### Persistence Conventions",
    "### Models Involved in This Feature",
)
ARCH_HEADINGS = (
    "## 2. High-Level Architecture",
    "### Topology Map",
    "### Architecture Boundaries",
    "### Dependency Composition & Wiring",
    "### Executable Entry Points",
)
TOPOLOGY_LABELS = (
    "Clients / External Actors",
    "Ingress Interfaces",
    "Runtime Processes",
    "Application Boundaries",
    "Specialized Runtime Subsystem",
    "Async / Realtime Paths",
    "Stateful / External Systems",
)


def slug(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", key).strip("_")


def headings_in_order(content: str, headings: tuple[str, ...]) -> bool:
    cursor = 0
    for heading in headings:
        match = re.search(r"^" + re.escape(heading) + r"\s*$", content[cursor:], re.M)
        if not match:
            return False
        cursor += match.end()
    return True


def check(root: Path, *, overview_only: bool = False) -> list[str]:
    problems: list[str] = []
    root = root.resolve()
    arch = root / ".architectureY"
    if not arch.is_dir() or not arch.resolve().is_relative_to(root):
        return ["Missing or unsafe .architectureY/ directory"]

    docs: dict[str, str] = {}
    for name in (*OVERVIEWS, "01_GENERAL_ARCHITECTURE.md"):
        path = arch / name
        if not path.is_file() or not path.resolve().is_relative_to(arch.resolve()):
            problems.append(f"Missing or unsafe document: {name}")
        else:
            docs[name] = path.read_text(encoding="utf-8")

    if "PROJECT_SUMMARY.md" in docs:
        summary = docs["PROJECT_SUMMARY.md"]
        if not re.search(r"^# .+ — General Architecture & Feature Overview$", summary, re.M) or not headings_in_order(summary, ("## 1. Project Summary",)):
            problems.append("PROJECT_SUMMARY.md: missing required title or heading")
    if "HIGH_LEVEL_ARCHITECTURE.md" in docs:
        architecture = docs["HIGH_LEVEL_ARCHITECTURE.md"]
        if not headings_in_order(architecture, ARCH_HEADINGS):
            problems.append("HIGH_LEVEL_ARCHITECTURE.md: missing or out-of-order headings")
        if any(f"[{label}:" not in architecture for label in TOPOLOGY_LABELS):
            problems.append("HIGH_LEVEL_ARCHITECTURE.md: incomplete topology labels")
    if all(name in docs for name in OVERVIEWS) and "01_GENERAL_ARCHITECTURE.md" in docs:
        def normalize(s: str) -> str:
            return re.sub(r"\n{3,}", "\n\n", s.replace("\r\n", "\n").strip())
        expected = "\n\n".join(docs[name].strip() for name in OVERVIEWS)
        if normalize(docs["01_GENERAL_ARCHITECTURE.md"]) != normalize(expected):
            problems.append("01_GENERAL_ARCHITECTURE.md: does not match assembled overview sources")

    catalog = docs.get("FEATURE_CATALOG.md")
    if catalog is None:
        return problems
    if not headings_in_order(catalog, ("## 3. Feature Catalog", "### Frozen Feature Manifest", "### Feature Details")):
        problems.append("FEATURE_CATALOG.md: missing or out-of-order headings")
    manifest_match = re.search(r"^### Frozen Feature Manifest\s*$([\s\S]*?)^### Feature Details\s*$", catalog, re.M)
    features: list[tuple[int, str]] = []
    if not manifest_match:
        problems.append("FEATURE_CATALOG.md: cannot parse frozen feature manifest")
        return problems
    table = manifest_match.group(1)
    if not re.search(r"^\|\s*Feature Key\s*\|\s*Dominant Root\s*\|\s*Standalone Reason\s*\|\s*Merged Boundaries\s*\|", table, re.M):
        problems.append("FEATURE_CATALOG.md: manifest table headers differ from contract")

    for line in table.splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) != 4 or parts[0] == "Feature Key" or re.fullmatch(r"[-: ]+", parts[0]):
            continue
        key = parts[0]
        if not key:
            problems.append("FEATURE_CATALOG.md: empty feature key")
            continue
        features.append((len(features) + 1, key))

    declared = [(int(num), name.strip()) for num, name in re.findall(r"^### Feature (\d+):\s*(.+?)\s*$", catalog, re.M)]
    if [key for _, key in declared] != [key for _, key in features]:
        problems.append("FEATURE_CATALOG.md: feature table and detail entries disagree")
    if len(set(k for _, k in declared)) != len(declared) or len(set(n for n, _ in declared)) != len(declared):
        problems.append("FEATURE_CATALOG.md: repeated feature number or key")
    if any(num < 1 for num, _ in declared):
        problems.append("FEATURE_CATALOG.md: invalid feature number")

    if overview_only:
        return problems
    for number, key in declared:
        filename = f"{number:02d}_{slug(key)}.md"
        file = arch / filename
        if not slug(key) or not file.is_file() or not file.resolve().is_relative_to(arch.resolve()):
            problems.append(f"Missing or unsafe feature detail: {filename}")
            continue
        body = file.read_text(encoding="utf-8")
        expected_title = f"# Feature {number}: {key} -- Flows & Key Files"
        if not body.startswith(expected_title + "\n"):
            problems.append(f"{filename}: incorrect title")
        if not headings_in_order(body, DETAIL_SECTIONS):
            problems.append(f"{filename}: missing or out-of-order main sections")
        if not headings_in_order(body, COUPLING_HEADINGS):
            problems.append(f"{filename}: incomplete coupling structure")
        if not headings_in_order(body, SCHEMA_HEADINGS):
            problems.append(f"{filename}: incomplete schema structure")
        for src in re.findall(r"^\s+->\s+(.+?):\s+[^\n]+$", body, re.M):
            verify_source(root, src, filename, problems)
        for src in re.findall(r"^file:\s+([^\n]+)$", body, re.M):
            verify_source(root, src.strip(), filename, problems)

    return problems


def verify_source(root: Path, value: str, document: str, problems: list[str]) -> None:
    rel = Path(value.strip())
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        problems.append(f"{document}: unsafe source path {value!r}")
        return
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        problems.append(f"{document}: missing source path {value!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="target repository root")
    parser.add_argument("--overview-only", action="store_true")
    args = parser.parse_args(argv)
    failures = check(args.root, overview_only=args.overview_only)
    for failure in failures:
        print("FAIL:", failure, file=sys.stderr)
    if failures:
        print(f"{len(failures)} validation issue(s).", file=sys.stderr)
        return 1
    print("PASS: Codebase-Manifest structure and referenced paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
