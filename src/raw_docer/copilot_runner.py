"""Remote Copilot CLI runner.

This module replaces the former Anthropic-API generator layer. Instead of
calling Claude directly with our own agentic tool loop, we drive GitHub's
Copilot CLI (`gh copilot`) on a remote VM over SSH. Copilot CLI is itself
agentic — it reads files, runs commands, and writes outputs in its own working
directory — so our job is only:

  1. rsync the local project up to the VM.
  2. Invoke `gh copilot -p "<prompt>" --allow-all-tools ...` inside the remote
     project directory. Copilot CLI explores the codebase and writes the docs.
  3. rsync the generated `.architectureY/` directory back to the local project.

No model API keys are required on the local machine — the remote VM is
already authenticated with a premium Copilot CLI account.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ── rsync exclude list ─────────────────────────────────────────────────
# Keep the upload small and avoid shipping vendored/generated junk.
DEFAULT_RSYNC_EXCLUDES: tuple[str, ...] = (
    ".git/",
    "node_modules/",
    "vendor/",
    "__pycache__/",
    ".venv/",
    "venv/",
    "dist/",
    "build/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".idea/",
    ".vscode/",
    "tmp/",
    "*.pyc",
    "*.pyo",
    "*.log",
    # Never ship previously-generated architecture docs to the VM — the
    # whole point is to let Copilot CLI regenerate them from scratch.
    ".architectureX/",
    ".architectureY/",
)


class CopilotRunnerError(RuntimeError):
    """Raised when remote sync or Copilot CLI invocation fails."""


@dataclass
class CopilotRunnerConfig:
    ssh_host: str = "root@10.10.10.27"
    remote_workdir: str = "/root/docer_work"
    ssh_options: tuple[str, ...] = (
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
    )
    # Copilot CLI flags
    model: str | None = None
    reasoning_effort: str | None = None  # low|medium|high|xhigh
    extra_copilot_args: tuple[str, ...] = ()


class CopilotRunner:
    """Run GitHub Copilot CLI on a remote VM against a project directory."""

    def __init__(self, config: CopilotRunnerConfig):
        self.cfg = config

    # ── SSH / rsync primitives ─────────────────────────────────────────

    def _ssh_cmd(self, remote_command: str) -> list[str]:
        return ["ssh", *self.cfg.ssh_options, self.cfg.ssh_host, remote_command]

    def _run(self, cmd: list[str], *, stream: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        logger.debug("exec: %s", " ".join(shlex.quote(c) for c in cmd))
        if stream:
            # Stream output live to the parent process.
            proc = subprocess.run(cmd, check=False)
            if check and proc.returncode != 0:
                raise CopilotRunnerError(f"command failed ({proc.returncode}): {' '.join(cmd[:4])}…")
            return proc
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if check and proc.returncode != 0:
            raise CopilotRunnerError(
                f"command failed ({proc.returncode}): {' '.join(cmd[:4])}…\n"
                f"stdout: {proc.stdout[-2000:]}\nstderr: {proc.stderr[-2000:]}"
            )
        return proc

    def ssh_exec(self, remote_command: str, *, stream: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        return self._run(self._ssh_cmd(remote_command), stream=stream, check=check)

    # ── Project sync ───────────────────────────────────────────────────

    def remote_project_path(self, project_name: str) -> str:
        return f"{self.cfg.remote_workdir.rstrip('/')}/{project_name}"

    def sync_up(self, local_project: Path, project_name: str, *, clean_remote: bool = True) -> str:
        """rsync local project to the VM. Returns the remote project path."""
        remote_path = self.remote_project_path(project_name)
        # Ensure parent exists
        self.ssh_exec(f"mkdir -p {shlex.quote(self.cfg.remote_workdir)}")
        if clean_remote:
            self.ssh_exec(f"rm -rf {shlex.quote(remote_path)}")
        self.ssh_exec(f"mkdir -p {shlex.quote(remote_path)}")

        excludes: list[str] = []
        for pat in DEFAULT_RSYNC_EXCLUDES:
            excludes += ["--exclude", pat]

        ssh_cmd_str = "ssh " + " ".join(shlex.quote(o) for o in self.cfg.ssh_options)
        cmd = [
            "rsync", "-az", "--delete",
            "-e", ssh_cmd_str,
            *excludes,
            f"{str(local_project).rstrip('/')}/",
            f"{self.cfg.ssh_host}:{remote_path}/",
        ]
        logger.info("Syncing project → %s:%s", self.cfg.ssh_host, remote_path)
        self._run(cmd, stream=True)
        return remote_path

    def sync_down(self, remote_subdir: str, local_dest: Path) -> None:
        """rsync a remote subdirectory back to local."""
        local_dest.parent.mkdir(parents=True, exist_ok=True)
        ssh_cmd_str = "ssh " + " ".join(shlex.quote(o) for o in self.cfg.ssh_options)
        cmd = [
            "rsync", "-az", "--delete",
            "-e", ssh_cmd_str,
            f"{self.cfg.ssh_host}:{remote_subdir.rstrip('/')}/",
            f"{str(local_dest).rstrip('/')}/",
        ]
        logger.info("Syncing %s:%s → %s", self.cfg.ssh_host, remote_subdir, local_dest)
        self._run(cmd, stream=True)

    # ── Copilot CLI invocation ─────────────────────────────────────────

    def run_copilot(
        self,
        remote_project_path: str,
        prompt: str,
        *,
        log_name: str,
        stream: bool = True,
    ) -> str:
        """Run `gh copilot -p` non-interactively inside the remote project dir.

        The prompt is uploaded to a temp file on the VM and passed via
        `$(cat …)` so we don't have to worry about shell-quoting multi-line
        text. Copilot CLI runs with full autonomy inside the project dir.
        """
        # Upload the prompt to the remote as a file.
        remote_prompt_path = f"{remote_project_path}/.copilot_prompt_{log_name}.txt"
        remote_log_path = f"{remote_project_path}/.copilot_run_{log_name}.log"

        # Write prompt via stdin to avoid quoting issues.
        upload_cmd = self._ssh_cmd(f"cat > {shlex.quote(remote_prompt_path)}")
        logger.info("Uploading prompt (%d chars) → %s", len(prompt), remote_prompt_path)
        proc = subprocess.run(upload_cmd, input=prompt, text=True, check=False, capture_output=True)
        if proc.returncode != 0:
            raise CopilotRunnerError(f"prompt upload failed: {proc.stderr}")

        # Build the copilot invocation.
        #
        # Goal: behave exactly like a single VS Code Copilot chat run that
        # follows the prompt as written. Round-0 testing showed:
        #   * `--available-tools` whitelist breaks file writes — Copilot's
        #     `create` tool falls back to its session-state sandbox instead
        #     of writing to cwd. So we DO NOT use a whitelist.
        #   * The only behaviour that produced unwanted side effects was the
        #     `task` tool (subagent delegation), which spawned an unrelated
        #     agent that wrote extra README.md / SUMMARY files.
        # We therefore deny just the tools that cause off-contract behaviour
        # and let the model use everything else normally. Any stray files it
        # still produces are removed by the cleanup sweep in the pipeline.
        denied_tools = ",".join([
            "task",                          # subagent delegation
            "read_agent", "list_agents",     # subagent inspection
            "report_intent",                 # writes status/intent files
        ])
        copilot_flags = [
            "--allow-all-tools",
            "--allow-all-paths",
            "--allow-all-urls",
            "--no-ask-user",
            "--no-color",
            "--no-custom-instructions",      # ignore any AGENTS.md in the project
            "--no-experimental",
            "--no-remote",                   # no GitHub web/mobile remote control
            "--no-auto-update",
            "--disable-builtin-mcps",        # disable github-mcp-server tools
            "--deny-tool", denied_tools,
            "-s",
        ]
        if self.cfg.model:
            copilot_flags += ["--model", self.cfg.model]
        if self.cfg.reasoning_effort:
            copilot_flags += ["--reasoning-effort", self.cfg.reasoning_effort]
        copilot_flags += list(self.cfg.extra_copilot_args)

        # `gh copilot -- <flags>` passes flags through to the copilot binary.
        # We run inside the project dir so Copilot CLI treats it as the cwd.
        copilot_cmd = (
            f"cd {shlex.quote(remote_project_path)} && "
            f"gh copilot -- {' '.join(shlex.quote(f) for f in copilot_flags)} "
            f"-p \"$(cat {shlex.quote(remote_prompt_path)})\" "
            f"2>&1 | tee {shlex.quote(remote_log_path)}"
        )
        logger.info("Invoking Copilot CLI for stage '%s' on VM…", log_name)
        self.ssh_exec(copilot_cmd, stream=stream)

        # Fetch the log contents for summary.
        fetch = self.ssh_exec(f"cat {shlex.quote(remote_log_path)}", stream=False, check=False)
        return fetch.stdout or ""
