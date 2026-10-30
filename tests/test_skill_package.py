"""Smoke tests for the portable skill installer and documentation validator."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(result)
    return result


validate = module("validate_docs", REPO / ".agents/skills/codebase-manifest/scripts/validate_docs.py")
installer = module("install_skill", REPO / "scripts/install_skill.py")


class SkillTests(unittest.TestCase):
    def test_frontmatter_and_skill_sources(self):
        skill = installer.SOURCE / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: codebase-manifest\n"))
        self.assertIn("description:", text.split("---", 2)[1])
        self.assertTrue((installer.SOURCE / "references/output-contract.md").exists())

    def test_install_copy_for_all_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            installed = installer.install(root, "all")
            self.assertEqual(len(installed), 2)
            self.assertEqual(
                (root / ".claude/skills/codebase-manifest/SKILL.md").read_bytes(),
                (root / ".agents/skills/codebase-manifest/SKILL.md").read_bytes(),
            )
            with self.assertRaises(ValueError):
                installer.install(root, "all")
            installer.install(root, "all", force=True)

    def _fixture(self, root: Path):
        arch = root / ".architectureY"
        arch.mkdir()
        (root / "src").mkdir()
        (root / "src/auth.py").write_text("def login(): pass\n", encoding="utf-8")
        summary = "# Demo — General Architecture & Feature Overview\n\n## 1. Project Summary\nDemo.\n"
        architecture = (
            "## 2. High-Level Architecture\n"
            "### Topology Map\n"
            + "\n".join(
                f"[{k}: (none)]" if i == 0 else f"  -> [{k}: (none)]"
                for i, k in enumerate(validate.TOPOLOGY_LABELS)
            )
            + "\n### Architecture Boundaries\n### Dependency Composition & Wiring\n"
            "### Executable Entry Points\n"
        )
        catalog = (
            "## 3. Feature Catalog\n"
            "### Frozen Feature Manifest\n"
            "| Feature Key | Dominant Root | Standalone Reason | Merged Boundaries |\n"
            "| --- | --- | --- | --- |\n"
            "| Auth | Auth | login | (none) |\n"
            "### Feature Details\n### Feature 1: Auth\nAuthentication is supported. Auth owns login. There are no integrations.\n"
        )
        detail = (
            "# Feature 1: Auth -- Flows & Key Files\n"
            "## Overview\nAuth. Dominant root: Auth. Integrations: none.\n"
            "## Flow 1: login\n```text\nHTTP POST /login\n  -> src/auth.py: login\n  <- response\n```\n"
            "## Cross-Feature Coupling\n"
            + "\n".join(validate.COUPLING_HEADINGS)
            + "\n## Database Schema & Relationships\n"
            + "\n".join(validate.SCHEMA_HEADINGS)
            + "\nNone.\n"
        )
        for name, content in [
            ("PROJECT_SUMMARY.md", summary),
            ("HIGH_LEVEL_ARCHITECTURE.md", architecture),
            ("FEATURE_CATALOG.md", catalog),
            ("01_GENERAL_ARCHITECTURE.md", "\n\n".join(x.strip() for x in (summary, architecture, catalog)) + "\n"),
            ("01_Auth.md", detail),
        ]:
            (arch / name).write_text(content, encoding="utf-8")

    def test_valid_then_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._fixture(root)
            self.assertEqual(validate.check(root), [])
            (root / "src/auth.py").unlink()
            self.assertTrue(any("missing source path" in e for e in validate.check(root)))

    def test_overview_only_does_not_need_feature_detail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._fixture(root)
            (root / ".architectureY/01_Auth.md").unlink()
            self.assertEqual(validate.check(root, overview_only=True), [])


if __name__ == "__main__":
    unittest.main()
