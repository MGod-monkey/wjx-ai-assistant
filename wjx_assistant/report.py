"""Run artifact persistence."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from selenium import webdriver

from .config import AppConfig
from .schema import Question


def create_run_dir(cfg: AppConfig) -> Path:
    root = Path(cfg.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    run_dir = root / time.strftime("%Y%m%d_%H%M%S", time.localtime())
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_run_report(
    run_dir: Path,
    driver: webdriver.Chrome | None,
    cfg: AppConfig,
    questions: List[Question],
    answers: Dict[str, Any],
    logs: List[str] | None = None,
    log_cb=print,
) -> None:
    write_json(run_dir / "config.safe.json", cfg.safe_dict())
    write_json(run_dir / "questions.json", [q.to_prompt_dict() for q in questions])
    write_json(run_dir / "answers.json", answers)
    if logs:
        (run_dir / "run.log").write_text("\n".join(logs) + "\n", encoding="utf-8")
    if driver is not None:
        try:
            driver.save_screenshot(str(run_dir / "result.png"))
        except Exception:
            pass
        try:
            (run_dir / "page.html").write_text(driver.page_source, encoding="utf-8")
        except Exception:
            pass
    log_cb(f"运行报告已保存到: {run_dir}")