"""Configuration loading and validation."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

CONFIG_FILE = "config.json"
ENV_API_KEY = "WJX_API_KEY"


@dataclass
class AppConfig:
    api_key: str = ""
    api_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    model: str = "deepseek-ai/DeepSeek-V2.5"
    wait_min: int = 80
    wait_max: int = 100
    screenshot_dir: str = "./screenshots"
    browser_width: int = 550
    browser_height: int = 700
    headless: bool = False
    auto_submit: bool = True
    max_retries: int = 2
    output_dir: str = "./runs"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def safe_dict(self) -> Dict[str, Any]:
        data = self.to_dict()
        if data.get("api_key"):
            data["api_key"] = "***"
        return data


DEFAULT_CONFIG = AppConfig().to_dict()


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_config(data: Dict[str, Any] | None) -> AppConfig:
    merged = DEFAULT_CONFIG.copy()
    if data:
        merged.update(data)

    cfg = AppConfig(**{key: merged.get(key) for key in DEFAULT_CONFIG})
    cfg.api_key = os.getenv(ENV_API_KEY, cfg.api_key or "")
    cfg.wait_min = _coerce_int(cfg.wait_min, 80)
    cfg.wait_max = _coerce_int(cfg.wait_max, 100)
    cfg.browser_width = _coerce_int(cfg.browser_width, 550)
    cfg.browser_height = _coerce_int(cfg.browser_height, 700)
    cfg.max_retries = _coerce_int(cfg.max_retries, 2)

    if cfg.wait_min < 0:
        cfg.wait_min = 0
    if cfg.wait_max < 0:
        cfg.wait_max = 0
    if cfg.wait_min > cfg.wait_max:
        cfg.wait_min, cfg.wait_max = cfg.wait_max, cfg.wait_min
    if cfg.browser_width < 320:
        cfg.browser_width = 320
    if cfg.browser_height < 320:
        cfg.browser_height = 320
    if cfg.max_retries < 0:
        cfg.max_retries = 0
    return cfg


def load_config(path: str | os.PathLike[str] = CONFIG_FILE) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        cfg = normalize_config({})
        save_config(cfg.to_dict(), config_path)
        return cfg.to_dict()
    with config_path.open("r", encoding="utf-8-sig") as f:
        raw = json.load(f)
    return normalize_config(raw).to_dict()


def save_config(cfg: Dict[str, Any] | AppConfig, path: str | os.PathLike[str] = CONFIG_FILE) -> None:
    data = cfg.to_dict() if isinstance(cfg, AppConfig) else normalize_config(cfg).to_dict()
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_config_object(cfg: Dict[str, Any] | AppConfig | None = None) -> AppConfig:
    if isinstance(cfg, AppConfig):
        return cfg
    return normalize_config(cfg or {})