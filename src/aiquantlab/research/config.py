"""Loading and canonical serialization of experiment configurations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aiquantlab.research.exceptions import ResearchContractError
from aiquantlab.research.models import ExperimentConfig


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as handle:
        payload: Any = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ResearchContractError(f"experiment configuration must be a mapping: {config_path}")
    return ExperimentConfig.model_validate(payload)


def write_experiment_config(config: ExperimentConfig, path: str | Path) -> None:
    """Write a resolved configuration with enums and defaults made explicit."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump(mode="json")
    output_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

