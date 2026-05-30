"""Configuration for raw-docer (Copilot CLI edition)."""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    ssh_host: str = Field(default="root@10.10.10.27", alias="DOCER_SSH_HOST")
    remote_workdir: str = Field(default="/root/docer_work", alias="DOCER_REMOTE_WORKDIR")
    copilot_model: str = Field(default="claude-opus-4.6", alias="DOCER_COPILOT_MODEL")
    copilot_reasoning_effort: str = Field(default="", alias="DOCER_COPILOT_EFFORT")

    architecture_dir: str = Field(default=".architectureY", alias="DOCER_ARCH_DIR")

    exclude_files: list[str] = Field(default_factory=lambda: [
        "*.env", "*.env.*", ".env*",
        "**/node_modules/**",
        "**/vendor/**",
        "**/.git/**",
        "**/tmp/**",
    ])

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def load_settings(env_file: str | None = None) -> Settings:
    if env_file and Path(env_file).exists():
        return Settings(_env_file=env_file)
    for candidate in [Path.cwd() / ".env", Path(__file__).parent.parent.parent.parent / ".env"]:
        if candidate.exists():
            return Settings(_env_file=str(candidate))
    return Settings()
