from __future__ import annotations

from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field


class Team(BaseModel):
    id: str
    name: str
    urls: List[str]


class AppConfig(BaseModel):
    timezone: str = "America/New_York"
    teams: List[Team] = Field(default_factory=list)


def load_config(config_path: Path = Path("config.yaml")) -> AppConfig:
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig(**data)