from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = WORKSPACE_ROOT / "configs"
DEFAULT_ENV_PATH = WORKSPACE_ROOT / ".env"


class ConfigError(ValueError):
    """Raised when runtime config is missing or invalid."""


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")

    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    if content is None:
        return {}

    if not isinstance(content, dict):
        raise ConfigError(f"Config file must contain a YAML object: {path}")

    return content


def load_dotenv(env_path: Path = DEFAULT_ENV_PATH) -> None:
    """Load local .env values into process environment if present."""
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def get_required_env(var_name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = (os.getenv(var_name) or "").strip()
    if not value:
        raise ConfigError(f"Missing {var_name} in environment.")
    return value


def validate_runtime_environment(required_vars: Iterable[str]) -> None:
    """Fail fast when required runtime secrets are unavailable."""
    for var_name in required_vars:
        get_required_env(var_name)


def load_runtime_config(configs_dir: Path = CONFIGS_DIR) -> Dict[str, Any]:
    """Load runtime.yaml and asana.yaml into one structured config map."""
    runtime_cfg = _read_yaml(configs_dir / "runtime.yaml")
    asana_cfg = _read_yaml(configs_dir / "asana.yaml")

    merged: Dict[str, Any] = {
        "runtime": runtime_cfg,
        "asana": asana_cfg,
    }

    return merged


def get_asana_project_gid(config: Dict[str, Any]) -> str:
    project_gid = (
        config.get("asana", {}).get("project_gid", "")
        if isinstance(config, dict)
        else ""
    )
    value = str(project_gid).strip()

    if not value:
        raise ConfigError(
            "Missing configs/asana.yaml::project_gid. "
            "Set the RWLV Asana project GID in repository config."
        )

    return value
