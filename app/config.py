from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


class Config:
    def __init__(self, data: dict):
        self.data = data or {}

    @property
    def app(self) -> dict:
        return self.data.get("app", {})

    @property
    def llm(self) -> dict:
        return self.data.get("llm", {})

    @property
    def runtime(self) -> dict:
        return self.data.get("runtime", {})

    @property
    def security(self) -> dict:
        return self.data.get("security", {})


def load_config(config_path: str = "configs/default.yaml") -> Config:
    load_dotenv()
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(data)


def env_value(env_name: str, default: str | None = None) -> str | None:
    return os.getenv(env_name, default)