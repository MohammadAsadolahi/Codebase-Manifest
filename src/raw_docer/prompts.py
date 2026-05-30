"""Prompt loading for raw documentation generation.

The canonical prompts live as plain text in `raw_update_generator/prompts/`
and are kept as the single source of truth. At runtime we only substitute
`.architectureX` with the configured output directory and, for the project
summary prompt, append the missing output-path contract.
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

PROJECT_SUMMARY_PROMPT_FILE = "project summary. prompt.txt"
HIGH_LEVEL_ARCHITECTURE_PROMPT_FILE = "get gist of architecture prompt.txt"
FEATURE_CATALOG_PROMPT_FILE = "feature gen prompt.txt"
IN_DEPTH_FEATURE_PROMPT_FILE = "in depth feature generation.txt"

PROJECT_SUMMARY_FILE = "PROJECT_SUMMARY.md"
HIGH_LEVEL_ARCHITECTURE_FILE = "HIGH_LEVEL_ARCHITECTURE.md"
FEATURE_CATALOG_FILE = "FEATURE_CATALOG.md"
FINAL_ARCHITECTURE_FILE = "01_GENERAL_ARCHITECTURE.md"


def _load(name: str, arch_dir: str) -> str:
    text = (PROMPTS_DIR / name).read_text(encoding="utf-8")
    return text.replace(".architectureX", arch_dir)


_PROJECT_SUMMARY_OUTPUT_FOOTER = """

---

OUTPUT REQUIREMENT (mandatory, not optional):
- Write the final Markdown document to the file `{arch_dir}/{filename}` (relative to the current working directory) using your file-write tool.
- Create the `{arch_dir}/` directory if it does not exist.
- Write ONLY that one file. Do not create README.md, SUMMARY.txt, index files, or any other side files anywhere on disk.
- Do not write to /tmp, /root, your session-state directory, or any path outside the current project directory.
- Do not delegate this task to a subagent.
- After writing, your final chat reply should be a single short confirmation line such as `Wrote {arch_dir}/{filename}`. Do not paste the document contents into chat.
"""


def project_summary_prompt(arch_dir: str) -> str:
    return _load(PROJECT_SUMMARY_PROMPT_FILE, arch_dir) + _PROJECT_SUMMARY_OUTPUT_FOOTER.format(
        arch_dir=arch_dir,
        filename=PROJECT_SUMMARY_FILE,
    )


def high_level_architecture_prompt(arch_dir: str) -> str:
    return _load(HIGH_LEVEL_ARCHITECTURE_PROMPT_FILE, arch_dir)


def feature_catalog_prompt(arch_dir: str) -> str:
    return _load(FEATURE_CATALOG_PROMPT_FILE, arch_dir)


_FEATURE_DETAIL_SCOPE_HEADER = """\
SCOPE OVERRIDE — SINGLE FEATURE MODE:
TARGET FEATURE: Feature {feature_number}: {feature_key}
OUTPUT FILE: `{output_file}`

- Read `{arch_dir}/FEATURE_CATALOG.md` and generate exactly one feature document for `Feature {feature_number}: {feature_key}`.
- Use the matching row in `### Frozen Feature Manifest` and the matching entry in `### Feature Details` as the only identity anchor.
- Write only `{output_file}`.

---

"""

_FEATURE_DETAIL_OUTPUT_FOOTER = """

---

OUTPUT REQUIREMENT (mandatory, not optional):
- Write the final Markdown document to `{output_file}` relative to the current working directory using your file-write tool.
- Create the directory if it does not exist.
- Write ONLY that one file.
- Do not write to /tmp, /root, your session-state directory, or any path outside the current project directory.
- Do not delegate this task to a subagent.
- After writing, your final chat reply should be one short confirmation line. Do not paste the document contents into chat.
"""


def feature_detail_prompt(
    arch_dir: str,
    feature_number: int,
    feature_key: str,
    output_file: str,
) -> str:
    body = _load(IN_DEPTH_FEATURE_PROMPT_FILE, arch_dir)
    header = _FEATURE_DETAIL_SCOPE_HEADER.format(
        feature_number=feature_number,
        feature_key=feature_key,
        arch_dir=arch_dir,
        output_file=output_file,
    )
    footer = _FEATURE_DETAIL_OUTPUT_FOOTER.format(output_file=output_file)
    return header + body + footer