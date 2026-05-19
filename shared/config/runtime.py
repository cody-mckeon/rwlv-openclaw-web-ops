from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = WORKSPACE_ROOT / "configs"


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
