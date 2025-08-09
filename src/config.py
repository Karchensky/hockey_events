from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


class Recipient(BaseModel):
    name: str
    email: Optional[str] = None
    calendar_id: Optional[str] = None


class NotifyConfig(BaseModel):
    summary_to: List[str] = Field(default_factory=list)


class Team(BaseModel):
    id: str
    name: str
    urls: List[str]


class AppConfig(BaseModel):
    timezone: str = "America/New_York"
    urls: List[str] = Field(default_factory=list)
    recipients: List[Recipient] = Field(default_factory=list)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    teams: List[Team] = Field(default_factory=list)


@dataclass
class Env:
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    google_default_calendar_id: Optional[str]
    smtp_server: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_use_tls: bool
    default_timezone: str


def load_config(config_path: Path = Path("config.yaml")) -> AppConfig:
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig(**data)


def load_env(env_path: Optional[Path] = None) -> Env:
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    def getenv_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.lower() in {"1", "true", "yes", "y"}

    return Env(
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        google_refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", ""),
        google_default_calendar_id=os.getenv("GOOGLE_DEFAULT_CALENDAR_ID"),
        smtp_server=os.getenv("SMTP_SERVER", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", ""),
        smtp_use_tls=getenv_bool("SMTP_USE_TLS", True),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "America/New_York"),
    )