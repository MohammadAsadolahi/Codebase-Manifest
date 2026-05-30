"""CLI interface for raw-docer (Copilot CLI edition)."""

from __future__ import annotations

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from raw_docer.config import load_settings
from raw_docer.pipeline import RawPipeline

app = typer.Typer(
    name="raw-docer",
    help="Raw architecture documentation generator powered by remote GitHub Copilot CLI.",
    no_args_is_help=True,
)
console = Console()


def setup_logging(verbose: bool = False, log_file: str | None = None):
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [
        RichHandler(console=console, rich_tracebacks=True, show_path=False)
    ]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file)
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        handlers.append(fh)
    logging.basicConfig(level=level, handlers=handlers, format="%(message)s")


@app.command()
def generate(
    project_path: str = typer.Argument(..., help="Path to the project repository"),
    force: bool = typer.Option(False, "--force", "-f", help="Clean the remote project dir before upload"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Upload only — skip Copilot calls"),
    skip_upload: bool = typer.Option(False, "--skip-upload", help="Assume the project is already uploaded to the VM"),
    env_file: str = typer.Option(None, "--env", "-e", help="Path to .env file"),
    ssh_host: str = typer.Option(None, "--ssh-host", help="Override SSH host (user@host)"),
    model: str = typer.Option(None, "--model", help="Override Copilot CLI model"),
    effort: str = typer.Option(None, "--effort", help="Copilot CLI reasoning effort (low|medium|high|xhigh)"),
    skip_features: bool = typer.Option(False, "--skip-features", help="Skip per-feature in-depth generation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
    log_file: str = typer.Option(None, "--log", "-l", help="Path to log file"),
):
    """Generate architecture docs and per-feature in-depth documents via Copilot CLI."""
    setup_logging(verbose=verbose, log_file=log_file)

    project = Path(project_path).resolve()
    if not project.exists():
        console.print(f"[red]Project path does not exist: {project}[/red]")
        raise typer.Exit(1)

    settings = load_settings(env_file)
    if ssh_host:
        settings.ssh_host = ssh_host
    if model:
        settings.copilot_model = model
    if effort:
        settings.copilot_reasoning_effort = effort

    console.print(
        f"[bold blue]raw-docer[/bold blue] — Generating docs for [green]{project}[/green]"
    )
    console.print(
        f"SSH host: [cyan]{settings.ssh_host}[/cyan] | Remote workdir: [cyan]{settings.remote_workdir}[/cyan]"
    )
    console.print(f"Architecture output dir: [cyan]{settings.architecture_dir}[/cyan]")
    if settings.copilot_model:
        console.print(f"Copilot model: [cyan]{settings.copilot_model}[/cyan]")
    if settings.copilot_reasoning_effort:
        console.print(f"Reasoning effort: [cyan]{settings.copilot_reasoning_effort}[/cyan]")

    pipeline = RawPipeline(settings, str(project))
    stats = pipeline.run(force=force, dry_run=dry_run, skip_upload=skip_upload, skip_features=skip_features)
    _display_stats(stats)

    if stats.get("errors"):
        raise typer.Exit(1)


def _display_stats(stats: dict):
    table = Table(title="raw-docer Run Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    if stats.get("dry_run"):
        table.add_row("Status", "[yellow]DRY RUN[/yellow]")

    if stats.get("stages"):
        labels = [
            ("project_summary", "Project summary"),
            ("high_level_architecture", "High-level architecture"),
            ("feature_catalog", "Feature catalog"),
            ("final_document", "Final document"),
        ]
        for key, label in labels:
            value = stats["stages"].get(key)
            if value:
                table.add_row(label, str(value))

    if stats.get("local_arch_dir"):
        table.add_row("Local output", stats["local_arch_dir"])

    if stats.get("features"):
        for feat_key, feat_info in stats["features"].items():
            table.add_row(f"Feature: {feat_key}", str(feat_info))

    errors = stats.get("errors", [])
    if errors:
        table.add_row("Errors", f"[red]{len(errors)}[/red]")
        for err in errors:
            table.add_row("", f"[red]{err}[/red]")

    console.print(table)


if __name__ == "__main__":
    app()
