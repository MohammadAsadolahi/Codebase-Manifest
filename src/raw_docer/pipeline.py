"""Pipeline orchestrator for the three-stage architecture document flow.

Flow:
  1. rsync the local project to the VM under {remote_workdir}/{project_name}/
  2. Run three standalone Copilot prompts in sequence:
       - project summary
       - high-level architecture
       - feature catalog
  3. Concatenate those three outputs into {arch_dir}/01_GENERAL_ARCHITECTURE.md
  4. rsync {arch_dir}/ back to the local project
"""

from __future__ import annotations

import logging
import re
import shlex
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from raw_docer.config import Settings
from raw_docer.copilot_runner import CopilotRunner, CopilotRunnerConfig
from raw_docer.prompts import (
    FEATURE_CATALOG_FILE,
    FINAL_ARCHITECTURE_FILE,
    HIGH_LEVEL_ARCHITECTURE_FILE,
    PROJECT_SUMMARY_FILE,
    feature_catalog_prompt,
    feature_detail_prompt,
    high_level_architecture_prompt,
    project_summary_prompt,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StageSpec:
    key: str
    title: str
    filename: str
    prompt_builder: Callable[[str], str]


STANDALONE_STAGES: tuple[StageSpec, ...] = (
    StageSpec(
        key="project_summary",
        title="Project Summary",
        filename=PROJECT_SUMMARY_FILE,
        prompt_builder=project_summary_prompt,
    ),
    StageSpec(
        key="high_level_architecture",
        title="High-Level Architecture",
        filename=HIGH_LEVEL_ARCHITECTURE_FILE,
        prompt_builder=high_level_architecture_prompt,
    ),
    StageSpec(
        key="feature_catalog",
        title="Feature Catalog",
        filename=FEATURE_CATALOG_FILE,
        prompt_builder=feature_catalog_prompt,
    ),
)


class RawPipeline:
    def __init__(self, settings: Settings, project_path: str):
        self.settings = settings
        self.project_path = Path(project_path).resolve()
        self.arch_dir_rel = settings.architecture_dir
        self.local_arch_dir = self.project_path / self.arch_dir_rel

        runner_cfg = CopilotRunnerConfig(
            ssh_host=settings.ssh_host,
            remote_workdir=settings.remote_workdir,
            model=settings.copilot_model or None,
            reasoning_effort=settings.copilot_reasoning_effort or None,
        )
        self.runner = CopilotRunner(runner_cfg)

    def run(self, *, force: bool = False, dry_run: bool = False, skip_upload: bool = False, skip_features: bool = False) -> dict:
        stats: dict = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "project": str(self.project_path),
            "stages": {},
            "errors": [],
        }

        try:
            if not self.project_path.exists():
                raise RuntimeError(f"project path does not exist: {self.project_path}")

            project_name = self.project_path.name
            remote_path = self.runner.remote_project_path(project_name)

            if skip_upload:
                logger.info("Skipping project upload (--skip-upload). Assuming %s exists.", remote_path)
            else:
                logger.info("Uploading project to VM…")
                remote_path = self.runner.sync_up(
                    self.project_path, project_name, clean_remote=force,
                )

            self._reset_remote_arch_dir(remote_path)

            if dry_run:
                stats["dry_run"] = True
                logger.info("[dry-run] would run Copilot CLI against %s", remote_path)
                return stats

            generated_files: list[str] = []
            for stage_index, stage in enumerate(STANDALONE_STAGES, start=1):
                logger.info("=" * 60)
                logger.info("STAGE %d: %s", stage_index, stage.title)
                logger.info("=" * 60)
                self.runner.run_copilot(
                    remote_path,
                    stage.prompt_builder(self.arch_dir_rel),
                    log_name=f"stage{stage_index}_{stage.key}",
                )

                generated_files.append(stage.filename)
                self._cleanup_remote_arch_dir(remote_path, generated_files)

                proc = self._verify_remote_file(remote_path, stage.filename)
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Stage {stage_index} failed: {stage.filename} was not created on remote."
                    )

                stats["stages"][stage.key] = proc.stdout.strip()
                logger.info("Stage %d OK: %s", stage_index, proc.stdout.strip())

            logger.info("=" * 60)
            logger.info("FINAL ASSEMBLY: Combined Architecture Document")
            logger.info("=" * 60)
            self._append_remote_documents(
                remote_path,
                [stage.filename for stage in STANDALONE_STAGES],
                FINAL_ARCHITECTURE_FILE,
            )

            generated_files.append(FINAL_ARCHITECTURE_FILE)
            self._cleanup_remote_arch_dir(remote_path, generated_files)

            proc = self._verify_remote_file(remote_path, FINAL_ARCHITECTURE_FILE)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Final assembly failed: {FINAL_ARCHITECTURE_FILE} was not created on remote."
                )

            stats["stages"]["final_document"] = proc.stdout.strip()
            logger.info("Final assembly OK: %s", proc.stdout.strip())

            # ── Per-feature in-depth generation ────────────────────────
            if skip_features:
                logger.info("Skipping per-feature generation (--skip-features).")
            else:
                feature_files = self._run_feature_details(
                    remote_path, generated_files, stats,
                )
                generated_files.extend(feature_files)

            logger.info("Downloading %s/ from remote…", self.arch_dir_rel)
            if self.local_arch_dir.exists():
                backup = self.local_arch_dir.with_suffix(".bak")
                if backup.exists():
                    shutil.rmtree(backup)
                shutil.move(str(self.local_arch_dir), str(backup))
                logger.info("Existing %s moved to %s", self.local_arch_dir, backup)

            self.runner.sync_down(f"{remote_path}/{self.arch_dir_rel}", self.local_arch_dir)
            stats["local_arch_dir"] = str(self.local_arch_dir)
            logger.info("Pipeline completed successfully.")

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            stats["errors"].append(str(e))

        stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        return stats

    def _reset_remote_arch_dir(self, remote_path: str) -> None:
        remote_dir = self._remote_arch_dir(remote_path)
        self.runner.ssh_exec(f"rm -rf {shlex.quote(remote_dir)}")

    def _verify_remote_file(self, remote_path: str, filename: str):
        remote_file = f"{self._remote_arch_dir(remote_path)}/{filename}"
        return self.runner.ssh_exec(
            f"test -f {shlex.quote(remote_file)} && wc -c {shlex.quote(remote_file)}",
            check=False,
        )

    def _append_remote_documents(
        self,
        remote_path: str,
        source_files: list[str],
        output_file: str,
    ) -> None:
        remote_dir = self._remote_arch_dir(remote_path)
        cmd_parts = [
            "set -e",
            f"d={shlex.quote(remote_dir)}",
            'out="$d/' + output_file + '"',
            'cat "$d/' + source_files[0] + '" > "$out"',
        ]
        for filename in source_files[1:]:
            cmd_parts.append('printf "\\n\\n" >> "$out"')
            cmd_parts.append('cat "$d/' + filename + '" >> "$out"')
        self.runner.ssh_exec("; ".join(cmd_parts))

    def _cleanup_remote_arch_dir(self, remote_path: str, keep_files: list[str]) -> None:
        remote_dir = self._remote_arch_dir(remote_path)
        filters = " ".join(
            f"! -name {shlex.quote(name)}" for name in keep_files
        )
        cmd = (
            f"set -e; "
            f"d={shlex.quote(remote_dir)}; "
            f"if [ -d \"$d\" ]; then "
            f"  find \"$d\" -mindepth 1 -maxdepth 1 {filters} "
            f"    -print -exec rm -rf {{}} +; "
            f"fi"
        )
        proc = self.runner.ssh_exec(cmd, check=False)
        if proc.stdout.strip():
            logger.info("Cleanup removed:\n%s", proc.stdout.strip())

    def _remote_arch_dir(self, remote_path: str) -> str:
        return f"{remote_path}/{self.arch_dir_rel}"

    # ── Per-feature in-depth generation ────────────────────────────────

    _FEATURE_HEADING_RE = re.compile(r"^#{2,4}\s+Feature\s+(\d+):\s+(.+)$")

    def _parse_feature_catalog(self, remote_path: str) -> list[tuple[int, str]]:
        """Read FEATURE_CATALOG.md from the remote and extract (number, key) pairs."""
        remote_file = f"{self._remote_arch_dir(remote_path)}/{FEATURE_CATALOG_FILE}"
        proc = self.runner.ssh_exec(
            f"cat {shlex.quote(remote_file)}", stream=False, check=True,
        )
        features: list[tuple[int, str]] = []
        for line in proc.stdout.splitlines():
            m = self._FEATURE_HEADING_RE.match(line.strip())
            if m:
                features.append((int(m.group(1)), m.group(2).strip()))
        if not features:
            raise RuntimeError(
                f"No features found in {remote_file}. "
                "Expected headings like '### Feature N: Key'."
            )
        features.sort(key=lambda t: t[0])
        return features

    @staticmethod
    def _feature_output_filename(feature_number: int, feature_key: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", feature_key).strip("_")
        return f"{feature_number:02d}_{slug}.md"

    def _run_feature_details(
        self,
        remote_path: str,
        generated_files: list[str],
        stats: dict,
    ) -> list[str]:
        """Parse the catalog and run in-depth generation for every feature."""
        logger.info("=" * 60)
        logger.info("PHASE 2: Per-Feature In-Depth Generation")
        logger.info("=" * 60)

        features = self._parse_feature_catalog(remote_path)
        logger.info("Found %d features: %s", len(features), features)

        feature_files: list[str] = []
        stats["features"] = {}

        for feat_num, feat_key in features:
            out_name = self._feature_output_filename(feat_num, feat_key)
            out_path = f"{self.arch_dir_rel}/{out_name}"

            logger.info("-" * 60)
            logger.info("FEATURE %d: %s → %s", feat_num, feat_key, out_path)
            logger.info("-" * 60)

            prompt = feature_detail_prompt(
                self.arch_dir_rel, feat_num, feat_key, out_path,
            )
            self.runner.run_copilot(
                remote_path,
                prompt,
                log_name=f"feature_{feat_num:02d}_{feat_key}",
            )

            feature_files.append(out_name)
            self._cleanup_remote_arch_dir(
                remote_path, generated_files + feature_files,
            )

            proc = self._verify_remote_file(remote_path, out_name)
            if proc.returncode != 0:
                msg = f"Feature {feat_num} ({feat_key}) failed: {out_name} was not created."
                logger.error(msg)
                stats["errors"].append(msg)
                continue

            stats["features"][feat_key] = proc.stdout.strip()
            logger.info("Feature %d OK: %s", feat_num, proc.stdout.strip())

        return feature_files